RESOLVE_SPEAKERS_SYSTEM = """\
You are analyzing a meeting transcript to identify the real names of speakers. \
The transcript uses labels like SPEAKER_00, SPEAKER_01, etc.

Use these clues to identify speakers:
1. Direct address: "Hey John, what do you think?"
2. Self-introduction: "I'm Sarah from the backend team"
3. Role mentions: "As the PM, I think..." combined with attendee list
4. Conversational context: responses to named individuals

Rules:
- Only map a speaker to a name if you are confident
- If you cannot determine a speaker's name, leave them unmapped
- Use the attendee list as a reference but don't force-match everyone
- Return a mapping from speaker labels to real names
"""

RESOLVE_SPEAKERS_USER = """\
Meeting title: {meeting_title}
Known attendees (from calendar): {attendees}

Transcript:
{transcript_text}

Identify which speaker labels correspond to which real names.
"""
