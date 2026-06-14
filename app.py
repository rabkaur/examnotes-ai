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

/* ── Page spacing ── */
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1100px;
}

/* ── Hero header ── */
.hero {
    background: linear-gradient(135deg, #0D9488 0%, #0F766E 100%);
    border-radius: 16px;
    padding: 2.5rem 2rem;
    margin-bottom: 2rem;
}
.hero h1 {
    color: #ffffff;
    font-size: 2.4rem;
    font-weight: 700;
    margin: 0 0 0.4rem 0;
}
.hero p {
    color: #CCFBF1;
    font-size: 1.05rem;
    margin: 0;
}

/* ── Section cards ── */
.section-card {
    background: rgba(13, 148, 136, 0.06);
    border: 1px solid rgba(13, 148, 136, 0.2);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
}

/* ── Upload label ── */
.upload-label {
    font-size: 1rem;
    font-weight: 600;
    color: #0D9488;
    margin-bottom: 0.5rem;
}

/* ── Generate button override ── */
div[data-testid="stButton"] > button[kind="primary"] {
    background-color: #0D9488;
    border: none;
    border-radius: 10px;
    font-size: 1rem;
    font-weight: 600;
    padding: 0.65rem 1.5rem;
    color: white;
    transition: background 0.2s;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background-color: #0F766E;
}

/* ── Tab styling ── */
button[data-baseweb="tab"] {
    font-size: 0.9rem;
    font-weight: 500;
    color: #94A3B8;
    border-radius: 8px 8px 0 0;
    padding: 0.5rem 1rem;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #0D9488 !important;
    border-bottom: 2px solid #0D9488 !important;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: rgba(13, 148, 136, 0.08);
    border: 1px solid rgba(13, 148, 136, 0.15);
    border-radius: 10px;
    padding: 1rem;
}
[data-testid="stMetricLabel"] {
    font-size: 0.8rem;
    color: #94A3B8;
}
[data-testid="stMetricValue"] {
    color: #0D9488;
    font-weight: 700;
}

/* ── Expander styling ── */
[data-testid="stExpander"] {
    border: 1px solid rgba(13, 148, 136, 0.15);
    border-radius: 8px;
    margin-bottom: 0.4rem;
}
[data-testid="stExpander"]:hover {
    border-color: #0D9488;
}

/* ── Download buttons ── */
div[data-testid="stDownloadButton"] > button {
    border: 1.5px solid #0D9488;
    color: #0D9488;
    background: transparent;
    border-radius: 8px;
    font-size: 0.85rem;
    font-weight: 500;
    transition: all 0.2s;
}
div[data-testid="stDownloadButton"] > button:hover {
    background: #0D9488;
    color: white;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    border-right: 1px solid rgba(13, 148, 136, 0.15);
}

/* ── Divider color ── */
hr {
    border-color: rgba(13, 148, 136, 0.15) !important;
}

/* ── Success message ── */
[data-testid="stAlert"] {
    border-radius: 10px;
}

/* ── Flashcard difficulty colors ── */
.easy { border-left: 3px solid #0D9488; }
.medium { border-left: 3px solid #F59E0B; }
.hard { border-left: 3px solid #EF4444; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <h1>📚 ExamNotes AI</h1>
    <p>Upload your study material and get structured, exam-ready notes powered by AI.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("### 📁 Upload Study Material")
st.markdown(
    "<p style='color:#94A3B8;font-size:0.9rem;margin-top:-0.8rem'>"
    "Supports PDF, PPTX, DOCX and TXT — upload multiple files at once.</p>",
    unsafe_allow_html=True
)

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
    st.markdown("**📌 Tag Question Papers**")
    st.markdown("Check any file that is a previous year question paper:")
    if uploaded_files:
        for uploaded_file in uploaded_files:
            pyq_selections[f"pyq_{uploaded_file.name}"] = st.checkbox(
                uploaded_file.name,
                key=f"pyq_{uploaded_file.name}",
            )

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
    st.divider()
    st.markdown("### 📖 Your Study Package")

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
    st.markdown("### ⬇️ Download Your Study Package")
    st.markdown(
        "<p style='color:#94A3B8;font-size:0.9rem;margin-top:-0.8rem'>"
        "All files generated from your uploaded study material.</p>",
        unsafe_allow_html=True
    )

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

with st.sidebar:
    st.markdown("""
    <div style='padding:0.5rem 0'>
        <h2 style='color:#0D9488;font-size:1.1rem;margin-bottom:1rem'>
            📚 ExamNotes AI
        </h2>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**ℹ️ How to Use**")
    st.markdown("""
    1. Upload your study files
    2. Tag any question papers as PYQ
    3. Click **Generate Notes**
    4. View notes, analysis, and flashcards
    5. Download your study package
    """)

    st.divider()

    st.markdown("**📋 Supported Formats**")
    st.markdown("""
    | Format | Extension |
    |--------|-----------|
    | PDF | .pdf |
    | PowerPoint | .pptx |
    | Word | .docx |
    | Text | .txt |
    """)

    st.divider()

    st.markdown(
        "<p style='color:#0D9488;font-size:0.85rem;font-weight:600'>"
        "⚡ Powered by Groq</p>",
        unsafe_allow_html=True
    )
    st.caption("llama-3.3-70b-versatile · Free tier")

st.markdown("""
<div style='text-align:center;padding:1.5rem 0 0.5rem;
color:#475569;font-size:0.82rem;border-top:1px solid rgba(13,148,136,0.15);
margin-top:1rem'>
    ExamNotes AI · Built with Streamlit + Groq ·
    <span style='color:#0D9488'>Free to use</span>
</div>
""", unsafe_allow_html=True)
