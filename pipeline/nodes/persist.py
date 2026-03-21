from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

from pipeline.state import PipelineState


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:60]


def _spec_to_markdown(spec: dict) -> str:
    """Convert a spec dict to a markdown document with YAML frontmatter."""
    lines = [
        "---",
        f"meeting_id: {spec.get('meeting_id', '')}",
        f"topic: \"{spec.get('topic', '')}\"",
        f"participants: {json.dumps(spec.get('participants', []))}",
        f"generated_at: \"{datetime.now(timezone.utc).isoformat()}\"",
        "---",
        "",
        f"# {spec.get('topic', 'Untitled')}",
        "",
        "## Summary",
        "",
        spec.get("summary", ""),
        "",
    ]

    if spec.get("requirements"):
        lines.extend(["## Requirements", ""])
        for req in spec["requirements"]:
            lines.append(f"- {req}")
        lines.append("")

    if spec.get("constraints"):
        lines.extend(["## Constraints", ""])
        for con in spec["constraints"]:
            lines.append(f"- {con}")
        lines.append("")

    if spec.get("acceptance_criteria"):
        lines.extend(["## Acceptance Criteria", ""])
        for ac in spec["acceptance_criteria"]:
            lines.append(f"- [ ] {ac}")
        lines.append("")

    if spec.get("decisions_made"):
        lines.extend(["## Decisions Made", ""])
        for dec in spec["decisions_made"]:
            lines.append(f"- {dec}")
        lines.append("")

    if spec.get("action_items"):
        lines.extend(["## Action Items", ""])
        for item in spec["action_items"]:
            assignee = item.get("assignee", "Unassigned")
            deadline = f" (by {item['deadline']})" if item.get("deadline") else ""
            lines.append(f"- [ ] {item['description']} — **{assignee}**{deadline}")
        lines.append("")

    if spec.get("open_questions"):
        lines.extend(["## Open Questions", ""])
        for q in spec["open_questions"]:
            lines.append(f"- {q}")
        lines.append("")

    return "\n".join(lines)


def persist_specs(state: PipelineState) -> dict:
    """Write specs as markdown files and record in database."""
    import sys
    pocs_path = os.path.join(os.path.dirname(__file__), "..", "..", "pocs", "meeting-transcripts")
    sys.path.insert(0, pocs_path)
    import storage

    specs = state["specs"]
    meeting_id = state["meeting_id"]
    config = state.get("config", {})
    specs_dir = config.get("specs_dir", "specs")

    # Create output directory
    meeting_specs_dir = os.path.join(specs_dir, str(meeting_id))
    os.makedirs(meeting_specs_dir, exist_ok=True)

    persisted = []
    for spec in specs:
        slug = _slugify(spec.get("topic", "untitled"))
        filename = f"{slug}.md"
        filepath = os.path.join(meeting_specs_dir, filename)

        # Write markdown file
        md_content = _spec_to_markdown(spec)
        with open(filepath, "w") as f:
            f.write(md_content)

        # Record in database
        storage.insert_spec(
            meeting_id=meeting_id,
            topic=spec.get("topic", ""),
            spec_file_path=filepath,
            status="draft",
            graph_run_id=None,
        )

        persisted.append(filepath)

    # Update meeting status
    meeting = storage.get_meeting(meeting_id)
    if meeting:
        storage.update_meeting_status(meeting["event_id"], "done")

    return {"error": None}
