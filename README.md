# ExamNotes AI

Convert messy university study material into structured,
exam-ready notes powered by AI.

## Tech Stack
- Frontend: Streamlit
- AI: Groq API — llama-3.3-70b-versatile (free tier)
- File parsing: PyMuPDF, python-pptx, python-docx
- PDF export: WeasyPrint

## Features
- Upload PDF, PPTX, DOCX, TXT files
- AI-generated structured exam notes
- Previous year question paper analysis
- Flashcard generator (CSV + Anki export)
- Question bank (2, 5, 10 mark questions)
- Download notes as Markdown or PDF

## Setup

1. Clone the repo
2. python -m venv venv
3. source venv/bin/activate
4. pip install -r requirements.txt
5. Add your Groq API key to .env:
   GROQ_API_KEY=your_key_here
6. streamlit run app.py

## Get a Free Groq API Key
Visit https://console.groq.com — free, no billing required.

## Status
- [x] Phase 1: Scaffold + file parsing
- [x] Phase 2: AI integration (Groq)
- [x] Phase 3: Streamlit UI
- [x] Phase 4: Question bank + PYQ analysis
- [x] Phase 5: Exports + deployment
