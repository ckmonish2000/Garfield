from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage

from pipeline.llm import get_llm
from pipeline.state import PipelineState, SpecOutput
from pipeline.prompts.generate import (
    GENERATE_SPEC_SYSTEM,
    GENERATE_SPEC_USER,
    GENERATE_SINGLE_SPEC_USER,
)


def _get_segments_text(raw_segments: list[dict], indices: list[int], speaker_map: dict[str, str]) -> str:
    lines = []
    for i in indices:
        if 0 <= i < len(raw_segments):
            seg = raw_segments[i]
            speaker = speaker_map.get(seg["speaker"], seg["speaker"])
            lines.append(f"[seg {seg['id']}] [{seg['start']:.1f}s - {seg['end']:.1f}s] {speaker}: {seg['text']}")
    return "\n".join(lines)


def _get_speaker_context(speaker_map: dict[str, str]) -> str:
    if not speaker_map:
        return "Speaker names could not be resolved from the transcript."
    lines = [f"  {label} = {name}" for label, name in speaker_map.items()]
    return "Speaker identification:\n" + "\n".join(lines)


def _get_participants(raw_segments: list[dict], indices: list[int], speaker_map: dict[str, str]) -> str:
    speakers = set()
    for i in indices:
        if 0 <= i < len(raw_segments):
            speaker_label = raw_segments[i]["speaker"]
            speakers.add(speaker_map.get(speaker_label, speaker_label))
    return ", ".join(sorted(speakers))


def generate_specs(state: PipelineState) -> dict:
    """Generate one spec per topic (multi-spec mode)."""
    raw_segments = state["raw_segments"]
    classified_topics = state["classified_topics"]
    config = state.get("config", {})
    speaker_map = state.get("speaker_map", {})
    meeting_id = state["meeting_id"]

    llm = get_llm(config)
    structured_llm = llm.with_structured_output(SpecOutput)

    specs = []
    for topic in classified_topics:
        segments_text = _get_segments_text(raw_segments, topic["segment_indices"], speaker_map)
        participants = _get_participants(raw_segments, topic["segment_indices"], speaker_map)
        speaker_context = _get_speaker_context(speaker_map)

        result = structured_llm.invoke([
            SystemMessage(content=GENERATE_SPEC_SYSTEM),
            HumanMessage(content=GENERATE_SPEC_USER.format(
                meeting_id=meeting_id,
                topic_title=topic["title"],
                participants=participants,
                segments_text=segments_text,
                speaker_context=speaker_context,
            )),
        ])

        specs.append(result.model_dump())

    return {"specs": specs, "refinement_count": 0}


def generate_single_spec(state: PipelineState) -> dict:
    """Generate a single consolidated spec (single-spec mode)."""
    raw_segments = state["raw_segments"]
    classified_topics = state["classified_topics"]
    config = state.get("config", {})
    speaker_map = state.get("speaker_map", {})
    meeting_id = state["meeting_id"]
    meeting_title = state.get("meeting_title", "Untitled Meeting")

    # Collect all segment indices from all topics
    all_indices = []
    for topic in classified_topics:
        all_indices.extend(topic["segment_indices"])
    all_indices = sorted(set(all_indices))

    segments_text = _get_segments_text(raw_segments, all_indices, speaker_map)
    participants = _get_participants(raw_segments, all_indices, speaker_map)
    speaker_context = _get_speaker_context(speaker_map)

    llm = get_llm(config)
    structured_llm = llm.with_structured_output(SpecOutput)

    result = structured_llm.invoke([
        SystemMessage(content=GENERATE_SPEC_SYSTEM),
        HumanMessage(content=GENERATE_SINGLE_SPEC_USER.format(
            meeting_id=meeting_id,
            meeting_title=meeting_title,
            participants=participants,
            segments_text=segments_text,
            speaker_context=speaker_context,
        )),
    ])

    return {"specs": [result.model_dump()], "refinement_count": 0}
