from __future__ import annotations

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from pipeline.state import PipelineState
from pipeline.nodes.load import load_transcript
from pipeline.nodes.speakers import resolve_speakers
from pipeline.nodes.classify import classify_and_segment
from pipeline.nodes.generate import generate_specs, generate_single_spec
from pipeline.nodes.critique import critique_specs, route_after_critique
from pipeline.nodes.refine import refine_specs
from pipeline.nodes.review import review_checkpoint
from pipeline.nodes.persist import persist_specs


def _route_granularity(state: PipelineState) -> str:
    """Route based on spec_mode config: multi or single."""
    config = state.get("config", {})
    mode = config.get("spec_mode", "multi")
    if mode == "single":
        return "generate_single_spec"
    return "generate_specs"


def _check_error(state: PipelineState) -> str:
    """Check if an error occurred and short-circuit to END."""
    if state.get("error"):
        return END
    return "next"


def build_graph(require_review: bool = False) -> StateGraph:
    """Build and compile the transcript-to-spec LangGraph pipeline.

    Args:
        require_review: If True, the graph will pause at review_checkpoint
                       for human inspection before persisting specs.

    Returns:
        Compiled graph ready for invocation.
    """
    workflow = StateGraph(PipelineState)

    # Add all nodes
    workflow.add_node("load_transcript", load_transcript)
    workflow.add_node("resolve_speakers", resolve_speakers)
    workflow.add_node("classify_and_segment", classify_and_segment)
    workflow.add_node("generate_specs", generate_specs)
    workflow.add_node("generate_single_spec", generate_single_spec)
    workflow.add_node("critique_specs", critique_specs)
    workflow.add_node("refine_specs", refine_specs)
    workflow.add_node("review_checkpoint", review_checkpoint)
    workflow.add_node("persist_specs", persist_specs)

    # Linear edges: START -> load -> speakers -> classify
    workflow.add_edge(START, "load_transcript")
    workflow.add_conditional_edges(
        "load_transcript",
        lambda s: END if s.get("error") else "resolve_speakers",
    )
    workflow.add_edge("resolve_speakers", "classify_and_segment")

    # Conditional: classify -> route to multi or single spec generation
    workflow.add_conditional_edges(
        "classify_and_segment",
        lambda s: END if s.get("error") else _route_granularity(s),
        {
            "generate_specs": "generate_specs",
            "generate_single_spec": "generate_single_spec",
            END: END,
        },
    )

    # Both generate nodes -> critique
    workflow.add_edge("generate_specs", "critique_specs")
    workflow.add_edge("generate_single_spec", "critique_specs")

    # Critique -> route based on quality
    workflow.add_conditional_edges(
        "critique_specs",
        route_after_critique,
        {
            "review_checkpoint": "review_checkpoint",
            "refine_specs": "refine_specs",
        },
    )

    # Refine loops back to critique
    workflow.add_edge("refine_specs", "critique_specs")

    # Review -> persist -> END
    workflow.add_conditional_edges(
        "review_checkpoint",
        lambda s: END if s.get("error") else "persist_specs",
    )
    workflow.add_edge("persist_specs", END)

    # Compile with checkpointer for human-in-the-loop support
    memory = MemorySaver()

    interrupt_before = ["review_checkpoint"] if require_review else None
    return workflow.compile(checkpointer=memory, interrupt_before=interrupt_before)


def run_pipeline(
    meeting_id: int,
    llm_provider: str = "openai",
    llm_model: str = "gpt-4o",
    spec_mode: str = "multi",
    require_review: bool = False,
    specs_dir: str = "specs",
    thread_id: str | None = None,
) -> dict:
    """Run the transcript-to-spec pipeline for a meeting.

    Args:
        meeting_id: ID of the meeting in the database.
        llm_provider: LLM provider to use ("openai", "anthropic", "google").
        llm_model: Model name.
        spec_mode: "multi" for one spec per topic, "single" for consolidated.
        require_review: If True, pause for human review before persisting.
        specs_dir: Directory for output spec files.
        thread_id: Optional thread ID for resuming interrupted runs.

    Returns:
        Final pipeline state dict.
    """
    graph = build_graph(require_review=require_review)

    config = {
        "configurable": {"thread_id": thread_id or f"meeting-{meeting_id}"},
    }

    initial_state: PipelineState = {
        "meeting_id": meeting_id,
        "raw_segments": [],
        "meeting_title": "",
        "meeting_attendees": [],
        "speaker_map": {},
        "classified_topics": [],
        "specs": [],
        "critique": {},
        "refinement_count": 0,
        "review_decision": None,
        "config": {
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "spec_mode": spec_mode,
            "require_review": require_review,
            "specs_dir": specs_dir,
        },
        "error": None,
    }

    result = graph.invoke(initial_state, config)
    return result
