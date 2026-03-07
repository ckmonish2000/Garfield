import os


def transcribe(audio_path):
    """Transcribe a WAV file using Whisper + pyannote for speaker diarization.

    Returns a list of dicts: [{speaker, start, end, text}, ...]
    """
    import torch
    import whisper
    from pyannote.audio import Pipeline

    print(f"[transcriber] Transcribing {audio_path}")

    # Whisper transcription
    model = whisper.load_model("base")
    result = model.transcribe(audio_path, language=None)
    whisper_segments = result["segments"]
    print(f"[transcriber] Whisper found {len(whisper_segments)} segments")

    # Pyannote diarization
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        print("[transcriber] HF_TOKEN not set, skipping diarization")
        return [
            {"speaker": "SPEAKER", "start": s["start"], "end": s["end"], "text": s["text"].strip()}
            for s in whisper_segments
        ]

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=hf_token,
    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    pipeline = pipeline.to(torch.device(device))
    diarization = pipeline(audio_path)

    # Build list of (start, end, speaker) from pyannote
    speaker_turns = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        speaker_turns.append((turn.start, turn.end, speaker))

    # Merge: assign each Whisper segment the speaker with most overlap
    merged = []
    for seg in whisper_segments:
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
            "text": seg["text"].strip(),
        })

    print(f"[transcriber] Produced {len(merged)} diarized segments")
    return merged
