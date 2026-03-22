from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "pocs", "meeting-transcripts"))

from pipeline.state import PipelineState


def load_transcript(state: PipelineState) -> dict:
    """Load transcript segments and meeting metadata from SQLite."""
    import storage

    meeting_id = state["meeting_id"]
    meeting = storage.get_meeting(meeting_id)
    if not meeting:
        return {"error": f"Meeting {meeting_id} not found"}

    segments = storage.get_transcript(meeting_id)
    if not segments:
        return {"error": f"No transcript segments found for meeting {meeting_id}"}

    raw_segments = [
        {
            "id": seg["id"],
            "speaker": seg["speaker"],
            "start": seg["start_seconds"],
            "end": seg["end_seconds"],
            "text": seg["text"],
        }
        for seg in segments
    ]

    return {
        "raw_segments": raw_segments,
        "meeting_title": meeting["title"] or "Untitled Meeting",
        "meeting_attendees": [],  # Calendar attendees not stored yet; extensible
    }
