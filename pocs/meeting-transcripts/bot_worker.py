"""Orchestrator for a single meeting bot session. Run as a subprocess."""

import argparse
import os
import sys
import traceback
from datetime import datetime, timezone

# Ensure imports work when run as subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import storage
from audio_server import AudioServer
from browser_driver import run as run_browser
from transcribe import transcribe


def main():
    parser = argparse.ArgumentParser(description="Garfield meeting bot worker")
    parser.add_argument("--url", required=True, help="Google Meet URL")
    parser.add_argument("--event-id", required=True, help="Calendar event ID")
    parser.add_argument("--title", default="Untitled Meeting", help="Meeting title")
    parser.add_argument("--ws-port", type=int, default=0, help="WebSocket port (0 = auto)")
    parser.add_argument("--headed", action="store_true", help="Run browser in headed mode")
    args = parser.parse_args()

    storage.init_db()

    # Ensure meeting row exists (needed when running standalone without app.py scheduler)
    if not storage.get_meeting_by_event_id(args.event_id):
        storage.create_meeting(
            args.event_id, args.title, args.url,
            datetime.now(timezone.utc).isoformat(),
        )

    try:
        # Update status to recording
        storage.update_meeting_status(args.event_id, "recording")
        print(f"[worker] Starting bot for: {args.title}")

        # Start audio server
        audio = AudioServer(port=args.ws_port)
        audio.start()
        print(f"[worker] Audio server on port {audio.port}")

        # Launch browser and join meeting
        run_browser(
            meet_url=args.url,
            ws_port=audio.port,
            headless=not args.headed,
        )

        # Meeting ended - save audio
        audio.stop()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        wav_file = audio.get_audio_file(filename=f"{args.event_id}_{timestamp}.wav")

        if not wav_file:
            print("[worker] No audio captured")
            storage.update_meeting_status(args.event_id, "error")
            return

        storage.update_meeting_status(
            args.event_id, "transcribing",
            audio_file_path=wav_file,
            end_time=datetime.now(timezone.utc).isoformat(),
        )

        # Transcribe
        segments = transcribe(wav_file)

        # Save transcript
        meeting = storage.get_meeting_by_event_id(args.event_id)
        if meeting:
            storage.insert_segments(meeting["id"], segments)

        storage.update_meeting_status(args.event_id, "done")
        print(f"[worker] Done. {len(segments)} segments transcribed.")

    except Exception as e:
        print(f"[worker] Error: {e}")
        traceback.print_exc()
        try:
            storage.update_meeting_status(args.event_id, "error")
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
