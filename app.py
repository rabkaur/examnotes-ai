"""
app.py
ExamNotes AI — Main Streamlit Application.
Handles file upload, processing pipeline, and results display.
All AI outputs are stored in st.session_state to survive Streamlit reruns.
"""

import streamlit as st
import os
import tempfile
import time
from services.file_parser import extract_all
from services.note_generator import run_note_generator
from services.pyq_analyzer import run_pyq_analyzer
from services.flashcard_generator import run_flashcard_generator
from services.question_bank_generator import run_question_bank_generator
from services.exporter import (
    export_markdown,
    export_pdf,
    export_flashcards_csv,
    export_anki,
    export_question_bank_csv,
)

st.set_page_config(
    page_title="ExamNotes AI",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "notes" not in st.session_state:
    st.session_state.notes = ""
if "pyq_report" not in st.session_state:
    st.session_state.pyq_report = ""
if "flashcards" not in st.session_state:
    st.session_state.flashcards = []
if "study_content" not in st.session_state:
    st.session_state.study_content = ""
if "pyq_content" not in st.session_state:
    st.session_state.pyq_content = ""
if "processing_done" not in st.session_state:
    st.session_state.processing_done = False
if "question_bank" not in st.session_state:
    st.session_state.question_bank = []

st.markdown("""
<style>
/* ── Force light mode ── */
html, body, [data-testid="stAppViewContainer"],
[data-testid="stApp"] {
    background-color: #F8FAFC !important;
    color: #1E293B !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stToolbar"] {visibility: hidden;}
[data-testid="stDecoration"] {display: none;}
[data-testid="stDecorationColorBackground"] {display: none;}
div[data-testid="stToolbarActions"] {display: none;}
[data-testid="manage-app-button"] {display: none;}
[data-testid="stStatusWidget"] {display: none;}
.viewerBadge_container__1QSob {display: none;}
.viewerBadge_link__1S137 {display: none;}
._container_gzau3_1 {display: none !important;}
._viewerBadge_nim44_23 {display: none !important;}
a[href*="streamlit.io"] {display: none !important;}
.egzxvld1 {display: none;}
.e1vs0wn31 {display: none;}
.st-emotion-cache-1wbqy5l {display: none;}
.st-emotion-cache-zq5wmm {display: none;}
.st-emotion-cache-15ecox0 {display: none;}
[data-testid="stSidebar"] {display: none !important;}

/* ── Page layout ── */
.block-container {
    padding-top: 0 !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    padding-bottom: 2rem !important;
    max-width: 1200px !important;
}

/* ── Top navbar ── */
.navbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1.2rem 0;
    margin-bottom: 2rem;
    border-bottom: 1px solid #E2E8F0;
}
.navbar-logo {
    font-size: 1.1rem;
    font-weight: 700;
    color: #1E293B;
    letter-spacing: -0.3px;
}
.navbar-badge {
    background: #F0FDF9;
    color: #0D9488;
    border: 1px solid #99F6E4;
    border-radius: 20px;
    padding: 0.25rem 0.85rem;
    font-size: 0.8rem;
    font-weight: 600;
}

/* ── Hero text ── */
.hero-title {
    font-size: 2.2rem;
    font-weight: 700;
    color: #1E293B;
    margin-bottom: 0.4rem;
    line-height: 1.2;
}
.hero-sub {
    font-size: 1rem;
    color: #475569;
    margin-bottom: 2rem;
}

/* ── Section labels ── */
.card-title {
    font-size: 0.72rem;
    font-weight: 700;
    color: #0D9488;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.3rem;
}
.card-sub {
    font-size: 0.9rem;
    color: #475569;
    margin-bottom: 1rem;
}

/* ── Upload zone ── */
[data-testid="stFileUploader"] {
    border: 2px dashed #CBD5E1 !important;
    border-radius: 12px !important;
    background: #FFFFFF !important;
    padding: 1rem !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: #0D9488 !important;
}

/* ── Generate button ── */
div[data-testid="stButton"] > button[kind="primary"] {
    background-color: #1E293B !important;
    border: none !important;
    border-radius: 10px !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    color: white !important;
    padding: 0.65rem 2rem !important;
    width: 100% !important;
    transition: background 0.2s !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background-color: #0F172A !important;
}

/* ── How it works card ── */
.how-card {
    background: #F0FDF9;
    border: 1px solid #99F6E4;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-top: 1rem;
}
.how-title {
    font-size: 0.7rem;
    font-weight: 700;
    color: #0D9488;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.8rem;
}
.how-item {
    font-size: 0.88rem;
    color: #334155;
    padding: 0.3rem 0;
    border-bottom: 1px solid #CCFBF1;
    line-height: 1.5;
}
.how-item:last-child {
    border-bottom: none;
}

/* ── Results section ── */
.results-header {
    font-size: 1.6rem;
    font-weight: 700;
    color: #1E293B;
    margin: 2rem 0 1rem;
}

/* ── Tabs ── */
button[data-baseweb="tab"] {
    font-size: 0.88rem;
    font-weight: 500;
    color: #64748B;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #0D9488 !important;
    border-bottom: 2px solid #0D9488 !important;
    font-weight: 600 !important;
}

/* ── Metrics ── */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
[data-testid="stMetricLabel"] {
    font-size: 0.8rem;
    color: #64748B !important;
}
[data-testid="stMetricValue"] {
    color: #0D9488 !important;
    font-weight: 700 !important;
}

/* ── Expanders ── */
[data-testid="stExpander"] {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 8px !important;
    margin-bottom: 0.4rem !important;
}
[data-testid="stExpander"]:hover {
    border-color: #0D9488 !important;
}

/* ── Download buttons ── */
div[data-testid="stDownloadButton"] > button {
    border: 1.5px solid #0D9488 !important;
    color: #0D9488 !important;
    background: transparent !important;
    border-radius: 8px !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    transition: all 0.2s !important;
}
div[data-testid="stDownloadButton"] > button:hover {
    background: #0D9488 !important;
    color: white !important;
}

/* ── Divider ── */
hr {
    border-color: #E2E8F0 !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] {
    border-radius: 10px !important;
}

/* ── Footer ── */
.footer {
    text-align: center;
    padding: 1.5rem 0 0.5rem;
    color: #94A3B8;
    font-size: 0.82rem;
    border-top: 1px solid #E2E8F0;
    margin-top: 2rem;
}

/* ── General text color fix for light mode ── */
p, li, label, .stMarkdown {
    color: #1E293B !important;
}
h1, h2, h3, h4 {
    color: #1E293B !important;
}
</style>
""", unsafe_allow_html=True)

# ── Navbar ──
st.markdown("""
<div class="navbar">
    <span class="navbar-logo">📚 ExamNotes AI</span>
    <span class="navbar-badge">● Free to use</span>
</div>
""", unsafe_allow_html=True)

# ── Hero ──
st.markdown("""
<div style="margin-bottom: 2rem;">
    <div class="hero-title">ExamNotes AI</div>
    <div class="hero-sub">
        Upload study material and get structured, exam-ready notes.
    </div>
</div>
""", unsafe_allow_html=True)

# ── Upload section ──
st.markdown("""
<div style="margin-bottom: 0.8rem;">
    <div class="card-title">Study material</div>
    <div class="card-sub">Drop your files to generate notes.</div>
</div>
""", unsafe_allow_html=True)

col_upload, col_pyq = st.columns([2, 1])

with col_upload:
    uploaded_files = st.file_uploader(
        label="Upload your files (PDF, PPTX, DOCX, TXT)",
        type=["pdf", "pptx", "docx", "txt"],
        accept_multiple_files=True,
        help="You can upload multiple files at once",
    )

pyq_selections = {}
with col_pyq:
    st.markdown("""
    <div class="card-title">Tag question papers</div>
    <div class="card-sub">Mark files as previous year papers.</div>
    """, unsafe_allow_html=True)
    if uploaded_files:
        for uploaded_file in uploaded_files:
            pyq_selections[f"pyq_{uploaded_file.name}"] = st.checkbox(
                uploaded_file.name,
                key=f"pyq_{uploaded_file.name}",
            )
    else:
        st.caption("No files uploaded yet.")

    st.markdown("""
    <div class="how-card">
        <div class="how-title">How it works</div>
        <div class="how-item">— AI structures your content into revision-ready sections</div>
        <div class="how-item">— Supports PDF, PPTX, DOCX and plain text</div>
        <div class="how-item">— Tag question papers for PYQ analysis</div>
        <div class="how-item">— Download notes, flashcards, and question banks</div>
    </div>
    """, unsafe_allow_html=True)

if uploaded_files and st.button(
    "🚀 Generate Notes", type="primary", use_container_width=True
):
    try:
        tmp_dir = tempfile.mkdtemp()
        saved_paths = []
        for file in uploaded_files:
            path = os.path.join(tmp_dir, file.name)
            with open(path, "wb") as f:
                f.write(file.getbuffer())
            saved_paths.append(path)

        pyq_flags = {
            path: pyq_selections.get(f"pyq_{file.name}", False)
            for file, path in zip(uploaded_files, saved_paths)
        }

        with st.spinner("Extracting text from files..."):
            extracted = extract_all(saved_paths, pyq_flags)
            st.session_state.study_content = extracted["study_content"]
            st.session_state.pyq_content = extracted["pyq_content"]

        with st.spinner("Generating exam notes with Groq AI..."):
            st.session_state.notes = run_note_generator(
                st.session_state.study_content
            )

        time.sleep(15)

        if st.session_state.pyq_content:
            with st.spinner("Analyzing previous year questions..."):
                st.session_state.pyq_report = run_pyq_analyzer(
                    st.session_state.pyq_content,
                    st.session_state.study_content,
                )
            time.sleep(15)
        else:
            st.session_state.pyq_report = ""

        with st.spinner("Generating flashcards..."):
            st.session_state.flashcards = run_flashcard_generator(
                st.session_state.study_content
            )

        time.sleep(15)

        with st.spinner("Generating question bank..."):
            st.session_state.question_bank = run_question_bank_generator(
                st.session_state.study_content
            )

        st.session_state.processing_done = True
        st.success("✅ Done! Your study package is ready below.")
        st.balloons()

    except Exception as e:
        st.error(f"Something went wrong: {e}")

if st.session_state.processing_done:
    st.markdown("""
    <div class="results-header">Your Study Package</div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 Exam Notes",
        "📊 PYQ Analysis",
        "🃏 Flashcards",
        "❓ Question Bank",
        "📈 Stats",
    ])

    with tab1:
        if st.session_state.notes:
            st.markdown(st.session_state.notes)
        else:
            st.info("No notes generated yet.")

    with tab2:
        if st.session_state.pyq_report:
            st.markdown(st.session_state.pyq_report)
        else:
            st.info(
                "No question papers were uploaded or tagged. Upload a PYQ file "
                "and tag it as a question paper to see analysis here."
            )

    with tab3:
        if st.session_state.flashcards:
            st.markdown(
                f"**{len(st.session_state.flashcards)} flashcards generated**"
            )
            for card in st.session_state.flashcards:
                difficulty = card.get("difficulty", "easy")
                with st.expander(
                    f"[{difficulty.upper()}] {card.get('question', '')}"
                ):
                    st.markdown(f"**Answer:** {card.get('answer', '')}")
                    st.caption(f"Topic: {card.get('topic', '')}")
        else:
            st.info("No flashcards generated yet.")

    with tab4:
        if st.session_state.question_bank:
            questions = st.session_state.question_bank

            two_mark = [q for q in questions if q.get("marks") == 2]
            five_mark = [q for q in questions if q.get("marks") == 5]
            ten_mark = [q for q in questions if q.get("marks") == 10]

            col1, col2, col3 = st.columns(3)
            col1.metric("2-Mark Questions", len(two_mark))
            col2.metric("5-Mark Questions", len(five_mark))
            col3.metric("10-Mark Questions", len(ten_mark))

            st.divider()

            if two_mark:
                st.markdown("### ✏️ 2-Mark Questions")
                for i, q in enumerate(two_mark, 1):
                    with st.expander(f"Q{i}. {q.get('question', '')}"):
                        st.markdown(f"**Topic:** {q.get('topic', '')}")
                        st.markdown(f"**Answer Hint:** {q.get('answer_hint', '')}")

            if five_mark:
                st.markdown("### 📝 5-Mark Questions")
                for i, q in enumerate(five_mark, 1):
                    with st.expander(f"Q{i}. {q.get('question', '')}"):
                        st.markdown(f"**Topic:** {q.get('topic', '')}")
                        st.markdown(f"**Answer Hint:** {q.get('answer_hint', '')}")

            if ten_mark:
                st.markdown("### 📋 10-Mark Questions")
                for i, q in enumerate(ten_mark, 1):
                    with st.expander(f"Q{i}. {q.get('question', '')}"):
                        st.markdown(f"**Topic:** {q.get('topic', '')}")
                        st.markdown(f"**Answer Hint:** {q.get('answer_hint', '')}")
        else:
            st.info("No question bank generated yet.")

    with tab5:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "📄 Characters Processed",
                f"{len(st.session_state.study_content):,}",
            )
        with col2:
            st.metric(
                "🃏 Flashcards Generated",
                len(st.session_state.flashcards),
            )
        with col3:
            st.metric(
                "📋 PYQ Content Found",
                "Yes" if st.session_state.pyq_content else "No",
            )
        st.metric(
            "❓ Questions Generated",
            value=len(st.session_state.question_bank),
        )
        st.markdown("**Content Preview**")
        st.text_area(
            "Extracted study content (first 1000 chars)",
            value=st.session_state.study_content[:1000],
            height=200,
            disabled=True,
        )

    st.divider()
    st.markdown("""
    <div style="margin: 1rem 0 0.5rem;">
        <div class="card-title">Downloads</div>
        <div class="card-sub">All files generated from your uploaded study material.</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        if st.session_state.notes:
            st.download_button(
                label="📄 Notes (MD)",
                data=export_markdown(st.session_state.notes),
                file_name="exam_notes.md",
                mime="text/markdown",
                use_container_width=True,
            )

    with col2:
        if st.session_state.notes:
            pdf_data = export_pdf(st.session_state.notes)
            if pdf_data:
                st.download_button(
                    label="📕 Notes (PDF)",
                    data=pdf_data,
                    file_name="exam_notes.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            else:
                st.caption("PDF unavailable")

    with col3:
        if st.session_state.flashcards:
            st.download_button(
                label="📊 Flashcards (CSV)",
                data=export_flashcards_csv(st.session_state.flashcards),
                file_name="flashcards.csv",
                mime="text/csv",
                use_container_width=True,
            )

    with col4:
        if st.session_state.flashcards:
            st.download_button(
                label="🃏 Flashcards (Anki)",
                data=export_anki(st.session_state.flashcards),
                file_name="flashcards_anki.txt",
                mime="text/plain",
                use_container_width=True,
            )

    with col5:
        if st.session_state.question_bank:
            st.download_button(
                label="❓ Questions (CSV)",
                data=export_question_bank_csv(
                    st.session_state.question_bank
                ),
                file_name="question_bank.csv",
                mime="text/csv",
                use_container_width=True,
            )

st.markdown("""
<div class="footer">
    ExamNotes AI · Built with Streamlit + Groq ·
    <span style="color:#0D9488">Free to use</span>
</div>
""", unsafe_allow_html=True)