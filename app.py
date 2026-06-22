"""
app.py — ExamNotes AI
Layout: dark navbar → subtitle → full-width upload zone → generate button
→ (after upload) PYQ row → scroll → how to use → footer
"""

import streamlit as st
import os, sys, json, tempfile
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.file_parser import extract_all
from services.note_generator import run_note_generator
from services.flashcard_generator import run_flashcard_generator
from services.question_bank_generator import run_question_bank_generator
from services.exporter import (
    export_notes_pdf, export_flashcards_pdf,
    export_question_bank_pdf, export_markdown,
    export_flashcards_csv, export_anki, export_question_bank_csv,
)

MAX_FILE_BYTES = 20 * 1024 * 1024
HISTORY_FILE = Path(__file__).parent / "exports" / "history.json"
MAX_HISTORY = 5

st.set_page_config(page_title="ExamNotes AI", page_icon="📚",
                   layout="wide", initial_sidebar_state="collapsed")

# ── History helpers ────────────────────────────────────────────────────────────
def load_history() -> list:
    try:
        if HISTORY_FILE.exists():
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []

def save_history(entry: dict):
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        history = load_history()
        history.insert(0, entry)
        HISTORY_FILE.write_text(
            json.dumps(history[:MAX_HISTORY], ensure_ascii=False, indent=2),
            encoding="utf-8")
    except Exception:
        pass

# ── Session state ──────────────────────────────────────────────────────────────
_defaults = {
    "notes": "", "flashcards": [], "question_bank": [],
    "study_content": "", "processing_done": False,
    "section_errors": {}, "last_upload_names": [], "show_history": False,
    "pending_generate": False, "pending_files": [],
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Reset & base ── */
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], .stApp {
    background-color: #0F1117 !important;
    color: #E2E8F0 !important;
}

