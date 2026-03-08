import os
import re
import sys
import argparse
import tempfile
import warnings
import wave

import torch
from pydub import AudioSegment
from nemo.collections.asr.models import EncDecMultiTaskModel

SUPPORTED_FORMATS = {".wav", ".mp4"}
LARGE_FILE_THRESHOLD = 500 * 1024 * 1024  # 500 MB
MODEL_NAME = "nvidia/canary-1b-flash"
DEFAULT_CHUNK_LENGTH = 30  # seconds
OVERLAP = 5  # seconds of overlap between chunks

_TIMESTAMP_TOKEN_RE = re.compile(r'<\|\d+\|>')


def _wav_is_16k_mono(path):
    """Check if a WAV file is already 16kHz mono."""
    try:
        with wave.open(path, "rb") as wf:
            return wf.getnchannels() == 1 and wf.getframerate() == 16000
    except wave.Error:
        return False


def _prepare_audio(input_path, ext):
    """Convert input to 16kHz mono WAV. Returns (wav_path, needs_cleanup)."""
    if ext == ".wav" and _wav_is_16k_mono(input_path):
        print(f"--- {input_path} is already 16kHz mono, using directly ---")
        return input_path, False

    print(f"--- Converting {input_path} to 16kHz Mono WAV ---")
    try:
        fmt = "mp4" if ext == ".mp4" else "wav"
        audio = AudioSegment.from_file(input_path, format=fmt)
        audio = audio.set_frame_rate(16000).set_channels(1)
    except Exception as e:
        raise RuntimeError(f"Failed to convert audio: {e}") from e

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = tmp.name
    tmp.close()
    audio.export(tmp_path, format="wav")
    return tmp_path, True


def _group_words_into_segments(words):
    """Group word-level timestamps into sentence segments.

    Splits on sentence-ending punctuation (. ? !).
    Returns a list of dicts: [{start, end, text}, ...]
    """
    segments = []
    current_words = []
    seg_start = None

    for w in words:
        word_text = w["word"]
        if seg_start is None:
            seg_start = w["start"]
        current_words.append(word_text)

        if word_text.rstrip().endswith((".", "?", "!")):
            segments.append({
                "start": seg_start,
                "end": w["end"],
                "text": " ".join(current_words).strip(),
            })
            current_words = []
            seg_start = None

    # Flush remaining words
    if current_words:
        segments.append({
            "start": seg_start,
            "end": words[-1]["end"],
            "text": " ".join(current_words).strip(),
        })

    return segments


def _get_wav_duration(path):
    """Return duration of a WAV file in seconds."""
    with wave.open(path, "rb") as wf:
        return wf.getnframes() / wf.getframerate()


def _merge_overlapping_segments(segments):
    """Remove duplicate segments from overlapping chunk regions."""
    if not segments:
        return segments
    segments.sort(key=lambda s: s["start"])
    merged = [segments[0]]
    for seg in segments[1:]:
        prev = merged[-1]
        # If this segment starts before the previous one ends,
        # it's from an overlap region — keep the longer one
        if seg["start"] < prev["end"] - 0.1:
            if (seg["end"] - seg["start"]) > (prev["end"] - prev["start"]):
                merged[-1] = seg
        else:
            merged.append(seg)
    return merged


