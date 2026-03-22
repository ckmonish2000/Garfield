# Transcript-to-Spec Pipeline Design

## Problem

Garfield captures meeting audio and produces diarized transcripts (`{speaker, start, end, text}` segments stored in SQLite). There is no automated way to convert these transcripts into structured specifications that downstream LLM agents can consume to generate TRDs, tickets, and code.

Meetings contain mixed content — feature discussions, bug reports, architecture decisions, and noise. The system must intelligently filter, classify, and structure this into actionable specs.

## Approach

A LangGraph `StateGraph` implementing an iterative pipeline with self-correction loops (Approach B from brainstorming). The pipeline has 9 nodes, a bounded critique-refine loop (max 2 iterations), optional human review checkpoint, and provider-agnostic LLM abstraction.

### Why This Approach

- **Self-correction loop** is the highest-leverage quality mechanism for specs that feed downstream LLM agents
- Only marginally more complex than a linear pipeline (one bounded loop, flat state)
- Matches existing sequential worker patterns in the codebase (`bot_worker.py`)
- Avoids premature optimization of parallel topic processing (can migrate to map-reduce later if latency becomes a bottleneck)

## Graph Flow

```
load_transcript -> resolve_speakers -> classify_and_segment -> route_granularity
                                                                      |
                                                             +--------+--------+
                                                             |                 |
                                                        gen_multi        gen_single
                                                             +--------+--------+
                                                                      |
                                                               critique_specs
                                                                      |
                                                                {quality_ok?}
                                                                /           \
                                                             yes             no (max 2x)
                                                              |               |
                                                      review_checkpoint   refine_specs
                                                              |               |
                                                        persist_specs    (-> critique)
                                                              |
                                                             END
```

## State Shape

```python
class PipelineState(TypedDict):
    meeting_id: int
    raw_segments: list[dict]              # from SQLite: {speaker, start, end, text}
    speaker_map: dict[str, str]           # SPEAKER_00 -> "John"
    classified_topics: list[dict]         # [{title, segments, relevance}]
    specs: list[dict]                     # generated SpecOutput objects
    critique: dict                        # {quality, issues, missing_topics, hallucinations}
    refinement_count: int                 # loop counter, max 2
    review_decision: Optional[str]        # "approve" | "revise" | None
    config: dict                          # {provider, model, spec_mode, require_review}
    error: Optional[str]
```

## Output Spec Format

A lean, agent-friendly format optimized for downstream LLM consumption:

```python
class ActionItem(BaseModel):
    description: str
    assignee: Optional[str]
    deadline: Optional[str]

class SpecOutput(BaseModel):
    meeting_id: int
    topic: str
    summary: str
    requirements: list[str]
    constraints: list[str]
    acceptance_criteria: list[str]
    participants: list[str]
    decisions_made: list[str]
    action_items: list[ActionItem]
    open_questions: list[str]
    source_segments: list[int]            # IDs back to transcript_segments
```

Each spec is persisted as:
1. A markdown file at `specs/{meeting_id}/{topic_slug}.md` with YAML frontmatter
2. A row in the `specs` SQLite table linked to the meeting

## Node Descriptions

### 1. load_transcript
Pure data loading, no LLM. Reads segments from SQLite using existing `storage.get_transcript(meeting_id)`. Also loads meeting metadata (title, attendees).

### 2. resolve_speakers
Maps `SPEAKER_XX` identifiers to real names. Sources: (1) Calendar invite attendees from `meetings` table, (2) LLM inference from transcript content (e.g., "Hey John..."). Populates `speaker_map`.

### 3. classify_and_segment
Single LLM call with the full transcript. Classifies each segment as `spec_relevant`, `context_only`, or `noise`. Groups relevant segments into coherent topics with titles. Uses Pydantic structured output.

### 4. route_granularity
Conditional edge (no LLM). Routes based on `config["spec_mode"]`:
- `"multi"` (default): one spec per detected topic
- `"single"`: collapse all topics into one spec

### 5. generate_specs / generate_single_spec
Core generation node. For each topic (or all topics in single mode), makes an LLM call with structured prompt that outputs the `SpecOutput` model. Extracts requirements, constraints, acceptance criteria, action items, and open questions.

### 6. critique_specs
Self-critique step. Feeds generated specs + original transcript segments to the LLM. Checks for:
- Accuracy against what was actually discussed
- Missing requirements or topics
- Fabricated/hallucinated details
- Action item attribution correctness

Returns structured `Critique` with routing: `pass` -> review, `needs_refinement` (and count < 2) -> refine, else -> review with `needs_review` status.

### 7. refine_specs
Targeted revision based on specific critique feedback. Not regeneration from scratch. Increments `refinement_count`.

### 8. review_checkpoint
Uses LangGraph's `interrupt_before` + `MemorySaver` checkpointer. If `config["require_review"]` is true, graph pauses for human inspection. Otherwise passthrough.

### 9. persist_specs
Writes markdown files to disk, inserts rows into `specs` table, updates meeting status.

## LLM Provider Abstraction

Provider-agnostic via factory function:

```python
def get_llm(config: dict) -> BaseChatModel:
    provider = config.get("llm_provider", "openai")
    model = config.get("llm_model", "gpt-4o")
    # Returns ChatOpenAI, ChatAnthropic, or ChatGoogleGenerativeAI
```

API keys via environment variables. No provider is hardcoded in any node.

## Storage Extension

New `specs` table:

```sql
CREATE TABLE IF NOT EXISTS specs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER NOT NULL,
    topic TEXT,
    spec_file_path TEXT,
    status TEXT DEFAULT 'draft',
    created_at TEXT,
    graph_run_id TEXT,
    FOREIGN KEY (meeting_id) REFERENCES meetings(id)
);
```

## Integration Points

- `bot_worker.py`: invoke pipeline after transcription (new status: `generating_specs`)
- `app.py`: new Flask routes for spec viewing and manual pipeline trigger
- Meeting status flow: `pending -> recording -> transcribing -> generating_specs -> done`

## Design Decisions

1. **Combined classify+segment** (single LLM call) rather than separate calls — reduces latency and avoids information loss between calls
2. **Bounded refinement loop** (max 2) — prevents runaway LLM costs while allowing quality improvement
3. **Structured output via Pydantic** throughout — ensures consistent, parseable output from every LLM call
4. **Speaker resolution as separate node** — cleanly separable concern, can be skipped if calendar data is unavailable
5. **Markdown + SQLite dual storage** — markdown files are git-friendly and easy for downstream agents to read; SQLite provides queryability and meeting linkage
