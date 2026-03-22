from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage

from pipeline.llm import get_llm
from pipeline.state import PipelineState, ClassificationResult
from pipeline.prompts.classify import (
    CLASSIFY_AND_SEGMENT_SYSTEM,
    CLASSIFY_AND_SEGMENT_USER,
)


def _format_transcript_with_indices(segments: list[dict], speaker_map: dict[str, str]) -> str:
    lines = []
    for i, seg in enumerate(segments):
        speaker = speaker_map.get(seg["speaker"], seg["speaker"])
        lines.append(f"[{i}] [{seg['start']:.1f}s - {seg['end']:.1f}s] {speaker}: {seg['text']}")
    return "\n".join(lines)


def classify_and_segment(state: PipelineState) -> dict:
    """Classify transcript segments and group into topic clusters."""
    raw_segments = state["raw_segments"]
    config = state.get("config", {})
    speaker_map = state.get("speaker_map", {})
    meeting_title = state.get("meeting_title", "Untitled Meeting")

    transcript_text = _format_transcript_with_indices(raw_segments, speaker_map)

    llm = get_llm(config)
    structured_llm = llm.with_structured_output(ClassificationResult)

    result = structured_llm.invoke([
        SystemMessage(content=CLASSIFY_AND_SEGMENT_SYSTEM),
        HumanMessage(content=CLASSIFY_AND_SEGMENT_USER.format(
            num_segments=len(raw_segments),
            meeting_title=meeting_title,
            transcript_text=transcript_text,
        )),
    ])

    # Convert to serializable dicts for state
    topics = [
        {
            "title": topic.title,
            "segment_indices": topic.segment_indices,
            "relevance": topic.relevance,
        }
        for topic in result.topics
        if topic.relevance == "spec_relevant"
    ]

    if not topics:
        return {"error": "No spec-relevant topics found in transcript", "classified_topics": []}

    return {"classified_topics": topics}