def _transcribe_single(model, wav_path):
    """Transcribe a single WAV file and return segments with timestamps.

    Returns a list of dicts: [{start, end, text}, ...]
    """
    try:
        res = model.transcribe(
            [wav_path],
            batch_size=1,
            source_lang="en",
            target_lang="en",
            pnc="yes",
            timestamps="yes",
        )
    except torch.cuda.OutOfMemoryError:
        raise RuntimeError(
            "GPU out of memory. Try reducing --chunk-length or use a GPU with more VRAM."
        )
    except Exception as e:
        raise RuntimeError(f"Transcription failed: {e}") from e

    if not res:
        return []

    ts = getattr(res[0], "timestamp", None)

    # Priority 1: Word-level timestamps (best granularity)
    if ts and "word" in ts and ts["word"]:
        filtered = [
            w for w in ts["word"]
            if not _TIMESTAMP_TOKEN_RE.fullmatch(w["word"].strip())
        ]
        if filtered:
            return _group_words_into_segments(filtered)

    # Priority 2: Segment-level timestamps
    if ts and "segment" in ts and ts["segment"]:
        segments = []
        for seg in ts["segment"]:
            text = _TIMESTAMP_TOKEN_RE.sub("", seg["segment"]).strip()
            if text:
                segments.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": text,
                })
        if segments:
            return segments

    # Fallback: no timestamp data available, return full text as single segment
    text = res[0].text.strip() if res[0].text else ""
    if text:
        text = _TIMESTAMP_TOKEN_RE.sub("", text).strip()
        if text:
            return [{"start": 0.0, "end": 0.0, "text": text}]
    return []


def transcribe_file(input_path, chunk_length=DEFAULT_CHUNK_LENGTH):
    """Transcribe a .wav or .mp4 file and return segments with timestamps.

    Returns a list of dicts: [{start, end, text}, ...]
    Long audio is split into overlapping chunks to avoid GPU OOM.
    """
    # --- Validate input ---
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")

    ext = os.path.splitext(input_path)[1].lower()
    if ext not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported format '{ext}'. Supported: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )

    file_size = os.path.getsize(input_path)
    if file_size == 0:
        raise ValueError(f"File is empty: {input_path}")
    if file_size > LARGE_FILE_THRESHOLD:
        warnings.warn(
            f"File is large ({file_size / 1024 / 1024:.0f} MB). "
            "This may require significant memory and time."
        )

    # --- Prepare audio ---
    wav_path, needs_cleanup = _prepare_audio(input_path, ext)

    try:
        # --- Load model ---
        print(f"--- Loading {MODEL_NAME} ---")
        try:
            model = EncDecMultiTaskModel.from_pretrained(model_name=MODEL_NAME)
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {e}") from e

        if torch.cuda.is_available():
            model = model.cuda().half()
        else:
            warnings.warn("CUDA not available — running on CPU (this will be slow)")

        decode_cfg = model.cfg.decoding
        decode_cfg.beam.beam_size = 1
        model.change_decoding_strategy(decode_cfg)

        # --- Transcribe ---
        print("--- Transcribing ---")
        duration = _get_wav_duration(wav_path)
        step = chunk_length - OVERLAP

        with torch.no_grad():
            # Short audio: transcribe directly without chunking
            if duration <= chunk_length:
                return _transcribe_single(model, wav_path)

            # Long audio: chunk with overlap and merge
            print(f"--- Audio is {duration:.1f}s, chunking with {chunk_length}s chunks (step={step}s, overlap={OVERLAP}s) ---")
            audio = AudioSegment.from_wav(wav_path)
            all_segments = []

            offset = 0.0
            chunk_idx = 0
            while offset < duration:
                chunk_end = min(offset + chunk_length, duration)
                chunk_audio = audio[int(offset * 1000):int(chunk_end * 1000)]

                # Export chunk to temp file
                chunk_tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                chunk_path = chunk_tmp.name
                chunk_tmp.close()
                try:
                    chunk_audio.export(chunk_path, format="wav")
                    print(f"  Chunk {chunk_idx}: {offset:.1f}s - {chunk_end:.1f}s")
                    segments = _transcribe_single(model, chunk_path)

                    # Offset timestamps to absolute positions
                    for seg in segments:
                        seg["start"] += offset
                        seg["end"] += offset
                    all_segments.extend(segments)
                except torch.cuda.OutOfMemoryError:
                    raise RuntimeError(
                        "GPU out of memory during chunked transcription. "
                        "Try reducing --chunk-length or use a GPU with more VRAM."
                    )
                finally:
                    if os.path.exists(chunk_path):
                        os.remove(chunk_path)

                offset += step
                chunk_idx += 1

            return _merge_overlapping_segments(all_segments)
    finally:
        if needs_cleanup and os.path.exists(wav_path):
            os.remove(wav_path)