/* Hide all Streamlit chrome */
#MainMenu, header, footer,
[data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stDecorationColorBackground"],
div[data-testid="stToolbarActions"],
[data-testid="manage-app-button"], [data-testid="stStatusWidget"],
.viewerBadge_container__1QSob, ._container_gzau3_1,
._viewerBadge_nim44_23, .egzxvld1, .e1vs0wn31,
.st-emotion-cache-1wbqy5l, .st-emotion-cache-zq5wmm,
.st-emotion-cache-15ecox0, [data-testid="stSidebar"] {
    visibility: hidden !important; display: none !important;
}
a[href*="streamlit.io"] { display: none !important; }

/* ── Layout ── */
.block-container {
    padding-top: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    padding-bottom: 0 !important;
    max-width: 100% !important;
}

/* ── Global text on dark ── */
p, li, label, .stMarkdown, span { color: #CBD5E1 !important; }
h1, h2, h3, h4 { color: #F1F5F9 !important; }

/* ── Dark navbar ── */
.dark-navbar {
    position: sticky; top: 0; z-index: 100;
    background: #0F1117;
    border-bottom: 1px solid #1E293B;
    display: flex; align-items: center; justify-content: space-between;
    padding: 0.85rem 2rem;
}
.dark-nav-logo {
    font-size: 0.9rem; font-weight: 700; color: #F1F5F9 !important;
    letter-spacing: 0.02em; display: flex; align-items: center; gap: 0.5rem;
}
.dark-nav-logo-icon {
    width: 28px; height: 28px; background: #0D9488;
    border-radius: 6px; display: inline-flex; align-items: center;
    justify-content: center; font-size: 0.9rem;
}
.dark-nav-right { display: flex; gap: 0.5rem; align-items: center; }
.dark-nav-link {
    background: none; border: none;
    color: #94A3B8 !important; font-size: 0.82rem; font-weight: 500;
    cursor: pointer; padding: 0.35rem 0.75rem; border-radius: 6px;
    text-decoration: none; transition: color 0.15s;
    display: flex; align-items: center; gap: 0.3rem;
}
.dark-nav-link:hover { color: #F1F5F9 !important; background: #1E293B; }
.dark-nav-history {
    background: #1E293B; border: 1px solid #334155;
    color: #CBD5E1 !important; font-size: 0.82rem; font-weight: 500;
    padding: 0.35rem 0.85rem; border-radius: 8px; cursor: pointer;
    transition: all 0.15s;
}
.dark-nav-history:hover { border-color: #0D9488; color: #0D9488 !important; }

/* ── Main upload area ── */
.upload-area {
    max-width: 760px; margin: 0 auto;
    padding: 2.5rem 1.5rem 1rem;
}
.upload-subtitle {
    text-align: center; font-size: 1rem;
    color: #94A3B8 !important; margin-bottom: 2rem; line-height: 1.6;
}

/* Override Streamlit uploader to look like mockup */
[data-testid="stFileUploader"] {
    background: #1A1F2E !important;
    border: 1.5px dashed #334155 !important;
    border-radius: 14px !important;
    padding: 1rem !important;
    min-height: 260px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    transition: border-color 0.2s !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: #0D9488 !important;
}
[data-testid="stFileUploaderDropzone"] {
    background: transparent !important;
    border: none !important;
    padding: 2rem 1rem !important;
    text-align: center !important;
}
[data-testid="stFileUploaderDropzone"] > div {
    display: flex; flex-direction: column; align-items: center; gap: 0.5rem;
}
[data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] p,
[data-testid="stFileUploaderDropzone"] small {
    color: #64748B !important; font-size: 0.85rem !important;
}
[data-testid="stFileUploaderDropzone"] button,
[data-testid="stFileUploader"] button {
    background: #1E293B !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    color: #CBD5E1 !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    padding: 0.45rem 1.2rem !important;
    margin-top: 0.5rem !important;
    transition: all 0.15s !important;
}
[data-testid="stFileUploaderDropzone"] button:hover,
[data-testid="stFileUploader"] button:hover {
    border-color: #0D9488 !important;
    color: #0D9488 !important;
}
[data-testid="stFileUploaderFile"] {
    background: #1E293B !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
}
[data-testid="stFileUploaderFile"] * { color: #CBD5E1 !important; }

/* ── Generate button ── */
div[data-testid="stButton"] > button[kind="primary"] {
    background-color: #1E293B !important;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
    font-size: 0.9rem !important; font-weight: 500 !important;
    color: #CBD5E1 !important;
    padding: 0.7rem 2rem !important;
    width: 100% !important;
    margin-top: 0.75rem !important;
    transition: all 0.2s !important;
    letter-spacing: 0.01em !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background-color: #0D9488 !important;
    border-color: #0D9488 !important;
    color: #FFFFFF !important;
}
div[data-testid="stButton"] > button[kind="primary"] p {
    color: inherit !important; display: inline !important;
}

/* ── Secondary buttons ── */
div[data-testid="stButton"] > button[kind="secondary"] {
    background: #1E293B !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    font-size: 0.82rem !important; font-weight: 500 !important;
    color: #94A3B8 !important;
    transition: all 0.15s !important;
}
div[data-testid="stButton"] > button[kind="secondary"]:hover {
    border-color: #0D9488 !important; color: #0D9488 !important;
}

/* ── PYQ strip ── */
.pyq-strip {
    max-width: 760px; margin: 0 auto;
    padding: 1rem 1.5rem;
    background: #1A1F2E;
    border: 1px solid #1E293B;
    border-radius: 10px;
    margin-top: 0.75rem;
}
.pyq-strip-label {
    font-size: 0.7rem; font-weight: 700; color: #0D9488 !important;
    text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem;
}

/* Checkboxes on dark */
[data-testid="stCheckbox"] label { color: #94A3B8 !important; font-size: 0.85rem !important; }
[data-testid="stCheckbox"] span { color: #CBD5E1 !important; }

/* ── Processing log ── */
.log-box {
    max-width: 760px; margin: 0.75rem auto;
    background: #0A0E17; border-radius: 10px;
    padding: 1rem 1.2rem; font-family: monospace;
    font-size: 0.82rem; color: #64748B;
    max-height: 180px; overflow-y: auto;
    border: 1px solid #1E293B;
}
.log-ok  { color: #34D399; }
.log-spin { color: #FBBF24; }
.log-err  { color: #F87171; }

/* ── How to use section ── */
.how-section {
    max-width: 760px; margin: 3rem auto 0;
    padding: 0 1.5rem;
    border-top: 1px solid #1E293B;
    padding-top: 2rem;
}
.how-section-label {
    font-size: 0.72rem; font-weight: 700; color: #0D9488 !important;
    text-transform: uppercase; letter-spacing: 0.1em;
    margin-bottom: 1.2rem;
    display: flex; align-items: center; gap: 0.4rem;
}
.how-steps {
    display: flex; gap: 1rem;
}
.how-step {
    flex: 1; font-size: 0.83rem; color: #64748B !important; line-height: 1.5;
}
.how-step strong { color: #94A3B8 !important; display: block; margin-bottom: 0.2rem; }

/* ── History panel ── */
.history-wrap {
    max-width: 760px; margin: 0 auto; padding: 0 1.5rem;
}
.history-entry-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.8rem 0; border-bottom: 1px solid #1E293B;
}
.history-ts { font-size: 0.7rem; color: #475569 !important; }
.history-files { font-size: 0.85rem; font-weight: 600; color: #CBD5E1 !important; }
.history-meta { font-size: 0.75rem; color: #475569 !important; margin-top: 0.15rem; }

/* ── Results section ── */
.results-wrap { max-width: 900px; margin: 2rem auto; padding: 0 1.5rem; }
.results-header {
    font-size: 1.3rem; font-weight: 700; color: #F1F5F9 !important;
    margin-bottom: 1rem;
}

/* Tabs */
button[data-baseweb="tab"] {
    font-size: 0.85rem; font-weight: 500;
    color: #64748B !important; background: transparent !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #0D9488 !important; font-weight: 600 !important;
}
[data-baseweb="tab-highlight"] { background-color: #0D9488 !important; }
[data-baseweb="tab-border"] { background-color: #1E293B !important; }

/* Metrics */
[data-testid="stMetric"] {
    background: #1A1F2E !important; border: 1px solid #1E293B !important;
    border-radius: 10px !important; padding: 1rem !important;
}
[data-testid="stMetricLabel"] p { font-size: 0.78rem !important; color: #64748B !important; }
[data-testid="stMetricValue"] { color: #0D9488 !important; font-weight: 700 !important; }

/* Expanders */
[data-testid="stExpander"] {
    background: #1A1F2E !important; border: 1px solid #1E293B !important;
    border-radius: 8px !important; margin-bottom: 0.4rem !important;
}
[data-testid="stExpander"] summary { color: #CBD5E1 !important; }

/* Download buttons */
div[data-testid="stDownloadButton"] > button {
    border: 1px solid #334155 !important; color: #0D9488 !important;
    background: #1A1F2E !important; border-radius: 8px !important;
    font-size: 0.83rem !important; font-weight: 500 !important;
}
div[data-testid="stDownloadButton"] > button:hover {
    background: #0D9488 !important; color: white !important; border-color: #0D9488 !important;
}

/* Alerts */
[data-testid="stAlert"] {
    border-radius: 8px !important; background: #1A1F2E !important;
    border: 1px solid #1E293B !important; color: #CBD5E1 !important;
}

hr { border-color: #1E293B !important; }
textarea {
    background: #1A1F2E !important; color: #CBD5E1 !important;
    border: 1px solid #334155 !important; border-radius: 8px !important;
}
.stCaption { color: #475569 !important; }

/* Flip cards */
.flip-card { background:transparent; width:100%; height:160px; perspective:1000px; margin-bottom:0.6rem; cursor:pointer; }
.flip-card-inner { position:relative; width:100%; height:100%; text-align:left; transition:transform 0.5s; transform-style:preserve-3d; }
.flip-card:hover .flip-card-inner { transform:rotateY(180deg); }
.flip-card-front, .flip-card-back {
    position:absolute; width:100%; height:100%;
    backface-visibility:hidden; -webkit-backface-visibility:hidden;
    border-radius:10px; padding:1rem 1.2rem;
    display:flex; flex-direction:column; justify-content:center; box-sizing:border-box;
}
.flip-card-front { background:#1A1F2E; border:1px solid #1E293B; }
.flip-card-back  { background:#0A0E17; border:1px solid #0D9488; transform:rotateY(180deg); }
.flip-label { font-size:0.65rem; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.4rem; }
.flip-q-label { color:#0D9488; } .flip-a-label { color:#34D399; }
.flip-q-text { font-size:0.88rem; font-weight:600; color:#E2E8F0; line-height:1.4; }
.flip-a-text { font-size:0.83rem; color:#94A3B8; line-height:1.5; }
.diff-badge { display:inline-block; font-size:0.65rem; font-weight:700; border-radius:20px; padding:0.15rem 0.5rem; margin-bottom:0.3rem; }
.diff-easy   { background:#042f2e; color:#34D399; }
.diff-medium { background:#2d1f00; color:#FBBF24; }
.diff-hard   { background:#2d0a0a; color:#F87171; }

.section-error {
    background:#1f0a0a; border:1px solid #7f1d1d; border-radius:8px;
    padding:0.6rem 1rem; font-size:0.85rem; color:#F87171; margin-bottom:0.5rem;
}

/* ── Footer ── */
.dark-footer {
    max-width: 760px; margin: 3rem auto 2rem;
    padding: 1.5rem 1.5rem 0;
    border-top: 1px solid #1E293B;
    text-align: center;
    font-size: 0.78rem; color: #334155 !important;
}

/* ── Multiselect on dark ── */
[data-baseweb="select"] { background: #1A1F2E !important; border-color: #334155 !important; }
[data-baseweb="tag"]    { background: #0D9488 !important; }

@media (max-width: 640px) {
    .upload-area, .how-section, .results-wrap, .history-wrap { padding-left: 1rem !important; padding-right: 1rem !important; }
    .how-steps { flex-direction: column; }
    .flip-card { height: 200px; }
}
</style>
""", unsafe_allow_html=True)

# ── Navbar ─────────────────────────────────────────────────────────────────────
history_data = load_history()

nav_l, nav_mid, nav_r = st.columns([2, 4, 2])
with nav_l:
    st.markdown("""
    <div style="padding:0.85rem 0 0.85rem 2rem;">
        <span style="font-size:0.88rem;font-weight:700;color:#F1F5F9;letter-spacing:0.02em;">
            <span style="background:#0D9488;border-radius:5px;padding:2px 6px;margin-right:6px;font-size:0.8rem;">📚</span>
            examnotes ai
        </span>
    </div>
    """, unsafe_allow_html=True)

with nav_r:
    rc1, rc2 = st.columns([1, 1])
    with rc1:
        st.markdown("""
        <div style="padding-top:0.75rem;">
            <a href="#how-to-use" style="color:#94A3B8;font-size:0.82rem;text-decoration:none;
               font-weight:500;display:flex;align-items:center;gap:4px;">
               how to use ↓
            </a>
        </div>
        """, unsafe_allow_html=True)
    with rc2:
        if st.button(f"🕐 history ({len(history_data)})",
                     key="toggle_history", type="secondary", use_container_width=True):
            st.session_state.show_history = not st.session_state.show_history
            st.rerun()

st.markdown("<div style='border-bottom:1px solid #1E293B;margin:0;'></div>", unsafe_allow_html=True)

# ── History panel ──────────────────────────────────────────────────────────────
if st.session_state.show_history:
    st.markdown("<div class='history-wrap'>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    if not history_data:
        st.info("No history yet. Generate your first study package to see it here.")
    else:
        for i, entry in enumerate(history_data):
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f"""
                <div class="history-ts">{entry.get('timestamp','')}</div>
                <div class="history-files">{entry.get('files','')}</div>
                <div class="history-meta">
                    {entry.get('notes_chars',0):,} chars &nbsp;·&nbsp;
                    {entry.get('flashcard_count',0)} flashcards &nbsp;·&nbsp;
                    {entry.get('question_count',0)} questions
                </div>
                """, unsafe_allow_html=True)
            with c2:
                if st.button("Restore", key=f"restore_{i}", type="secondary"):
                    st.session_state.notes          = entry.get("notes","")
                    st.session_state.flashcards     = entry.get("flashcards",[])
                    st.session_state.question_bank  = entry.get("question_bank",[])
                    st.session_state.study_content  = entry.get("study_content","")
                    st.session_state.processing_done = True
                    st.session_state.section_errors = {}
                    st.session_state.show_history   = False
                    st.rerun()
            st.markdown("<div style='border-bottom:1px solid #1E293B;margin:0.2rem 0;'></div>",
                        unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

# ── Upload area ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="upload-area">
    <p class="upload-subtitle">
        Upload your study material and get structured notes,<br>
        flashcards, and a question bank in under a minute.
    </p>
</div>
""", unsafe_allow_html=True)

_, upload_col, _ = st.columns([1, 6, 1])
with upload_col:
    uploaded_files = st.file_uploader(
        label="drop your files here, or click to upload",
        type=["pdf", "pptx", "docx", "txt"],
        accept_multiple_files=True,
        help="pdf, pptx, docx, txt — up to 20mb per file",
        label_visibility="collapsed",
    )

# ── Detect new upload → reset ──────────────────────────────────────────────────
if uploaded_files:
    current_names = sorted([f.name for f in uploaded_files])
    if current_names != st.session_state.last_upload_names:
        for k in ("notes","pyq_report","section_errors"):
            st.session_state[k] = "" if k != "section_errors" else {}
        st.session_state.flashcards    = []
        st.session_state.question_bank = []
        st.session_state.study_content = ""
        st.session_state.processing_done = False
        st.session_state.last_upload_names = current_names

# ── Generate button ────────────────────────────────────────────────────────────
oversized = [f.name for f in (uploaded_files or []) if f.size > MAX_FILE_BYTES]
if oversized:
    st.error(f"Files exceed 20 MB: {', '.join(oversized)}")

_, btn_col, _ = st.columns([1, 6, 1])
with btn_col:
    if st.button(
        "generate notes, flashcards & question bank",
        type="primary",
        use_container_width=True,
        disabled=not bool(uploaded_files) or bool(oversized),
    ):
        # Set flag only — checkboxes render AFTER this, so we read them next rerun
        st.session_state.pending_generate = True
        st.session_state.pending_files = [f.name for f in (uploaded_files or [])]
        st.rerun()



# ── Process ────────────────────────────────────────────────────────────────────
if st.session_state.get('pending_generate') and uploaded_files and not oversized:
    with tempfile.TemporaryDirectory() as tmp_dir:
        saved_paths = []
        for file in uploaded_files:
            path = os.path.join(tmp_dir, file.name)
            with open(path, "wb") as fh:
                fh.write(file.getbuffer())
            saved_paths.append(path)

        pyq_flags = {path: False for path in saved_paths}

        _, log_col, _ = st.columns([1, 6, 1])
        with log_col:
            log_placeholder = st.empty()
        log_lines: list[str] = []

        def update_log(line: str, status: str = "spin"):
            css  = {"ok":"log-ok","spin":"log-spin","err":"log-err"}.get(status,"log-spin")
            icon = {"ok":"✓","spin":"⟳","err":"✗"}.get(status,"⟳")
            log_lines.append(f'<span class="{css}">{icon} {line}</span>')
            log_placeholder.markdown(
                '<div class="log-box">'+"<br>".join(log_lines)+"</div>",
                unsafe_allow_html=True)

        update_log("Extracting text from files...")
        extracted = extract_all(saved_paths, pyq_flags)
        st.session_state.study_content = extracted["study_content"]
        st.session_state.pyq_content   = extracted["pyq_content"]


        for name, err in extracted.get("errors", []):
            update_log(f"{name}: {err}", "err")

        if not st.session_state.study_content.strip():
            update_log("No readable text found.", "err")
            st.error("No text extracted. Check if files are scanned or password-protected.")
            st.stop()

        update_log(f"Extracted {len(st.session_state.study_content):,} chars", "ok")
        update_log("Running AI tasks in parallel...")

        section_errors: dict[str, str] = {}

        def _run(task_name, fn, *args):
            try:    return task_name, fn(*args), None
            except Exception as e: return task_name, None, str(e)

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {
                pool.submit(_run,"notes",run_note_generator,st.session_state.study_content):"notes",
                pool.submit(_run,"flashcards",run_flashcard_generator,st.session_state.study_content):"flashcards",
                pool.submit(_run,"question_bank",run_question_bank_generator,st.session_state.study_content):"question_bank",
            }


            for future in as_completed(futures):
                name, result, error = future.result()
                if error:
                    section_errors[name] = error
                    update_log(f"{name}: failed — {error[:100]}", "err")
                else:
                    if name=="notes":         st.session_state.notes         = result or ""
                    elif name=="flashcards":  st.session_state.flashcards    = result or []
                    elif name=="question_bank": st.session_state.question_bank = result or []
                    update_log(f"{name}: done ✓","ok")

        st.session_state.section_errors  = section_errors
        st.session_state.processing_done = True

        save_history({
            "timestamp":      datetime.now().strftime("%d %b %Y, %I:%M %p"),
            "files":          ", ".join(f.name for f in uploaded_files),
            "notes_chars":    len(st.session_state.notes),
            "flashcard_count":len(st.session_state.flashcards),
            "question_count": len(st.session_state.question_bank),
            "notes":          st.session_state.notes,
            "flashcards":     st.session_state.flashcards,
            "question_bank":  st.session_state.question_bank,
            "study_content":  st.session_state.study_content[:5000],
        })

        update_log("Saved to history ✓","ok")
        update_log("All done!" if not section_errors else
                   f"Done with {len(section_errors)} error(s). Check tabs below.","ok")
        st.session_state.pending_generate = False
        st.balloons()
        st.rerun()

# ── Results ────────────────────────────────────────────────────────────────────
if st.session_state.processing_done:
    st.markdown("<div class='results-wrap'>", unsafe_allow_html=True)
    st.markdown('<div class="results-header">Your Study Package</div>', unsafe_allow_html=True)

    tab1, tab3, tab4, tab5 = st.tabs([
        "📝 Notes", "🃏 Flashcards", "❓ Q-Bank", "📈 Stats & Downloads"
    ])

    with tab1:
        _, rg = st.columns([5,1])
        with rg:
            if st.button("↻ Regen", key="regen_notes", type="secondary"):
                with st.spinner("Regenerating..."):
                    try:
                        st.session_state.notes = run_note_generator(st.session_state.study_content)
                        st.session_state.section_errors.pop("notes",None)
                        st.rerun()
                    except Exception as e: st.error(str(e))
        if "notes" in st.session_state.section_errors:
            st.markdown(f'<div class="section-error">⚠️ {st.session_state.section_errors["notes"]}</div>',unsafe_allow_html=True)
        elif st.session_state.notes:
            st.markdown(st.session_state.notes)
        else:
            st.info("No notes yet.")

    with tab3:
        _, rg = st.columns([5,1])
        with rg:
            if st.button("↻ Regen", key="regen_flash", type="secondary"):
                with st.spinner("Regenerating..."):
                    try:
                        st.session_state.flashcards = run_flashcard_generator(st.session_state.study_content)
                        st.session_state.section_errors.pop("flashcards",None)
                        st.rerun()
                    except Exception as e: st.error(str(e))
        if "flashcards" in st.session_state.section_errors:
            st.markdown(f'<div class="section-error">⚠️ {st.session_state.section_errors["flashcards"]}</div>',unsafe_allow_html=True)
        elif st.session_state.flashcards:
            cards = st.session_state.flashcards
            st.markdown(f"**{len(cards)} flashcards** — hover to flip.")
            diffs = sorted({c.get("difficulty","easy") for c in cards})
            sel = st.multiselect("Filter by difficulty", diffs, default=diffs, key="diff_filter")
            filtered = [c for c in cards if c.get("difficulty","easy") in sel]
            cols = st.columns(2)
            for i, card in enumerate(filtered):
                diff = card.get("difficulty","easy").lower()
                dc = f"diff-{diff}" if diff in ("easy","medium","hard") else "diff-easy"
                q = card.get("question","").replace('"',"&quot;").replace("<","&lt;")
                a = card.get("answer","").replace('"',"&quot;").replace("<","&lt;")
                with cols[i%2]:
                    st.markdown(f"""
                    <div class="flip-card"><div class="flip-card-inner">
                      <div class="flip-card-front">
                        <span class="diff-badge {dc}">{diff.upper()}</span>
                        <div class="flip-label flip-q-label">QUESTION — {card.get('topic','')}</div>
                        <div class="flip-q-text">{q}</div>
                      </div>
                      <div class="flip-card-back">
                        <div class="flip-label flip-a-label">ANSWER</div>
                        <div class="flip-a-text">{a}</div>
                      </div>
                    </div></div>""", unsafe_allow_html=True)
        else:
            st.info("No flashcards yet.")

    with tab4:
        _, rg = st.columns([5,1])
        with rg:
            if st.button("↻ Regen", key="regen_qbank", type="secondary"):
                with st.spinner("Regenerating..."):
                    try:
                        st.session_state.question_bank = run_question_bank_generator(st.session_state.study_content)
                        st.session_state.section_errors.pop("question_bank",None)
                        st.rerun()
                    except Exception as e: st.error(str(e))
        if "question_bank" in st.session_state.section_errors:
            st.markdown(f'<div class="section-error">⚠️ {st.session_state.section_errors["question_bank"]}</div>',unsafe_allow_html=True)
        elif st.session_state.question_bank:
            qs = st.session_state.question_bank
            two  = [q for q in qs if q.get("marks")==2]
            five = [q for q in qs if q.get("marks")==5]
            ten  = [q for q in qs if q.get("marks")==10]
            c1,c2,c3 = st.columns(3)
            c1.metric("2-Mark",len(two)); c2.metric("5-Mark",len(five)); c3.metric("10-Mark",len(ten))
            st.divider()
            for label, section in [("### ✏️ 2-Mark",two),("### 📝 5-Mark",five),("### 📋 10-Mark",ten)]:
                if not section: continue
                st.markdown(label)
                for i, q in enumerate(section,1):
                    with st.expander(f"Q{i}. {q.get('question','')}"):
                        st.markdown(f"**Topic:** {q.get('topic','')}")
                        st.markdown(f"**Hint:** {q.get('answer_hint','')}")
        else:
            st.info("No question bank yet.")

    with tab5:
        c1,c2,c3 = st.columns(3)
        c1.metric("Characters", f"{len(st.session_state.study_content):,}")
        c2.metric("Flashcards", len(st.session_state.flashcards))
        c3.metric("Questions",  len(st.session_state.question_bank))
        if st.session_state.section_errors:
            for sec, err in st.session_state.section_errors.items():
                st.error(f"**{sec}**: {err}")
        st.text_area("Content preview",value=st.session_state.study_content[:1000],height=120,disabled=True)
        st.divider()
        st.markdown("### Downloads")
        c1,c2,c3,c4 = st.columns(4)
        with c1:
            if st.session_state.notes:
                st.download_button("📄 Notes PDF",export_notes_pdf(st.session_state.notes),"exam_notes.pdf","application/pdf",use_container_width=True)
        with c2:
            if st.session_state.flashcards:
                st.download_button("🃏 Flashcards PDF",export_flashcards_pdf(st.session_state.flashcards),"flashcards.pdf","application/pdf",use_container_width=True)
        with c4:
            if st.session_state.question_bank:
                st.download_button("❓ Q-Bank PDF",export_question_bank_pdf(st.session_state.question_bank),"question_bank.pdf","application/pdf",use_container_width=True)
        c5,c6,c7,c8 = st.columns(4)
        with c5:
            if st.session_state.notes:
                st.download_button("📝 Notes MD",export_markdown(st.session_state.notes),"exam_notes.md","text/markdown",use_container_width=True)
        with c6:
            if st.session_state.flashcards:
                st.download_button("📋 Flashcards CSV",export_flashcards_csv(st.session_state.flashcards),"flashcards.csv","text/csv",use_container_width=True)
        with c7:
            if st.session_state.flashcards:
                st.download_button("🎴 Anki .txt",export_anki(st.session_state.flashcards),"flashcards_anki.txt","text/plain",use_container_width=True)
        with c8:
            if st.session_state.question_bank:
                st.download_button("📊 Q-Bank CSV",export_question_bank_csv(st.session_state.question_bank),"question_bank.csv","text/csv",use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ── How to use + Footer (below the fold) ──────────────────────────────────────
st.markdown("""
<div class="how-section" id="how-to-use">
    <div class="how-section-label">💡 how to use</div>
    <div class="how-steps">
        <div class="how-step"><strong>1 · upload</strong>Drop your study PDFs, slides, or notes</div>
        <div class="how-step"><strong>2 · tag pyq</strong>Tick any previous year question paper</div>
        <div class="how-step"><strong>3 · generate</strong>Click generate — takes ~45 seconds</div>
        <div class="how-step"><strong>4 · download</strong>Notes, flashcards & question bank</div>
    </div>
</div>
<div class="dark-footer">
    examnotes ai · powered by gemini 2.5 flash
</div>
""", unsafe_allow_html=True)
