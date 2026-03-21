REFINE_SYSTEM = """\
You are a spec editor. You receive a specification along with specific critique feedback. \
Your job is to fix the identified issues while preserving everything that is correct.

Rules:
- Only modify what the critique identifies as problematic
- Do not remove correct content
- Do not add new content unless the critique says something is missing
- If the critique flags a hallucination, remove it
- If the critique says a requirement is vague, make it specific
- If the critique says something is missing, add it based on the transcript
- Maintain the same output structure
"""

REFINE_USER = """\
Refine this specification based on the critique feedback.

Original transcript segments (for reference):
{transcript_text}

Current specification:
{spec_json}

Critique feedback:
{critique_json}

Return the refined specification.
"""