def _assign_speakers(segments, wav_path):
    """Run Pyannote diarization and assign speaker labels to segments."""
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        print("[transcribe] HF_TOKEN not set, skipping diarization")
        return [
            {"speaker": "SPEAKER", "start": s["start"], "end": s["end"], "text": s["text"]}
            for s in segments
        ]

    from pyannote.audio import Pipeline

    print("[transcribe] Running speaker diarization...")
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        token=hf_token,
    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    pipeline = pipeline.to(torch.device(device))
    diarization_output = pipeline(wav_path)

    # pyannote >= 3.1 returns DiarizeOutput; extract the Annotation object
    diarization = getattr(diarization_output, "speaker_diarization", diarization_output)

    # Build list of (start, end, speaker) from pyannote
    speaker_turns = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        speaker_turns.append((turn.start, turn.end, speaker))

    # Assign each segment the speaker with most overlap
    merged = []
    for seg in segments:
        seg_start, seg_end = seg["start"], seg["end"]
        best_speaker = "UNKNOWN"
        best_overlap = 0.0
        for t_start, t_end, speaker in speaker_turns:
            overlap_start = max(seg_start, t_start)
            overlap_end = min(seg_end, t_end)
            overlap = max(0, overlap_end - overlap_start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = speaker
        merged.append({
            "speaker": best_speaker,
            "start": seg_start,
            "end": seg_end,
            "text": seg["text"],
        })

    print(f"[transcribe] Produced {len(merged)} diarized segments")
    return merged


def transcribe(audio_path):
    """Transcribe a WAV file using Canary + optional Pyannote diarization.

    Returns a list of dicts: [{speaker, start, end, text}, ...]
    Compatible with bot_worker.py / storage.insert_segments().
    """
    # Prepare 16kHz mono WAV for both transcription and diarization
    ext = os.path.splitext(audio_path)[1].lower()
    wav_path, needs_cleanup = _prepare_audio(audio_path, ext)

    try:
        segments = transcribe_file(wav_path)
        return _assign_speakers(segments, wav_path)
    finally:
        if needs_cleanup and os.path.exists(wav_path):
            os.remove(wav_path)


def _format_time(seconds):
    """Format seconds as MM:SS.s"""
    m, s = divmod(seconds, 60)
    return f"{int(m):02d}:{s:05.2f}"


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio/video files using nvidia/canary-1b-flash"
    )
    parser.add_argument("input_file", help="Path to .wav or .mp4 file")
    parser.add_argument(
        "-o", "--output", help="Write transcript to this file instead of stdout"
    )
    parser.add_argument(
        "--chunk-length", type=int, default=DEFAULT_CHUNK_LENGTH,
        help=f"Max chunk length in seconds for long audio (default: {DEFAULT_CHUNK_LENGTH})"
    )
    parser.add_argument(
        "--diarize", action="store_true",
        help="Enable speaker diarization (requires HF_TOKEN env var)"
    )
    args = parser.parse_args()

    try:
        segments = transcribe_file(args.input_file, chunk_length=args.chunk_length)

        if args.diarize:
            ext = os.path.splitext(args.input_file)[1].lower()
            wav_path, needs_cleanup = _prepare_audio(args.input_file, ext)
            try:
                segments = _assign_speakers(segments, wav_path)
            finally:
                if needs_cleanup and os.path.exists(wav_path):
                    os.remove(wav_path)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Format output with timestamps
    lines = []
    for seg in segments:
        start = _format_time(seg["start"])
        end = _format_time(seg["end"])
        speaker = seg.get("speaker", "")
        if speaker:
            lines.append(f"[{start} -> {end}] {speaker}: {seg['text']}")
        else:
            lines.append(f"[{start} -> {end}] {seg['text']}")
    output = "\n".join(lines)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Transcript written to {args.output}")
    else:
        print("\n--- TRANSCRIPT ---")
        print(output)


if __name__ == "__main__":
    main()
