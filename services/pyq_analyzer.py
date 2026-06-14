"""
pyq_analyzer.py
Thin wrapper around ai_service.analyze_pyq().
Returns a Markdown PYQ analysis report.
"""

from services.ai_service import analyze_pyq


def run_pyq_analyzer(pyq_content: str, study_content: str) -> str:
    """Calls AI service to analyze previous year question papers."""
    if not pyq_content.strip():
        return "# No question paper content provided."
    return analyze_pyq(pyq_content, study_content)
