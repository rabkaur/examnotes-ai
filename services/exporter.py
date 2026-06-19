"""
exporter.py
Handles all export functionality for ExamNotes AI.
Generates downloadable PDFs, CSV flashcards, and Anki export.
Uses fpdf2 for PDF generation - no system dependencies required.
"""

import csv
import io
from fpdf import FPDF

def _sanitize(text) -> str:
    """Replaces Unicode characters that fpdf2's default font can't render
    and inserts breakable spaces into long unbroken words to prevent overflow."""
    if not isinstance(text, str):
        text = str(text)
    replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u2022": "*",
        "\u00a0": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.encode("latin-1", "ignore").decode("latin-1")

    # Insert a zero-width-safe break (space) into words longer than 40 chars
    words = text.split(" ")
    safe_words = []
    for word in words:
        if len(word) > 40:
            chunks = [word[i:i+40] for i in range(0, len(word), 40)]
            safe_words.append(" ".join(chunks))
        else:
            safe_words.append(word)
    return " ".join(safe_words)

class NotesPDF(FPDF):
    """Custom PDF class with header and footer."""

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(13, 148, 136)
        self.cell(0, 8, _sanitize("ExamNotes AI"), align="L")
        self.ln(6)
        self.set_draw_color(226, 232, 240)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, _sanitize(f"Page {self.page_no()}"), align="C")


def _parse_markdown_to_pdf(pdf: FPDF, text: str):
    """Parses basic Markdown and writes styled content to PDF."""
    lines = text.split("\n")
    for line in lines:
        stripped = _sanitize(line.strip())
        if not stripped:
            pdf.ln(3)
        elif stripped.startswith("## "):
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(13, 148, 136)
            pdf.multi_cell(0, 8, stripped[3:])
            pdf.set_draw_color(13, 148, 136)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(2)
        elif stripped.startswith("### "):
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(30, 41, 59)
            pdf.multi_cell(0, 7, stripped[4:])
        elif stripped.startswith("#### "):
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(71, 85, 105)
            pdf.multi_cell(0, 6, stripped[5:])
        elif stripped.startswith("- ") or stripped.startswith("* "):
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 41, 59)
            pdf.multi_cell(0, 6, f"  *  {stripped[2:]}")
        elif stripped.startswith("**") and stripped.endswith("**"):
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(30, 41, 59)
            pdf.multi_cell(0, 6, stripped[2:-2])
        else:
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 41, 59)
            pdf.multi_cell(0, 6, stripped)


def export_notes_pdf(notes: str) -> bytes:
    """Exports exam notes as a styled PDF."""
    pdf = NotesPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(13, 148, 136)
    pdf.cell(0, 12, _sanitize("Exam Notes"), align="C")
    pdf.ln(10)
    _parse_markdown_to_pdf(pdf, _sanitize(notes))
    return bytes(pdf.output())


def export_pyq_pdf(pyq_report: str) -> bytes:
    """Exports PYQ analysis report as a styled PDF."""
    pdf = NotesPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(13, 148, 136)
    pdf.cell(0, 12, _sanitize("PYQ Analysis Report"), align="C")
    pdf.ln(10)
    _parse_markdown_to_pdf(pdf, _sanitize(pyq_report))
    return bytes(pdf.output())


def export_flashcards_pdf(flashcards: list) -> bytes:
    """Exports flashcards as a styled PDF with Q&A format."""
    pdf = NotesPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(13, 148, 136)
    pdf.cell(0, 12, _sanitize("Flashcards"), align="C")
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 6, _sanitize(f"{len(flashcards)} flashcards generated"), align="C")
    pdf.ln(10)

    difficulty_colors = {
        "easy": (13, 148, 136),
        "medium": (245, 158, 11),
        "hard": (239, 68, 68),
    }

    for i, card in enumerate(flashcards, 1):
        difficulty = _sanitize(card.get("difficulty", "easy")).lower()
        color = difficulty_colors.get(difficulty, (13, 148, 136))

        topic = _sanitize(card.get("topic", ""))
        question = _sanitize(card.get("question", ""))
        answer = _sanitize(card.get("answer", ""))

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*color)
        pdf.cell(0, 7, f"#{i}  [{difficulty.upper()}]  -  {topic}")
        pdf.ln(5)

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(30, 41, 59)
        pdf.multi_cell(0, 6, f"Q: {question}")
        pdf.ln(2)

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(71, 85, 105)
        pdf.multi_cell(0, 6, f"A: {answer}")
        pdf.ln(2)

        pdf.set_draw_color(226, 232, 240)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)

    return bytes(pdf.output())


def export_question_bank_pdf(questions: list) -> bytes:
    """Exports question bank as a styled PDF grouped by marks."""
    pdf = NotesPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(13, 148, 136)
    pdf.cell(0, 12, _sanitize("Question Bank"), align="C")
    pdf.ln(10)

    two_mark = [q for q in questions if q.get("marks") == 2]
    five_mark = [q for q in questions if q.get("marks") == 5]
    ten_mark = [q for q in questions if q.get("marks") == 10]

    for section_title, section_questions in [
        ("2-Mark Questions", two_mark),
        ("5-Mark Questions", five_mark),
        ("10-Mark Questions", ten_mark),
    ]:
        if not section_questions:
            continue

        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(13, 148, 136)
        pdf.cell(0, 10, _sanitize(section_title))
        pdf.ln(2)
        pdf.set_draw_color(13, 148, 136)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

        for i, q in enumerate(section_questions, 1):
            question = _sanitize(q.get("question", ""))
            topic = _sanitize(q.get("topic", ""))
            hint = _sanitize(q.get("answer_hint", ""))

            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(30, 41, 59)
            pdf.multi_cell(0, 6, f"Q{i}. {question}")
            pdf.ln(1)

            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(71, 85, 105)
            pdf.multi_cell(0, 6, f"Topic: {topic}")
            pdf.ln(1)

            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(100, 116, 139)
            pdf.multi_cell(0, 6, f"Hint: {hint}")

            pdf.set_draw_color(226, 232, 240)
            pdf.line(10, pdf.get_y() + 2, 200, pdf.get_y() + 2)
            pdf.ln(6)

    return bytes(pdf.output())


def export_markdown(notes: str) -> bytes:
    """Exports notes as raw Markdown bytes."""
    return notes.encode("utf-8")


def export_flashcards_csv(flashcards: list) -> bytes:
    """Exports flashcards as CSV."""
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["question", "answer", "topic", "difficulty"]
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
    """Exports flashcards in Anki tab-separated format."""
    lines = []
    for card in flashcards:
        q = card.get("question", "").replace("\t", " ")
        a = card.get("answer", "").replace("\t", " ")
        lines.append(f"{q}\t{a}")
    return "\n".join(lines).encode("utf-8")


def export_question_bank_csv(questions: list) -> bytes:
    """Exports question bank as CSV."""
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["question", "marks", "type", "topic", "answer_hint"]
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