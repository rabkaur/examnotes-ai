"""
ai_service.py
Handles all AI calls using Groq API (llama-3.1-8b-instant).
Loads prompt templates from prompts/ directory.
Implements chunking for large content to avoid context overflow.
Called by note_generator.py, pyq_analyzer.py, flashcard_generator.py,
and question_bank_generator.py.
"""

from groq import Groq
import os
import json
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"
CHUNK_SIZE = 4000
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")


def load_prompt(filename: str) -> str:
    """Loads a prompt template from the prompts/ directory."""
    try:
        path = os.path.join(PROMPTS_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        raise RuntimeError(f"Could not load prompt {filename}: {e}")


def call_groq(prompt: str) -> str:
    """Sends a prompt to Groq and returns the response text."""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4096,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[Groq Error] {e}")
        return ""


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> list:
    """Splits large text into chunks at paragraph boundaries."""
    if len(text) <= chunk_size:
        return [text]
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 > chunk_size:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para
    if current_chunk:
        chunks.append(current_chunk)
    return chunks


def generate_notes(study_content: str) -> str:
    """Generates structured Markdown exam notes from study content."""
    prompt_template = load_prompt("notes_prompt.txt")
    chunks = chunk_text(study_content)
    if len(chunks) == 1:
        prompt = prompt_template.replace("{content}", chunks[0])
        return call_groq(prompt)
    results = []
    for chunk in chunks:
        prompt = prompt_template.replace("{content}", chunk)
        results.append(call_groq(prompt))
    joined = "\n\n---\n\n".join(results)
    merge_prompt = f"""You are merging multiple sets of exam notes into one clean,
deduplicated, well-structured Markdown document.
Remove duplicate topics. Preserve all unique content.
Output valid Markdown only. No commentary.

NOTES TO MERGE:
{joined}"""
    return call_groq(merge_prompt)


def analyze_pyq(pyq_content: str, study_content: str) -> str:
    """Analyzes previous year questions against study material."""
    prompt_template = load_prompt("pyq_prompt.txt")
    prompt = prompt_template.replace("{pyq_content}", pyq_content)
    prompt = prompt.replace("{study_content}", study_content[:5000])
    return call_groq(prompt)


def generate_flashcards(study_content: str) -> list:
    """Generates flashcards and returns a list of dicts."""
    prompt_template = load_prompt("flashcard_prompt.txt")
    chunk = chunk_text(study_content)[0]
    prompt = prompt_template.replace("{content}", chunk)
    raw = call_groq(prompt)
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        return json.loads(cleaned)
    except Exception as e:
        print(f"[Flashcard Parse Warning] Could not parse JSON response: {e}")
        return []


# Keep call_gemini as an alias so other files don't break
call_gemini = call_groq


if __name__ == "__main__":
    test_content = """
    Normalization is the process of organizing data in a database.
    It involves dividing large tables into smaller tables and
    defining relationships between them.
    First Normal Form (1NF): Eliminate repeating groups.
    Second Normal Form (2NF): Eliminate redundant data.
    Third Normal Form (3NF): Eliminate columns not dependent on key.
    """

    print("=== Testing note generation ===")
    notes = generate_notes(test_content)
    print(notes[:800])

    print("\n=== Testing flashcard generation ===")
    cards = generate_flashcards(test_content)
    print(f"Generated {len(cards)} flashcards")
    if cards:
        print("Sample card:", cards[0])