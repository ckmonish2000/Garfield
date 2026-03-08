import os
import re
import json
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone, timedelta

from flask import Flask, redirect, request, session, url_for
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

import storage

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

app = Flask(__name__)
app.secret_key = os.urandom(24)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRET_FILE = os.path.join(BASE_DIR, "client_secret.json")
TOKEN_FILE = os.path.join(BASE_DIR, "tokens.json")
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
REDIRECT_URI = "http://localhost:8000/oauth/callback"

MEETING_LINK_PATTERNS = [
    r"https://meet\.google\.com/[a-z\-]+",
    r"https://[\w.]*zoom\.us/j/\d+[^\s]*",
    r"https://teams\.microsoft\.com/l/meetup-join/[^\s]+",
]


def save_tokens(credentials):
    token_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f)


def load_tokens():
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE, "r") as f:
        token_data = json.load(f)
    return Credentials(
        token=token_data["token"],
        refresh_token=token_data["refresh_token"],
        token_uri=token_data["token_uri"],
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
        scopes=token_data["scopes"],
    )


def get_events(credentials):
    service = build("calendar", "v3", credentials=credentials)
    now = datetime.now(timezone.utc).isoformat()
    result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return result.get("items", [])


def detect_meeting_link(event):
    # Check for Google Meet conference data
    conference = event.get("conferenceData", {})
    for entry in conference.get("entryPoints", []):
        if entry.get("entryPointType") == "video":
            return entry.get("uri")

    # Search description and location for meeting links
    text = (event.get("description", "") or "") + " " + (event.get("location", "") or "")
    for pattern in MEETING_LINK_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return match.group(0)

    return None


def spawn_bot(event_id, title, meet_url):
    """Spawn a bot_worker subprocess for a meeting."""
    cmd = [
        sys.executable,
        os.path.join(BASE_DIR, "bot_worker.py"),
        "--url", meet_url,
        "--event-id", event_id,
        "--title", title,
    ]
    print(f"[scheduler] Spawning bot for: {title}")
    subprocess.Popen(cmd)


def scheduler():
    """Poll for upcoming meetings every 60 seconds."""
    while True:
        credentials = load_tokens()
        if credentials:
            try:
                events = get_events(credentials)
                now = datetime.now(timezone.utc)
                for event in events:
                    link = detect_meeting_link(event)
                    if not link:
                        continue

                    event_id = event.get("id", "")
                    summary = event.get("summary", "No title")
                    start_str = event.get("start", {}).get("dateTime")
                    if not start_str:
                        continue

                    # Parse start time
                    start_time = datetime.fromisoformat(start_str)
                    # Join if meeting starts within 2 minutes
                    if not (timedelta(0) <= (start_time - now) <= timedelta(minutes=2)):
                        continue

                    # Skip if already tracked
                    existing = storage.get_meeting_by_event_id(event_id)
                    if existing:
                        continue

                    storage.create_meeting(event_id, summary, link, start_str)
                    spawn_bot(event_id, summary, link)

            except Exception as e:
                print(f"[scheduler] Error: {e}")
        else:
            print("[scheduler] No credentials. Log in at http://localhost:8000/login")
        time.sleep(60)


@app.route("/")
def index():
    credentials = load_tokens()
    if not credentials:
        return '<a href="/login">Login with Google</a>'

    events = get_events(credentials)
    output = "<h2>Upcoming Meetings</h2><ul>"
    for event in events:
        summary = event.get("summary", "No title")
        event_id = event.get("id", "")
        start = event.get("start", {}).get("dateTime", event.get("start", {}).get("date", ""))
        link = detect_meeting_link(event)
        link_html = f' - <a href="{link}">{link}</a>' if link else ""
        join_html = ""
        if link and not storage.get_meeting_by_event_id(event_id):
            join_html = (
                f' <form method="post" action="/join" style="display:inline">'
                f'<input type="hidden" name="event_id" value="{event_id}">'
                f'<input type="hidden" name="title" value="{summary}">'
                f'<input type="hidden" name="meet_url" value="{link}">'
                f'<button type="submit">Join</button>'
                f'</form>'
            )
        output += f"<li><strong>{summary}</strong> ({start}){link_html}{join_html}</li>"
    output += "</ul>"
    return output


@app.route("/login")
def login():
    flow = Flow.from_client_secrets_file(CLIENT_SECRET_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    auth_url, state = flow.authorization_url(prompt="consent", access_type="offline")
    session["state"] = state
    session["code_verifier"] = flow.code_verifier
    return redirect(auth_url)


@app.route("/oauth/callback")
def oauth_callback():
    flow = Flow.from_client_secrets_file(CLIENT_SECRET_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    flow.code_verifier = session.get("code_verifier")
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    save_tokens(credentials)
    return redirect(url_for("index"))


@app.route("/join", methods=["POST"])
def join():
    event_id = request.form.get("event_id", "")
    title = request.form.get("title", "")
    meet_url = request.form.get("meet_url", "")

    if event_id and meet_url:
        existing = storage.get_meeting_by_event_id(event_id)
        if not existing:
            storage.create_meeting(event_id, title, meet_url, "")
            spawn_bot(event_id, title, meet_url)

    return redirect(url_for("index"))


@app.route("/meetings")
def meetings_list():
    rows = storage.get_meetings()
    html = "<h2>Meetings</h2><table border='1' cellpadding='8'><tr><th>ID</th><th>Title</th><th>Start</th><th>Status</th><th>Transcript</th></tr>"
    for m in rows:
        link = f'<a href="/meetings/{m["id"]}">View</a>' if m["status"] == "done" else ""
        html += f'<tr><td>{m["id"]}</td><td>{m["title"]}</td><td>{m["start_time"]}</td><td>{m["status"]}</td><td>{link}</td></tr>'
    html += "</table>"
    return html


@app.route("/meetings/<int:meeting_id>")
def meeting_detail(meeting_id):
    meeting = storage.get_meeting(meeting_id)
    if not meeting:
        return "Meeting not found", 404

    segments = storage.get_transcript(meeting_id)
    html = f'<h2>{meeting["title"]}</h2><p>Status: {meeting["status"]}</p>'
    if not segments:
        html += "<p>No transcript available.</p>"
    else:
        html += "<table border='1' cellpadding='6'><tr><th>Speaker</th><th>Time</th><th>Text</th></tr>"
        for s in segments:
            start = f'{s["start_seconds"]:.1f}'
            end = f'{s["end_seconds"]:.1f}'
            html += f'<tr><td>{s["speaker"]}</td><td>{start}s - {end}s</td><td>{s["text"]}</td></tr>'
        html += "</table>"
    html += '<p><a href="/meetings">Back to meetings</a></p>'
    return html


if __name__ == "__main__":
    storage.init_db()

    # Start the scheduler in a background thread
    scheduler_thread = threading.Thread(target=scheduler, daemon=True)
    scheduler_thread.start()

    app.run(host="0.0.0.0", port=8000, debug=False)
