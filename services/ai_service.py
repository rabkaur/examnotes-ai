"""
ai_service.py
Handles all AI calls using Google Gemini 2.5 Flash (google-genai package).
Loads prompt templates from prompts/ directory.
Implements chunking for large content to avoid context overflow.
"""

from google import genai
import os
import json
import time
from dotenv import load_dotenv

load_dotenv()

# ── Gemini client ──
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = "gemini-2.5-flash"

CHUNK_SIZE = 28000
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")


def load_prompt(filename: str) -> str:
    """Loads a prompt template from the prompts/ directory."""
    try:
        path = os.path.join(PROMPTS_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        raise RuntimeError(f"Could not load prompt {filename}: {e}")

def call_gemini(prompt: str) -> str:
    """Sends a prompt to Gemini 2.5 Flash and returns response text."""
    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"[Gemini Error] {e}")
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
        return call_gemini(prompt)
    results = []
    for chunk in chunks:
        prompt = prompt_template.replace("{content}", chunk)
        results.append(call_gemini(prompt))
        time.sleep(5)
    joined = "\n\n---\n\n".join(results)
    merge_prompt = f"""You are merging multiple sets of exam notes into one clean,
deduplicated, well-structured Markdown document.
Remove duplicate topics. Preserve all unique content.
Output valid Markdown only. No commentary.

NOTES TO MERGE:
{joined}"""
    return call_gemini(merge_prompt)


def analyze_pyq(pyq_content: str, study_content: str) -> str:
    """Analyzes previous year questions against study material."""
    prompt_template = load_prompt("pyq_prompt.txt")
    prompt = prompt_template.replace("{pyq_content}", pyq_content)
    prompt = prompt.replace("{study_content}", study_content[:5000])
    return call_gemini(prompt)


def generate_flashcards(study_content: str) -> list:
    """Generates flashcards and returns a list of dicts."""
    prompt_template = load_prompt("flashcard_prompt.txt")
    chunk = chunk_text(study_content)[0]
    prompt = prompt_template.replace("{content}", chunk)
    raw = call_gemini(prompt)
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
        print(f"[Flashcard Parse Warning] Could not parse JSON: {e}")
        return []


# Keep aliases so other files don't break


if __name__ == "__main__":
    test_content = """
    Normalization is the process of organizing data in a database.
    First Normal Form (1NF): Eliminate repeating groups.
    Second Normal Form (2NF): Eliminate redundant data.
    Third Normal Form (3NF): Eliminate columns not dependent on key.
    """

    print("=== Testing Gemini note generation ===")
    notes = generate_notes(test_content)
    print(notes[:800])

    print("\n=== Testing flashcard generation ===")
    cards = generate_flashcards(test_content)
    print(f"Generated {len(cards)} flashcards")
    if cards:
        print("Sample:", cards[0])