"""
Export component — JSON, CSV, PDF export functionality.
"""

import json
import csv
import io
import streamlit as st
from datetime import datetime


def render_export_buttons(report: dict, analyzed_results: list) -> None:
    """
    Render export buttons for JSON, CSV, and PDF.

    Args:
        report: The complete report dict.
        analyzed_results: List of analyzed result dicts.
    """
    st.markdown("### :arrow_down: Export Report")

    col1, col2, col3 = st.columns(3)

    company = report.get("company", "company")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename_base = f"{company.lower().replace(' ', '_')}_{timestamp}"

    with col1:
        # JSON export
        json_str = json.dumps(report, indent=2, ensure_ascii=False)
        st.download_button(
            label=":page_facing_up: Download JSON",
            data=json_str,
            file_name=f"{filename_base}_report.json",
            mime="application/json",
            use_container_width=True,
        )

    with col2:
        # CSV export
        csv_data = _generate_csv(analyzed_results)
        st.download_button(
            label=":chart_with_upwards_trend: Download CSV",
            data=csv_data,
            file_name=f"{filename_base}_results.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col3:
        # PDF export
        pdf_data = _generate_pdf(report)
        st.download_button(
            label=":closed_book: Download PDF",
            data=pdf_data,
            file_name=f"{filename_base}_summary.pdf",
            mime="application/pdf",
            use_container_width=True,
        )


def _generate_csv(results: list) -> str:
    """Generate CSV from analyzed results."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Source Platform",
        "Source URL",
        "Sentiment",
        "Confidence",
        "Reviewer Type",
        "Themes",
        "Severity",
        "Language",
        "Date",
        "Raw Text (truncated)",
    ])

    for r in results:
        writer.writerow([
            r.get("source_platform", ""),
            r.get("source_url", ""),
            r.get("sentiment", ""),
            r.get("confidence", ""),
            r.get("reviewer_type", ""),
            "; ".join(r.get("themes", [])),
            r.get("severity", ""),
            r.get("language_detected", ""),
            r.get("date", ""),
            r.get("raw_text", "")[:200],
        ])

    return output.getvalue()


def _generate_pdf(report: dict) -> bytes:
    """Generate a PDF summary report."""
    try:
        from fpdf import FPDF
    except ImportError:
        return b"PDF generation requires fpdf2. Install with: pip install fpdf2"

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 15, "Company Career Scout Report", ln=True, align="C")
    pdf.ln(5)

    # Company info
    pdf.set_font("Helvetica", "B", 14)
    company = report.get("company", "Unknown")
    pdf.cell(0, 10, f"Company: {company}", ln=True)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Generated: {report.get('generated_at', '')}", ln=True)
    pdf.cell(0, 6, f"Model: {report.get('model_used', '')}", ln=True)
    pdf.cell(0, 6, f"Total Results: {report.get('total_results', 0)}", ln=True)
    pdf.ln(5)

    # Overall Score
    score = report.get("overall_score", 0)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Overall Score: {score}/100", ln=True)
    pdf.ln(5)

    # Summary
    summary = report.get("aggregated_summary", {})

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "What Employees Say:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    _pdf_multi_cell(pdf, summary.get("what_employees_say", "N/A"))
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "What Customers Say:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    _pdf_multi_cell(pdf, summary.get("what_customers_say", "N/A"))
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "What Press Says:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    _pdf_multi_cell(pdf, summary.get("what_press_says", "N/A"))
    pdf.ln(5)

    # Pros
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Top Pros:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    for pro in summary.get("top_5_pros", []):
        pdf.cell(0, 6, f"  + {pro}", ln=True)
    pdf.ln(3)

    # Cons
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Top Cons:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    for con in summary.get("top_5_cons", []):
        pdf.cell(0, 6, f"  - {con}", ln=True)
    pdf.ln(3)

    # Crisis flags
    crisis = summary.get("crisis_flags", [])
    if crisis:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(220, 38, 38)
        pdf.cell(0, 8, "CRISIS FLAGS:", ln=True)
        pdf.set_font("Helvetica", "", 10)
        for flag in crisis:
            pdf.cell(0, 6, f"  ! {flag}", ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(3)

    # Recommendation
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Recommendation:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    _pdf_multi_cell(pdf, summary.get("recommendation", "N/A"))

    # Source breakdown
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Results by Source", ln=True)
    pdf.ln(3)

    by_source = report.get("by_source", {})
    for source_key, source_data in by_source.items():
        platform = source_data.get("platform", source_key)
        count = source_data.get("result_count", 0)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, f"{platform}: {count} results", ln=True)

        sentiment = source_data.get("sentiment_breakdown", {})
        if sentiment:
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(
                0, 5,
                f"  Positive: {sentiment.get('positive', 0)} | "
                f"Neutral: {sentiment.get('neutral', 0)} | "
                f"Negative: {sentiment.get('negative', 0)}",
                ln=True,
            )
        pdf.ln(2)

    return pdf.output()


def _pdf_multi_cell(pdf, text: str, width: int = 0, height: int = 6):
    """Write multi-line text to PDF, handling encoding."""
    try:
        # Replace problematic characters
        safe_text = text.encode("latin-1", errors="replace").decode("latin-1")
        pdf.multi_cell(width, height, safe_text)
    except Exception:
        pdf.multi_cell(width, height, "Text could not be rendered.")
