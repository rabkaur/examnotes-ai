"""
exporter.py
Handles all export functionality for ExamNotes AI.
Generates downloadable files: Markdown, PDF, CSV flashcards,
and Anki-compatible flashcard export.
"""

import csv
import io
import markdown as md


def export_markdown(notes: str) -> bytes:
    """Converts notes string to UTF-8 encoded bytes for download."""
    return notes.encode("utf-8")


def export_pdf(notes: str) -> bytes:
    """Converts Markdown notes to PDF bytes using weasyprint."""
    try:
        from weasyprint import HTML

        html_content = md.markdown(notes, extensions=["tables", "fenced_code"])
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: Georgia, serif;
                    max-width: 800px;
                    margin: 40px auto;
                    padding: 0 20px;
                    line-height: 1.7;
                    color: #1a1a1a;
                }}
                h1 {{ font-size: 2em; border-bottom: 2px solid #333; padding-bottom: 8px; }}
                h2 {{ font-size: 1.5em; color: #2c2c2c; margin-top: 2em; }}
                h3 {{ font-size: 1.2em; color: #444; }}
                ul {{ padding-left: 1.5em; }}
                li {{ margin-bottom: 4px; }}
                p {{ margin-bottom: 1em; }}
                code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 4px; }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        pdf_bytes = HTML(string=full_html).write_pdf()
        return pdf_bytes
    except Exception as e:
        print(f"[PDF Export Error] {e}")
        return b""


def export_flashcards_csv(flashcards: list) -> bytes:
    """Exports flashcards as a CSV file with columns:
    Question, Answer, Topic, Difficulty."""
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["question", "answer", "topic", "difficulty"],
    )
    writer.writeheader()
    for card in flashcards:
        writer.writerow({
            "question": card.get("question", ""),
            "answer": card.get("answer", ""),
            "topic": card.get("topic", ""),
            "difficulty": card.get("difficulty", ""),
        })
    return output.getvalue().encode("utf-8")


def export_anki(flashcards: list) -> bytes:
    """Exports flashcards in Anki-compatible tab-separated format.
    Each line: Question[tab]Answer
    Import into Anki as tab-separated, no HTML."""
    lines = []
    for card in flashcards:
        q = card.get("question", "").replace("\t", " ")
        a = card.get("answer", "").replace("\t", " ")
        lines.append(f"{q}\t{a}")
    return "\n".join(lines).encode("utf-8")


def export_question_bank_csv(questions: list) -> bytes:
    """Exports question bank as CSV with columns:
    Question, Marks, Type, Topic, Answer Hint."""
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["question", "marks", "type", "topic", "answer_hint"],
    )
    writer.writeheader()
    for q in questions:
        writer.writerow({
            "question": q.get("question", ""),
            "marks": q.get("marks", ""),
            "type": q.get("type", ""),
            "topic": q.get("topic", ""),
            "answer_hint": q.get("answer_hint", ""),
        })
    return output.getvalue().encode("utf-8")
