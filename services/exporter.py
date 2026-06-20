"""
exporter.py
Handles all export functionality for ExamNotes AI.
Generates downloadable PDFs, Markdown, CSV flashcards, and Anki export.

Fix history:
- Removed double-sanitize bug (_sanitize was called on whole doc AND each line)
- Fixed bullet set_x(14) + multi_cell(0,...) zero-width crash
- Word-breaking now applied per-line only, not on the full document string
"""

import csv
import io
import re
from fpdf import FPDF

# Page geometry (A4, 10mm margins each side)
LEFT_MARGIN = 10
RIGHT_MARGIN = 10
PAGE_W = 210
CONTENT_W = PAGE_W - LEFT_MARGIN - RIGHT_MARGIN  # 190mm
BULLET_INDENT = 4   # mm indent for bullet text from left margin


def _clean(text) -> str:
    """
    Coerce to str, replace common Unicode typographic chars with ASCII,
    encode to latin-1 (replacing unknowns with '?').
    Does NOT do word-breaking — that is done per-line in _safe_line().
    """
    if not isinstance(text, str):
        text = str(text)

    replacements = {
        "\u2014": "--",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u2022": "*",
        "\u00a0": " ",
        "\u2192": "->",
        "\u2190": "<-",
        "\u2248": "~=",
        "\u00b0": " deg",
        "\u03b1": "alpha",
        "\u03b2": "beta",
        "\u03b3": "gamma",
        "\u03c0": "pi",
        "\u00d7": "x",
        "\u00f7": "/",
        "\u2264": "<=",
        "\u2265": ">=",
        "\u2260": "!=",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    return text.encode("latin-1", "replace").decode("latin-1")


def _safe_line(text: str, max_word: int = 35) -> str:
    """
    Clean + break any word longer than max_word chars with spaces
    so fpdf2 can wrap it. Applied per-line, never on the full document.
    """
    text = _clean(text)
    words = text.split(" ")
    out = []
    for w in words:
        if len(w) > max_word:
            out.extend(w[i:i + max_word] for i in range(0, len(w), max_word))
        else:
            out.append(w)
    return " ".join(out)


# ── PDF base class ─────────────────────────────────────────────────────────────
class NotesPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(13, 148, 136)
        self.set_x(LEFT_MARGIN)
        self.cell(CONTENT_W, 8, "ExamNotes AI", align="L")
        self.ln(6)
        self.set_draw_color(226, 232, 240)
        self.line(LEFT_MARGIN, self.get_y(), PAGE_W - RIGHT_MARGIN, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def _mc(pdf: FPDF, h: float, text: str, indent: float = 0):
    """Safe multi_cell: always uses explicit width so X position doesn't matter."""
    w = CONTENT_W - indent
    if w <= 0:
        w = CONTENT_W
    pdf.set_x(LEFT_MARGIN + indent)
    pdf.multi_cell(w, h, _safe_line(text))


# ── Markdown → PDF renderer ────────────────────────────────────────────────────
def _parse_markdown_to_pdf(pdf: FPDF, text: str):
    """
    Parse basic Markdown line-by-line and write styled content to PDF.
    Receives raw (unsanitized) text — sanitization happens per-line inside _mc/_safe_line.
    """
    for line in text.split("\n"):
        raw = line.rstrip()

        if not raw.strip():
            pdf.ln(3)
            continue

        stripped = raw.strip()

        if stripped.startswith("#### "):
            pdf.ln(1)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(71, 85, 105)
            _mc(pdf, 6, stripped[5:])

        elif stripped.startswith("### "):
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(30, 41, 59)
            _mc(pdf, 7, stripped[4:])

        elif stripped.startswith("## "):
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(13, 148, 136)
            _mc(pdf, 8, stripped[3:])
            pdf.set_draw_color(13, 148, 136)
            pdf.line(LEFT_MARGIN, pdf.get_y(), PAGE_W - RIGHT_MARGIN, pdf.get_y())
            pdf.ln(2)

        elif stripped.startswith("# "):
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 16)
            pdf.set_text_color(13, 148, 136)
            _mc(pdf, 9, stripped[2:])
            pdf.ln(2)

        elif stripped.startswith(("- ", "* ")):
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 41, 59)
            # Print bullet marker, then text with indent
            pdf.set_x(LEFT_MARGIN + BULLET_INDENT)
            pdf.cell(4, 6, "*")
            pdf.set_x(LEFT_MARGIN + BULLET_INDENT + 4)
            w = CONTENT_W - BULLET_INDENT - 4
            pdf.multi_cell(w, 6, _safe_line(stripped[2:]))

        elif stripped.startswith("---"):
            pdf.set_draw_color(226, 232, 240)
            pdf.line(LEFT_MARGIN, pdf.get_y() + 2, PAGE_W - RIGHT_MARGIN, pdf.get_y() + 2)
            pdf.ln(5)

        elif stripped.startswith("**") and stripped.endswith("**") and len(stripped) > 4:
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(30, 41, 59)
            _mc(pdf, 6, stripped[2:-2])

        else:
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 41, 59)
            _mc(pdf, 6, stripped)


