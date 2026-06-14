"""
flashcard_generator.py
Thin wrapper around ai_service.generate_flashcards().
Returns a list of dicts: {question, answer, topic, difficulty}
"""

from services.ai_service import generate_flashcards


def run_flashcard_generator(study_content: str) -> list:
    """Calls AI service to generate exam flashcards."""
    if not study_content.strip():
        return []
    return generate_flashcards(study_content)
