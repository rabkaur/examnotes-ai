"""
note_generator.py
Thin wrapper around ai_service.generate_notes().
Receives study_content string, returns Markdown string.
"""

from services.ai_service import generate_notes


def run_note_generator(study_content: str) -> str:
    """Calls AI service to generate structured exam notes."""
    if not study_content.strip():
        return "# No study content provided."
    return generate_notes(study_content)
