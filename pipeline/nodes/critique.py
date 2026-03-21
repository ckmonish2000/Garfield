from __future__ import annotations

import json

from langchain_core.messages import SystemMessage, HumanMessage

from pipeline.llm import get_llm
from pipeline.state import PipelineState, Critique
from pipeline.prompts.critique import CRITIQUE_SYSTEM, CRITIQUE_USER


def _format_transcript(segments: list[dict], speaker_map: dict[str, str]) -> str:
    lines = []
    for seg in segments:
        speaker = speaker_map.get(seg["speaker"], seg["speaker"])
        lines.append(f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {speaker}: {seg['text']}")
    return "\n".join(lines)


def critique_specs(state: PipelineState) -> dict:
    """Critique generated specs against the original transcript."""
    raw_segments = state["raw_segments"]
    specs = state["specs"]
    config = state.get("config", {})
    speaker_map = state.get("speaker_map", {})

    transcript_text = _format_transcript(raw_segments, speaker_map)
    spec_json = json.dumps(specs, indent=2, default=str)

    llm = get_llm(config)
    structured_llm = llm.with_structured_output(Critique)

    result = structured_llm.invoke([
        SystemMessage(content=CRITIQUE_SYSTEM),
        HumanMessage(content=CRITIQUE_USER.format(
            transcript_text=transcript_text,
            spec_json=spec_json,
        )),
    ])

    return {"critique": result.model_dump()}


def route_after_critique(state: PipelineState) -> str:
    """Route based on critique quality and refinement count."""
    critique = state.get("critique", {})
    refinement_count = state.get("refinement_count", 0)
    quality = critique.get("overall_quality", "pass")

    if quality == "pass":
        return "review_checkpoint"
    elif quality == "needs_refinement" and refinement_count < 2:
        return "refine_specs"
    else:
        # Either "fail" or max refinements reached — proceed anyway
        return "review_checkpoint"
