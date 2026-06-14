"""
question_bank_generator.py
Generates a structured question bank from study content.
Questions are categorized by marks: 2, 5, and 10.
Returns a list of dicts with keys: question, marks, topic,
answer_hint, type.
"""

from services.ai_service import call_gemini, load_prompt, chunk_text
import json


def run_question_bank_generator(study_content: str) -> list:
    """Generates a question bank and returns a list of question dicts."""
    if not study_content.strip():
        return []

    prompt_template = load_prompt("question_bank_prompt.txt")

    chunk = chunk_text(study_content)[0]
    prompt = prompt_template.replace("{content}", chunk)

    raw = call_gemini(prompt)

    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            cleaned = "\n".join(lines)
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        return json.loads(cleaned)
    except Exception as e:
        print(f"[Question Bank Parse Warning] Could not parse response: {e}")
        return []
