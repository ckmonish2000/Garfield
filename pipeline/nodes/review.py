from __future__ import annotations

from pipeline.state import PipelineState


def review_checkpoint(state: PipelineState) -> dict:
    """Human review checkpoint. When interrupt_before is configured on this node,
    LangGraph will pause execution here, allowing a human to inspect specs and
    critique before resuming.

    If require_review is false (default), this is a passthrough.
    """
    config = state.get("config", {})
    if not config.get("require_review", False):
        return {}

    # When interrupt_before is active, the graph pauses before this node runs.
    # The human can inspect state["specs"] and state["critique"],
    # then resume with Command(resume={"review_decision": "approve"}) or similar.
    review_decision = state.get("review_decision")
    if review_decision == "revise":
        return {"error": "Human reviewer requested revision. Please re-run with updated input."}

    return {}