# ── Export functions ───────────────────────────────────────────────────────────
def export_notes_pdf(notes: str) -> bytes:
    pdf = NotesPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(LEFT_MARGIN, 15, RIGHT_MARGIN)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(13, 148, 136)
    pdf.cell(CONTENT_W, 12, "Exam Notes", align="C")
    pdf.ln(10)
    _parse_markdown_to_pdf(pdf, notes)
    return bytes(pdf.output())


def export_pyq_pdf(pyq_report: str) -> bytes:
    pdf = NotesPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(LEFT_MARGIN, 15, RIGHT_MARGIN)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(13, 148, 136)
    pdf.cell(CONTENT_W, 12, "PYQ Analysis Report", align="C")
    pdf.ln(10)
    _parse_markdown_to_pdf(pdf, pyq_report)
    return bytes(pdf.output())


def export_flashcards_pdf(flashcards: list) -> bytes:
    pdf = NotesPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(LEFT_MARGIN, 15, RIGHT_MARGIN)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(13, 148, 136)
    pdf.cell(CONTENT_W, 12, "Flashcards", align="C")
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(CONTENT_W, 6, f"{len(flashcards)} flashcards generated", align="C")
    pdf.ln(10)

    diff_colors = {
        "easy": (13, 148, 136),
        "medium": (245, 158, 11),
        "hard": (239, 68, 68),
    }

    for i, card in enumerate(flashcards, 1):
        difficulty = _clean(card.get("difficulty", "easy")).lower()
        color = diff_colors.get(difficulty, (13, 148, 136))

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*color)
        _mc(pdf, 7, f"#{i}  [{difficulty.upper()}]  -  {card.get('topic', '')}")
        pdf.ln(2)

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(30, 41, 59)
        _mc(pdf, 6, f"Q: {card.get('question', '')}")
        pdf.ln(2)

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(71, 85, 105)
        _mc(pdf, 6, f"A: {card.get('answer', '')}")
        pdf.ln(2)

        pdf.set_draw_color(226, 232, 240)
        pdf.line(LEFT_MARGIN, pdf.get_y(), PAGE_W - RIGHT_MARGIN, pdf.get_y())
        pdf.ln(4)

    return bytes(pdf.output())


def export_question_bank_pdf(questions: list) -> bytes:
    pdf = NotesPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(LEFT_MARGIN, 15, RIGHT_MARGIN)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(13, 148, 136)
    pdf.cell(CONTENT_W, 12, "Question Bank", align="C")
    pdf.ln(10)

    two_mark = [q for q in questions if q.get("marks") == 2]
    five_mark = [q for q in questions if q.get("marks") == 5]
    ten_mark  = [q for q in questions if q.get("marks") == 10]

    for section_title, section_qs in [
        ("2-Mark Questions", two_mark),
        ("5-Mark Questions", five_mark),
        ("10-Mark Questions", ten_mark),
    ]:
        if not section_qs:
            continue
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(13, 148, 136)
        _mc(pdf, 10, section_title)
        pdf.ln(2)
        pdf.set_draw_color(13, 148, 136)
        pdf.line(LEFT_MARGIN, pdf.get_y(), PAGE_W - RIGHT_MARGIN, pdf.get_y())
        pdf.ln(5)

        for i, q in enumerate(section_qs, 1):
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(30, 41, 59)
            _mc(pdf, 6, f"Q{i}. {q.get('question', '')}")
            pdf.ln(1)

            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(71, 85, 105)
            _mc(pdf, 6, f"Topic: {q.get('topic', '')}")
            pdf.ln(1)

            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(100, 116, 139)
            _mc(pdf, 6, f"Hint: {q.get('answer_hint', '')}")

            pdf.set_draw_color(226, 232, 240)
            pdf.line(LEFT_MARGIN, pdf.get_y() + 2, PAGE_W - RIGHT_MARGIN, pdf.get_y() + 2)
            pdf.ln(6)

    return bytes(pdf.output())


def export_markdown(notes: str) -> bytes:
    return notes.encode("utf-8")


def export_flashcards_csv(flashcards: list) -> bytes:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["question", "answer", "topic", "difficulty"])
    writer.writeheader()
    for card in flashcards:
        writer.writerow({k: card.get(k, "") for k in ["question", "answer", "topic", "difficulty"]})
    return output.getvalue().encode("utf-8")


def export_anki(flashcards: list) -> bytes:
    lines = [
        f"{card.get('question','').replace(chr(9),' ')}\t{card.get('answer','').replace(chr(9),' ')}"
        for card in flashcards
    ]
    return "\n".join(lines).encode("utf-8")


def export_question_bank_csv(questions: list) -> bytes:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["question", "marks", "type", "topic", "answer_hint"])
    writer.writeheader()
    for q in questions:
        writer.writerow({k: q.get(k, "") for k in ["question", "marks", "type", "topic", "answer_hint"]})
    return output.getvalue().encode("utf-8")
