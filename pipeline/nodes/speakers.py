from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage

from pipeline.llm import get_llm
from pipeline.state import PipelineState, SpeakerMap
from pipeline.prompts.speakers import RESOLVE_SPEAKERS_SYSTEM, RESOLVE_SPEAKERS_USER


def _format_transcript(segments: list[dict]) -> str:
    lines = []
    for seg in segments:
        start = seg["start"]
        end = seg["end"]
        lines.append(f"[{start:.1f}s - {end:.1f}s] {seg['speaker']}: {seg['text']}")
    return "\n".join(lines)


def resolve_speakers(state: PipelineState) -> dict:
    """Map SPEAKER_XX labels to real names using LLM inference."""
    raw_segments = state["raw_segments"]
    config = state.get("config", {})

    # Collect unique speaker labels
    speakers = set(seg["speaker"] for seg in raw_segments)
    if len(speakers) <= 1:
        # Single speaker or no speakers — skip LLM call
        return {"speaker_map": {}}

    transcript_text = _format_transcript(raw_segments[:50])  # Limit context
    attendees = state.get("meeting_attendees", [])
    meeting_title = state.get("meeting_title", "Untitled Meeting")

    llm = get_llm(config)
    structured_llm = llm.with_structured_output(SpeakerMap)

    result = structured_llm.invoke([
        SystemMessage(content=RESOLVE_SPEAKERS_SYSTEM),
        HumanMessage(content=RESOLVE_SPEAKERS_USER.format(
            meeting_title=meeting_title,
            attendees=", ".join(attendees) if attendees else "Unknown",
            transcript_text=transcript_text,
        )),
    ])

    return {"speaker_map": result.mapping}
