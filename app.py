"""
app.py — ExamNotes AI
Changes in this version:
- FIX: PYQ checkbox reads from st.session_state directly (not local dict)
- NEW: History stored as JSON in exports/history.json, survives refresh
- NEW: Navbar with How to Use anchor + History dropdown
- NEW: Centered hero layout with three cards
"""

import streamlit as st
import os, sys, json, tempfile
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.file_parser import extract_all
from services.note_generator import run_note_generator
from services.pyq_analyzer import run_pyq_analyzer
from services.flashcard_generator import run_flashcard_generator
from services.question_bank_generator import run_question_bank_generator
from services.exporter import (
    export_notes_pdf, export_pyq_pdf, export_flashcards_pdf,
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
        history = history[:MAX_HISTORY]
        HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

# ── Session state ──────────────────────────────────────────────────────────────
_defaults = {
    "notes": "", "pyq_report": "", "flashcards": [], "question_bank": [],
    "study_content": "", "pyq_content": "", "processing_done": False,
    "section_errors": {}, "last_upload_names": [],
    "show_history": False,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], .stApp {
    background-color: #F8FAFC !important; color: #1E293B !important;
}
#MainMenu,header,footer,[data-testid="stToolbar"],[data-testid="stDecoration"],
[data-testid="stDecorationColorBackground"],div[data-testid="stToolbarActions"],
[data-testid="manage-app-button"],[data-testid="stStatusWidget"],
.viewerBadge_container__1QSob,._container_gzau3_1,._viewerBadge_nim44_23,
.egzxvld1,.e1vs0wn31,.st-emotion-cache-1wbqy5l,.st-emotion-cache-zq5wmm,
.st-emotion-cache-15ecox0,[data-testid="stSidebar"]
{ visibility:hidden; display:none !important; }
a[href*="streamlit.io"] { display:none !important; }

.block-container {
    padding-top: 0 !important; padding-left: 2rem !important;
    padding-right: 2rem !important; padding-bottom: 2rem !important;
    max-width: 1100px !important;
}
p,li,label,.stMarkdown,div,span { color: #1E293B; }
h1,h2,h3,h4 { color: #1E293B !important; }

/* ── Navbar ── */
.navbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 1.1rem 0; border-bottom: 1px solid #E2E8F0; margin-bottom: 0;
}
.navbar-logo {
    font-size: 1rem; font-weight: 800; color: #1E293B !important;
    letter-spacing: -0.5px; text-transform: uppercase;
}
.navbar-links { display: flex; gap: 0.3rem; align-items: center; }
.nav-btn {
    background: none; border: 1.5px solid #E2E8F0; border-radius: 8px;
    padding: 0.3rem 0.9rem; font-size: 0.82rem; font-weight: 600;
    color: #475569 !important; cursor: pointer; text-decoration: none;
    transition: all 0.15s;
}
.nav-btn:hover { border-color: #0D9488; color: #0D9488 !important; }
.nav-btn-active { border-color: #0D9488 !important; color: #0D9488 !important; background: #F0FDF9 !important; }

/* ── Hero ── */
.hero {
    text-align: center; padding: 3.5rem 1rem 2.5rem;
}
.hero-title {
    font-size: 3rem; font-weight: 800; color: #1E293B !important;
    letter-spacing: -1.5px; line-height: 1.1; margin-bottom: 0.6rem;
}
.hero-title span { color: #0D9488; }
.hero-sub {
    font-size: 1.05rem; color: #64748B !important;
    max-width: 520px; margin: 0 auto 2.5rem;
}

/* ── Three cards ── */
.cards-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; }
.card {
    flex: 1; background: #FFFFFF; border: 1px solid #E2E8F0;
    border-radius: 14px; padding: 1.4rem 1.5rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.card-icon { font-size: 1.4rem; margin-bottom: 0.6rem; }
.card-label {
    font-size: 0.68rem; font-weight: 700; color: #0D9488 !important;
    text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.3rem;
}
.card-desc { font-size: 0.85rem; color: #64748B !important; line-height: 1.5; }
.how-item { font-size: 0.85rem; color: #334155 !important; padding: 0.25rem 0;
    border-bottom: 1px solid #F1F5F9; line-height: 1.5; }
.how-item:last-child { border-bottom: none; }

/* ── History panel ── */
.history-panel {
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px;
    padding: 1.2rem 1.4rem; margin-bottom: 1.5rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.history-entry {
    display: flex; justify-content: space-between; align-items: flex-start;
    padding: 0.7rem 0; border-bottom: 1px solid #F1F5F9;
}
.history-entry:last-child { border-bottom: none; }
.history-ts { font-size: 0.72rem; color: #94A3B8 !important; margin-bottom: 0.2rem; }
.history-files { font-size: 0.82rem; font-weight: 600; color: #1E293B !important; }
.history-meta { font-size: 0.75rem; color: #64748B !important; margin-top: 0.1rem; }

/* ── Upload zone ── */
[data-testid="stFileUploader"] {
    border: 2px dashed #CBD5E1 !important; border-radius: 12px !important;
    background: #FFFFFF !important; padding: 0.5rem !important;
}
[data-testid="stFileUploader"]:hover { border-color: #0D9488 !important; }
[data-testid="stFileUploaderDropzone"] {
    background-color: #FFFFFF !important; border: none !important; padding: 1rem !important;
}
[data-testid="stFileUploaderDropzone"] button,
[data-testid="stFileUploader"] button {
    background-color: #F1F5F9 !important; color: #1E293B !important;
    border: 1.5px solid #94A3B8 !important; border-radius: 8px !important;
    font-weight: 500 !important; opacity: 1 !important;
    visibility: visible !important; display: inline-flex !important;
}
[data-testid="stFileUploaderDropzone"] button:hover,
[data-testid="stFileUploader"] button:hover {
    background-color: #E2E8F0 !important; border-color: #0D9488 !important; color: #0D9488 !important;
}
[data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] p,
[data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploader"] span,
[data-testid="stFileUploader"] small { color: #475569 !important; opacity: 1 !important; }
[data-testid="stFileUploaderFile"] {
    background-color: #F1F5F9 !important; border: 1px solid #E2E8F0 !important; border-radius: 8px !important;
}
[data-testid="stFileUploaderFile"] * { color: #1E293B !important; }

/* ── Buttons ── */
div[data-testid="stButton"] > button[kind="primary"] {
    background-color: #1E293B !important; border: none !important;
    border-radius: 10px !important; font-size: 0.95rem !important;
    font-weight: 600 !important; color: #FFFFFF !important;
    padding: 0.65rem 2rem !important; width: 100% !important;
    transition: background 0.2s !important; margin-top: 0.5rem !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover { background-color: #0F172A !important; }
div[data-testid="stButton"] > button[kind="primary"] * { color: #FFFFFF !important; }
div[data-testid="stButton"] > button[kind="primary"] p { color: #FFFFFF !important; display: inline !important; }
div[data-testid="stButton"] > button[kind="secondary"] {
    background-color: #F1F5F9 !important; border: 1.5px solid #CBD5E1 !important;
    border-radius: 8px !important; font-size: 0.82rem !important;
    font-weight: 500 !important; color: #475569 !important;
}
div[data-testid="stButton"] > button[kind="secondary"]:hover {
    border-color: #0D9488 !important; color: #0D9488 !important;
}

/* ── Log ── */
.log-box {
    background: #0F172A; border-radius: 10px; padding: 1rem 1.2rem;
    font-family: monospace; font-size: 0.83rem; color: #94A3B8;
    max-height: 200px; overflow-y: auto; margin: 1rem 0;
}
.log-ok { color: #34D399; } .log-spin { color: #FBBF24; } .log-err { color: #F87171; }

/* ── Results ── */
.results-header { font-size: 1.6rem; font-weight: 700; color: #1E293B !important; margin: 2rem 0 1rem; }
button[data-baseweb="tab"] { font-size: 0.88rem; font-weight: 500; color: #64748B !important; background: transparent !important; }
button[data-baseweb="tab"][aria-selected="true"] { color: #0D9488 !important; font-weight: 600 !important; }
[data-baseweb="tab-highlight"] { background-color: #0D9488 !important; }
[data-baseweb="tab-border"] { background-color: #E2E8F0 !important; }

[data-testid="stMetric"] {
    background: #FFFFFF !important; border: 1px solid #E2E8F0 !important;
    border-radius: 10px !important; padding: 1rem !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
}
[data-testid="stMetricLabel"] p { font-size: 0.8rem !important; color: #64748B !important; }
[data-testid="stMetricValue"] { color: #0D9488 !important; font-weight: 700 !important; }

[data-testid="stExpander"] {
    background: #FFFFFF !important; border: 1px solid #E2E8F0 !important;
    border-radius: 8px !important; margin-bottom: 0.4rem !important;
}
[data-testid="stExpander"]:hover { border-color: #0D9488 !important; }

div[data-testid="stDownloadButton"] > button {
    border: 1.5px solid #0D9488 !important; color: #0D9488 !important;
    background: transparent !important; border-radius: 8px !important;
    font-size: 0.85rem !important; font-weight: 500 !important;
}
div[data-testid="stDownloadButton"] > button:hover { background: #0D9488 !important; color: white !important; }

[data-testid="stAlert"] {
    border-radius: 10px !important; background: #F0FDF9 !important;
    border: 1px solid #99F6E4 !important; color: #1E293B !important;
}
hr { border-color: #E2E8F0 !important; }
textarea { background: #FFFFFF !important; color: #1E293B !important; border: 1px solid #E2E8F0 !important; border-radius: 8px !important; }

/* ── Flip cards ── */
.flip-card { background-color:transparent; width:100%; height:160px; perspective:1000px; margin-bottom:0.6rem; cursor:pointer; }
.flip-card-inner { position:relative; width:100%; height:100%; text-align:left; transition:transform 0.5s; transform-style:preserve-3d; }
.flip-card:hover .flip-card-inner { transform:rotateY(180deg); }
.flip-card-front,.flip-card-back {
    position:absolute; width:100%; height:100%; backface-visibility:hidden;
    -webkit-backface-visibility:hidden; border-radius:10px; padding:1rem 1.2rem;
    display:flex; flex-direction:column; justify-content:center; box-sizing:border-box;
}
.flip-card-front { background:#FFFFFF; border:1px solid #E2E8F0; }
.flip-card-back { background:#0F172A; border:1px solid #0F172A; transform:rotateY(180deg); }
.flip-label { font-size:0.65rem; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.4rem; }
.flip-q-label { color:#0D9488; } .flip-a-label { color:#34D399; }
.flip-q-text { font-size:0.9rem; font-weight:600; color:#1E293B; line-height:1.4; }
.flip-a-text { font-size:0.85rem; color:#CBD5E1; line-height:1.5; }
.diff-badge { display:inline-block; font-size:0.65rem; font-weight:700; border-radius:20px; padding:0.15rem 0.5rem; margin-bottom:0.3rem; }
.diff-easy { background:#CCFBF1; color:#0D9488; }
.diff-medium { background:#FEF3C7; color:#D97706; }
.diff-hard { background:#FEE2E2; color:#DC2626; }

.section-error {
    background:#FEF2F2; border:1px solid #FECACA; border-radius:8px;
    padding:0.6rem 1rem; font-size:0.85rem; color:#DC2626; margin-bottom:0.5rem;
}
.footer {
    text-align:center; padding:1.5rem 0 0.5rem; color:#94A3B8 !important;
    font-size:0.82rem; border-top:1px solid #E2E8F0; margin-top:2rem;
}
@media (max-width:640px) {
    .block-container { padding-left:1rem !important; padding-right:1rem !important; }
    .hero-title { font-size:2rem; }
    .cards-row { flex-direction:column; }
    .flip-card { height:200px; }
}
</style>
""", unsafe_allow_html=True)

# ── Navbar ─────────────────────────────────────────────────────────────────────
history_data = load_history()
history_active = "nav-btn-active" if st.session_state.show_history else ""

col_nav_l, col_nav_r = st.columns([1, 1])
with col_nav_l:
    st.markdown('<div class="navbar-logo">📚 ExamNotes AI</div>', unsafe_allow_html=True)
with col_nav_r:
    btn_col1, btn_col2 = st.columns([1, 1])
    with btn_col1:
        st.markdown('<a class="nav-btn" href="#how-to-use">How to use ↓</a>', unsafe_allow_html=True)
    with btn_col2:
        hist_label = f"🕐 History ({len(history_data)})"
        if st.button(hist_label, key="toggle_history", type="secondary", use_container_width=True):
            st.session_state.show_history = not st.session_state.show_history
            st.rerun()

st.markdown("<hr style='margin:0 0 0 0;border-color:#E2E8F0;'>", unsafe_allow_html=True)

# ── History panel ──────────────────────────────────────────────────────────────
if st.session_state.show_history:
    st.markdown("### 🕐 Previous Sessions")
    if not history_data:
        st.info("No history yet. Generate your first study package to see it here.")
    else:
        for i, entry in enumerate(history_data):
            with st.container():
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"""
                    <div class="history-ts">{entry.get('timestamp','')}</div>
                    <div class="history-files">{entry.get('files','')}</div>
                    <div class="history-meta">
                        {entry.get('notes_chars',0):,} chars of notes &nbsp;·&nbsp;
                        {entry.get('flashcard_count',0)} flashcards &nbsp;·&nbsp;
                        {entry.get('question_count',0)} questions
                    </div>
                    """, unsafe_allow_html=True)
                with c2:
                    if st.button("Restore", key=f"restore_{i}", type="secondary"):
                        st.session_state.notes          = entry.get("notes", "")
                        st.session_state.pyq_report     = entry.get("pyq_report", "")
                        st.session_state.flashcards     = entry.get("flashcards", [])
                        st.session_state.question_bank  = entry.get("question_bank", [])
                        st.session_state.study_content  = entry.get("study_content", "")
                        st.session_state.pyq_content    = entry.get("pyq_content", "")
                        st.session_state.processing_done = True
                        st.session_state.section_errors = {}
                        st.session_state.show_history   = False
                        st.rerun()
                st.markdown("<hr style='margin:0.4rem 0;border-color:#F1F5F9;'>", unsafe_allow_html=True)
    st.markdown("")

# ── Hero ───────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-title">Turn notes into<br><span>exam weapons.</span></div>
    <div class="hero-sub">
        Upload your study material and get structured notes,
        flashcards, and a question bank in under a minute.
    </div>
</div>
""", unsafe_allow_html=True)

# ── Three cards: Upload / Tag PYQ / How to use ─────────────────────────────────
card1, card2, card3 = st.columns([2, 1, 1])

with card1:
    st.markdown("""
    <div class="card-icon">📂</div>
    <div class="card-label">Study Material</div>
    <div class="card-desc">Drop your files below. PDF, PPTX, DOCX, and TXT supported. Max 20 MB per file.</div>
    """, unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        label="Upload files",
        type=["pdf", "pptx", "docx", "txt"],
        accept_multiple_files=True,
        help="Max 20 MB per file.",
        label_visibility="collapsed",
    )

with card2:
    st.markdown("""
    <div class="card-icon">🎯</div>
    <div class="card-label">Tag Question Papers</div>
    <div class="card-desc">Tick any file that is a previous year question paper.</div>
    """, unsafe_allow_html=True)
    if uploaded_files:
        for f in uploaded_files:
            size_mb = f.size / (1024 * 1024)
            label = f.name if f.size <= MAX_FILE_BYTES else f"⚠️ {f.name} ({size_mb:.1f} MB)"
            st.checkbox(label, key=f"pyq_{f.name}")
    else:
        st.markdown("<p style='color:#94A3B8;font-size:0.83rem;margin-top:0.5rem;'>Upload files first.</p>",
                    unsafe_allow_html=True)

with card3:
    st.markdown("""
    <div class="card-icon">💡</div>
    <div class="card-label" id="how-to-use">How to use</div>
    <div>
        <div class="how-item">1 · Upload your study PDFs or slides</div>
        <div class="how-item">2 · Tag any question paper as PYQ</div>
        <div class="how-item">3 · Click Generate — takes ~45 seconds</div>
        <div class="how-item">4 · Download notes, flashcards & Q-Bank</div>
    </div>
    """, unsafe_allow_html=True)

# ── Detect new upload → reset ──────────────────────────────────────────────────
if uploaded_files:
    current_names = sorted([f.name for f in uploaded_files])
    if current_names != st.session_state.last_upload_names:
        for k in ("notes","pyq_report","flashcards","question_bank",
                  "study_content","pyq_content","section_errors"):
            st.session_state[k] = "" if isinstance(_defaults[k], str) else _defaults[k]
        st.session_state.processing_done = False
        st.session_state.last_upload_names = current_names

# ── Validate ───────────────────────────────────────────────────────────────────
oversized = [f.name for f in (uploaded_files or []) if f.size > MAX_FILE_BYTES]
if oversized:
    st.error(f"Files exceed 20 MB: {', '.join(oversized)}. Please compress or split them.")

# ── Generate ───────────────────────────────────────────────────────────────────
if uploaded_files and not oversized:
    if st.button("🚀 Generate Study Package", type="primary", use_container_width=True):

        with tempfile.TemporaryDirectory() as tmp_dir:
            saved_paths = []
            for file in uploaded_files:
                path = os.path.join(tmp_dir, file.name)
                with open(path, "wb") as fh:
                    fh.write(file.getbuffer())
                saved_paths.append(path)

            # ── PYQ FIX: read checkbox values directly from st.session_state ──
            pyq_flags = {
                path: bool(st.session_state.get(f"pyq_{file.name}", False))
                for file, path in zip(uploaded_files, saved_paths)
            }

            log_placeholder = st.empty()
            log_lines: list[str] = []

            def update_log(line: str, status: str = "spin"):
                css = {"ok":"log-ok","spin":"log-spin","err":"log-err"}.get(status,"log-spin")
                icon = {"ok":"✓","spin":"⟳","err":"✗"}.get(status,"⟳")
                log_lines.append(f'<span class="{css}">{icon} {line}</span>')
                log_placeholder.markdown(
                    '<div class="log-box">' + "<br>".join(log_lines) + "</div>",
                    unsafe_allow_html=True)

            update_log("Extracting text from files...")
            extracted = extract_all(saved_paths, pyq_flags)
            st.session_state.study_content = extracted["study_content"]
            st.session_state.pyq_content   = extracted["pyq_content"]

            tagged = [f.name for f, p in zip(uploaded_files, saved_paths) if pyq_flags.get(p)]
            if tagged:
                update_log(f"PYQ files detected: {', '.join(tagged)}", "ok")
            else:
                update_log("No files tagged as PYQ — skipping PYQ analysis", "spin")

            for name, err in extracted.get("errors", []):
                update_log(f"{name}: {err}", "err")

            if not st.session_state.study_content.strip():
                update_log("No readable text found.", "err")
                st.error("No text could be extracted. Check if files are scanned or password-protected.")
                st.stop()

            update_log(f"Extracted {len(st.session_state.study_content):,} chars", "ok")
            update_log("Running AI tasks in parallel...")

            section_errors: dict[str, str] = {}

            def _run(task_name, fn, *args):
                try:
                    return task_name, fn(*args), None
                except Exception as e:
                    return task_name, None, str(e)

            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = {
                    pool.submit(_run,"notes",run_note_generator,st.session_state.study_content):"notes",
                    pool.submit(_run,"flashcards",run_flashcard_generator,st.session_state.study_content):"flashcards",
                    pool.submit(_run,"question_bank",run_question_bank_generator,st.session_state.study_content):"question_bank",
                }
                if st.session_state.pyq_content.strip():
                    futures[pool.submit(_run,"pyq",run_pyq_analyzer,
                        st.session_state.pyq_content,st.session_state.study_content)] = "pyq"

                for future in as_completed(futures):
                    task_name, result, error = future.result()
                    if error:
                        section_errors[task_name] = error
                        update_log(f"{task_name}: failed — {error[:100]}", "err")
                    else:
                        if task_name == "notes":       st.session_state.notes         = result or ""
                        elif task_name == "pyq":       st.session_state.pyq_report    = result or ""
                        elif task_name == "flashcards":st.session_state.flashcards    = result or []
                        elif task_name == "question_bank": st.session_state.question_bank = result or []
                        update_log(f"{task_name}: done ✓", "ok")

            st.session_state.section_errors  = section_errors
            st.session_state.processing_done = True

            # ── Save to history ────────────────────────────────────────────────
            save_history({
                "timestamp":      datetime.now().strftime("%d %b %Y, %I:%M %p"),
                "files":          ", ".join(f.name for f in uploaded_files),
                "notes_chars":    len(st.session_state.notes),
                "flashcard_count":len(st.session_state.flashcards),
                "question_count": len(st.session_state.question_bank),
                "notes":          st.session_state.notes,
                "pyq_report":     st.session_state.pyq_report,
                "flashcards":     st.session_state.flashcards,
                "question_bank":  st.session_state.question_bank,
                "study_content":  st.session_state.study_content[:5000],
                "pyq_content":    st.session_state.pyq_content[:2000],
            })

            update_log("Saved to history ✓", "ok")
            update_log("All done!" if not section_errors else
                       f"Done with {len(section_errors)} error(s). Check tabs below.", "ok")
            st.balloons()
            st.rerun()

# ── Results ────────────────────────────────────────────────────────────────────
if st.session_state.processing_done:
    st.markdown('<div class="results-header">Your Study Package</div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 Exam Notes", "📊 PYQ Analysis", "🃏 Flashcards", "❓ Question Bank", "📈 Stats & Downloads"
    ])

    # Tab 1 — Notes
    with tab1:
        _, col_regen = st.columns([5, 1])
        with col_regen:
            if st.button("↻ Regenerate", key="regen_notes", type="secondary"):
                with st.spinner("Regenerating..."):
                    try:
                        st.session_state.notes = run_note_generator(st.session_state.study_content)
                        st.session_state.section_errors.pop("notes", None)
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
        if "notes" in st.session_state.section_errors:
            st.markdown(f'<div class="section-error">⚠️ {st.session_state.section_errors["notes"]}</div>',
                        unsafe_allow_html=True)
            st.info("Check your GEMINI_API_KEY or try regenerating.")
        elif st.session_state.notes:
            st.markdown(st.session_state.notes)
        else:
            st.info("No notes yet.")

    # Tab 2 — PYQ
    with tab2:
        _, col_regen = st.columns([5, 1])
        with col_regen:
            if st.session_state.pyq_content and st.button("↻ Regenerate", key="regen_pyq", type="secondary"):
                with st.spinner("Regenerating..."):
                    try:
                        st.session_state.pyq_report = run_pyq_analyzer(
                            st.session_state.pyq_content, st.session_state.study_content)
                        st.session_state.section_errors.pop("pyq", None)
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
        if "pyq" in st.session_state.section_errors:
            st.markdown(f'<div class="section-error">⚠️ {st.session_state.section_errors["pyq"]}</div>',
                        unsafe_allow_html=True)
        elif st.session_state.pyq_report:
            st.markdown(st.session_state.pyq_report)
        else:
            st.info("No question papers tagged. Tick the PYQ checkbox next to a file before generating.")

    # Tab 3 — Flashcards
    with tab3:
        _, col_regen = st.columns([5, 1])
        with col_regen:
            if st.button("↻ Regenerate", key="regen_flash", type="secondary"):
                with st.spinner("Regenerating..."):
                    try:
                        st.session_state.flashcards = run_flashcard_generator(st.session_state.study_content)
                        st.session_state.section_errors.pop("flashcards", None)
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
        if "flashcards" in st.session_state.section_errors:
            st.markdown(f'<div class="section-error">⚠️ {st.session_state.section_errors["flashcards"]}</div>',
                        unsafe_allow_html=True)
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
                with cols[i % 2]:
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

    # Tab 4 — Question Bank
    with tab4:
        _, col_regen = st.columns([5, 1])
        with col_regen:
            if st.button("↻ Regenerate", key="regen_qbank", type="secondary"):
                with st.spinner("Regenerating..."):
                    try:
                        st.session_state.question_bank = run_question_bank_generator(st.session_state.study_content)
                        st.session_state.section_errors.pop("question_bank", None)
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
        if "question_bank" in st.session_state.section_errors:
            st.markdown(f'<div class="section-error">⚠️ {st.session_state.section_errors["question_bank"]}</div>',
                        unsafe_allow_html=True)
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
                for i, q in enumerate(section, 1):
                    with st.expander(f"Q{i}. {q.get('question','')}"):
                        st.markdown(f"**Topic:** {q.get('topic','')}")
                        st.markdown(f"**Hint:** {q.get('answer_hint','')}")
        else:
            st.info("No question bank yet.")

    # Tab 5 — Stats & Downloads
    with tab5:
        st.markdown("### 📈 Stats")
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Characters", f"{len(st.session_state.study_content):,}")
        c2.metric("Flashcards", len(st.session_state.flashcards))
        c3.metric("Questions",  len(st.session_state.question_bank))
        c4.metric("PYQ", "Yes" if st.session_state.pyq_content else "No")

        if st.session_state.section_errors:
            for sec, err in st.session_state.section_errors.items():
                st.error(f"**{sec}**: {err}")

        st.text_area("Content preview (first 1,000 chars)",
                     value=st.session_state.study_content[:1000], height=120, disabled=True)
        st.divider()
        st.markdown("### 📥 Downloads")

        c1,c2,c3,c4 = st.columns(4)
        with c1:
            if st.session_state.notes:
                st.download_button("📄 Notes (PDF)", export_notes_pdf(st.session_state.notes),
                                   "exam_notes.pdf","application/pdf",use_container_width=True)
        with c2:
            if st.session_state.pyq_report:
                st.download_button("📊 PYQ (PDF)", export_pyq_pdf(st.session_state.pyq_report),
                                   "pyq_analysis.pdf","application/pdf",use_container_width=True)
        with c3:
            if st.session_state.flashcards:
                st.download_button("🃏 Flashcards (PDF)", export_flashcards_pdf(st.session_state.flashcards),
                                   "flashcards.pdf","application/pdf",use_container_width=True)
        with c4:
            if st.session_state.question_bank:
                st.download_button("❓ Q-Bank (PDF)", export_question_bank_pdf(st.session_state.question_bank),
                                   "question_bank.pdf","application/pdf",use_container_width=True)

        c5,c6,c7,c8 = st.columns(4)
        with c5:
            if st.session_state.notes:
                st.download_button("📝 Notes (MD)", export_markdown(st.session_state.notes),
                                   "exam_notes.md","text/markdown",use_container_width=True)
        with c6:
            if st.session_state.flashcards:
                st.download_button("📋 Flashcards (CSV)", export_flashcards_csv(st.session_state.flashcards),
                                   "flashcards.csv","text/csv",use_container_width=True)
        with c7:
            if st.session_state.flashcards:
                st.download_button("🎴 Anki (.txt)", export_anki(st.session_state.flashcards),
                                   "flashcards_anki.txt","text/plain",use_container_width=True)
        with c8:
            if st.session_state.question_bank:
                st.download_button("📊 Q-Bank (CSV)", export_question_bank_csv(st.session_state.question_bank),
                                   "question_bank.csv","text/csv",use_container_width=True)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">ExamNotes AI · Powered by Gemini 2.5 Flash</div>
""", unsafe_allow_html=True)
