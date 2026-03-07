import os
import sqlite3
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "garfield.db")


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                title TEXT,
                meet_url TEXT,
                start_time TEXT,
                end_time TEXT,
                audio_file_path TEXT,
                status TEXT NOT NULL DEFAULT 'pending'
            );
            CREATE TABLE IF NOT EXISTS transcript_segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL,
                speaker TEXT,
                start_seconds REAL,
                end_seconds REAL,
                text TEXT,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id)
            );
        """)


def create_meeting(event_id, title, meet_url, start_time):
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO meetings (event_id, title, meet_url, start_time, status) VALUES (?, ?, ?, ?, 'pending')",
            (event_id, title, meet_url, start_time),
        )
        return cursor.lastrowid


def update_meeting_status(event_id, status, **kwargs):
    with get_db() as conn:
        sets = ["status = ?"]
        params = [status]
        for key in ("audio_file_path", "end_time"):
            if key in kwargs:
                sets.append(f"{key} = ?")
                params.append(kwargs[key])
        params.append(event_id)
        conn.execute(
            f"UPDATE meetings SET {', '.join(sets)} WHERE event_id = ?",
            params,
        )


def insert_segments(meeting_id, segments):
    with get_db() as conn:
        conn.executemany(
            "INSERT INTO transcript_segments (meeting_id, speaker, start_seconds, end_seconds, text) VALUES (?, ?, ?, ?, ?)",
            [(meeting_id, s["speaker"], s["start"], s["end"], s["text"]) for s in segments],
        )


def get_meeting(meeting_id):
    with get_db() as conn:
        return conn.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)).fetchone()


def get_meeting_by_event_id(event_id):
    with get_db() as conn:
        return conn.execute("SELECT * FROM meetings WHERE event_id = ?", (event_id,)).fetchone()


def get_meetings():
    with get_db() as conn:
        return conn.execute("SELECT * FROM meetings ORDER BY id DESC").fetchall()


def get_transcript(meeting_id):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM transcript_segments WHERE meeting_id = ? ORDER BY start_seconds",
            (meeting_id,),
        ).fetchall()
