from __future__ import annotations

import json

from langchain_core.messages import SystemMessage, HumanMessage

from pipeline.llm import get_llm
from pipeline.state import PipelineState, SpecOutput
from pipeline.prompts.refine import REFINE_SYSTEM, REFINE_USER


def _format_transcript(segments: list[dict], speaker_map: dict[str, str]) -> str:
    lines = []
    for seg in segments:
        speaker = speaker_map.get(seg["speaker"], seg["speaker"])
        lines.append(f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {speaker}: {seg['text']}")
    return "\n".join(lines)


def refine_specs(state: PipelineState) -> dict:
    """Refine specs based on critique feedback."""
    raw_segments = state["raw_segments"]
    specs = state["specs"]
    critique = state["critique"]
    config = state.get("config", {})
    speaker_map = state.get("speaker_map", {})
    refinement_count = state.get("refinement_count", 0)

    transcript_text = _format_transcript(raw_segments, speaker_map)

    llm = get_llm(config)

    refined_specs = []
    for spec in specs:
        structured_llm = llm.with_structured_output(SpecOutput)
        result = structured_llm.invoke([
            SystemMessage(content=REFINE_SYSTEM),
            HumanMessage(content=REFINE_USER.format(
                transcript_text=transcript_text,
                spec_json=json.dumps(spec, indent=2, default=str),
                critique_json=json.dumps(critique, indent=2, default=str),
            )),
        ])
        refined_specs.append(result.model_dump())

    return {"specs": refined_specs, "refinement_count": refinement_count + 1}
