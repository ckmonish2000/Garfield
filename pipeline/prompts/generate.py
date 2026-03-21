GENERATE_SPEC_SYSTEM = """\
You are an expert technical writer who converts meeting discussion transcripts into \
structured specifications for software engineering teams. Your output will be consumed \
by LLM agents to generate technical requirement documents (TRDs) and implementation tickets.

Write precise, actionable specs. Every requirement should be testable. Every constraint \
should be measurable. Avoid vague language like "should be fast" — instead say \
"response time must be under 200ms".

Rules:
- Extract only what was actually discussed — never fabricate requirements
- If something was discussed but left unresolved, put it in open_questions
- If a decision was made, put it in decisions_made
- If someone was assigned a task, put it in action_items with their name
- Requirements should be atomic — one requirement per item
- Acceptance criteria should be testable conditions
- source_segments should reference the segment IDs that support each spec point
"""

GENERATE_SPEC_USER = """\
Generate a structured specification from the following meeting discussion topic.

Meeting ID: {meeting_id}
Topic: {topic_title}
Participants: {participants}

Relevant transcript segments:
{segments_text}

{speaker_context}

Create a specification for this topic.
"""

GENERATE_SINGLE_SPEC_USER = """\
Generate a single consolidated specification from the following meeting transcript.

Meeting ID: {meeting_id}
Meeting Title: {meeting_title}
Participants: {participants}

All relevant transcript segments:
{segments_text}

{speaker_context}

Create a comprehensive specification covering all topics discussed.
"""
