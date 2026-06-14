"""
doc_generator.py — PDF document generation using Jinja2 + fpdf2.
Generates offer letters, employment contracts, NDAs from HTML templates.
"""
import io
import os
import logging
from datetime import datetime
from typing import Optional
from jinja2 import Environment, FileSystemLoader, Template

from fpdf import FPDF

logger = logging.getLogger("successcore.doc_generator")

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")
_jinja_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

TEMPLATE_DEFS = {
    "offer_letter": {
        "name": "Job Offer Letter",
        "filename": "offer_letter.html",
        "required": ["employee_name", "company_name", "position", "start_date", "salary"],
        "optional": ["department", "manager_name", "location", "employment_type", "bonus", "equity", "benefits", "additional_terms", "offer_expiry"],
    },
    "employment_contract": {
        "name": "Employment Contract",
        "filename": "employment_contract.html",
        "required": ["employee_name", "company_name", "position", "start_date", "salary", "jurisdiction"],
        "optional": ["department", "manager_name", "notice_period", "bonus", "equity"],
    },
    "nda": {
        "name": "Non-Disclosure Agreement",
        "filename": "nda.html",
        "required": ["employee_name", "company_name", "purpose", "jurisdiction"],
        "optional": ["duration"],
    },
}


def get_available_templates() -> list[dict]:
    return [
        {"id": key, "name": val["name"], "required": val["required"], "optional": val["optional"]}
        for key, val in TEMPLATE_DEFS.items()
    ]


def render_html(template_type: str, variables: dict) -> str:
    if template_type not in TEMPLATE_DEFS:
        raise ValueError(f"Unknown template: {template_type}")

    defn = TEMPLATE_DEFS[template_type]
    template = _jinja_env.get_template(defn["filename"])

    defaults = {
        "date": datetime.now().strftime("%B %d, %Y"),
        "department": "General",
        "manager_name": "Management",
        "location": "Remote",
        "employment_type": "Full-time",
        "notice_period": "30 days",
        "offer_expiry": "7 days from date of offer",
        "duration": "3 years",
        "jurisdiction": "Delaware, USA",
        "benefits": "Health insurance, 401(k), paid time off",
        "purpose": "Employment evaluation and business relationship discussion",
    }
    defaults.update(variables)
    return template.render(**defaults)


def generate_pdf(template_type: str, variables: dict) -> bytes:
    """Generate PDF from HTML template. Returns PDF bytes."""
    html = render_html(template_type, variables)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Use built-in font with Unicode support
    pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
    pdf.add_font("DejaVu", "B", "DejaVuSans-Bold.ttf", uni=True)
    pdf.set_font("DejaVu", "", 10)
    pdf.write_html(html)

    return pdf.output()


async def generate_document(template_type: str, variables: dict) -> bytes:
    """Async wrapper for PDF generation."""
    return generate_pdf(template_type, variables)
