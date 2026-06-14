import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger("successcore.invoice_pdf")

FPDF_AVAILABLE = False
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    logger.warning("fpdf2 not installed. pip install fpdf2>=2.8.0")


COMPANY_NAME = "SuccessCore HR"
COMPANY_ADDRESS = "Calle Principal 123, Planta 4\n28001 Madrid, Spain"
COMPANY_EMAIL = "billing@successcore.com"
COMPANY_PHONE = "+34 910 000 000"
COMPANY_TAX_ID = "ES-B00000000"
COMPANY_IBAN = "ES91 2100 0418 4502 0005 1332"
COMPANY_BIC = "CAIXESBBXXX"


async def generate_invoice_pdf(
    invoice_data: dict,
    tenant_id: str,
    db_session=None,
) -> bytes:
    if not FPDF_AVAILABLE:
        return f"Error: fpdf2 not available".encode("utf-8")

    try:
        logo_path = await _get_tenant_logo_path(tenant_id, db_session)

        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        _draw_header(pdf, logo_path)

        invoice_number = invoice_data.get("invoice_number", "INV-0001")
        date_str = _format_date(invoice_data.get("date", ""))
        due_date_str = _format_date(invoice_data.get("due_date", ""))
        currency = invoice_data.get("currency", "USD")
        customer_name = invoice_data.get("customer_name", "")
        customer_email = invoice_data.get("customer_email", "")
        customer_address = invoice_data.get("customer_address", "")
        line_items = invoice_data.get("line_items", [])
        tax_rate = invoice_data.get("tax_rate")
        notes = invoice_data.get("notes", "")
        payment_terms = invoice_data.get("payment_terms", "")

        _draw_invoice_meta(pdf, invoice_number, date_str, due_date_str, currency)

        pdf.ln(4)
        _draw_billing_section(pdf, customer_name, customer_email, customer_address)

        pdf.ln(6)
        subtotal = _draw_line_items_table(pdf, line_items, currency)

        tax_amount = 0.0
        if tax_rate is not None and tax_rate > 0:
            tax_amount = round(subtotal * tax_rate, 2)

        total = round(subtotal + tax_amount, 2)

        _draw_totals(pdf, subtotal, tax_rate, tax_amount, total, currency)

        _draw_payment_section(pdf, payment_terms or notes)

        pdf.set_y(-30)
        pdf.set_font("Helvetica", "I", 7)
        pdf.set_text_color(140, 140, 140)
        pdf.cell(0, 4, f"SuccessCore Platform - Invoice generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC", align="C")

        return pdf.output()

    except Exception as e:
        logger.error(f"Error generating invoice PDF: {e}")
        import traceback
        traceback.print_exc()
        return f"Error generating invoice PDF: {e}".encode("utf-8")


def _draw_header(pdf: FPDF, logo_path: Optional[str]):
    pdf.set_fill_color(30, 30, 46)
    pdf.rect(0, 0, 210, 40, "F")

    if logo_path and os.path.isfile(logo_path):
        try:
            pdf.image(logo_path, x=10, y=4, h=16)
        except Exception:
            pass

    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_y(8)
    pdf.cell(0, 10, COMPANY_NAME, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(200, 200, 210)
    pdf.cell(0, 5, COMPANY_ADDRESS.replace("\n", "  |  ").replace("Calle Principal 123, Planta 4   |  28001 Madrid, Spain", f"{COMPANY_TAX_ID}  |  {COMPANY_EMAIL}"), align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(46)
    pdf.set_text_color(0, 0, 0)


def _draw_invoice_meta(pdf: FPDF, invoice_number: str, date_str: str, due_date_str: str, currency: str):
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(30, 30, 46)
    pdf.cell(0, 10, "INVOICE", align="L", new_x="LMARGIN", new_y="NEXT")

    pdf.set_draw_color(30, 30, 46)
    pdf.set_line_width(0.6)
    y = pdf.get_y()
    pdf.line(10, y, 200, y)
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 60)

    meta_items = [
        ("Invoice Number", invoice_number),
        ("Invoice Date", date_str),
        ("Due Date", due_date_str),
        ("Currency", currency),
    ]

    for label, value in meta_items:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(40, 6, f"{label}:")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, value, new_x="LMARGIN", new_y="NEXT")


def _draw_billing_section(pdf: FPDF, customer_name: str, customer_email: str, customer_address: str):
    pdf.set_fill_color(245, 245, 250)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 30, 46)
    pdf.cell(0, 8, "  BILL TO", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_text_color(40, 40, 40)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, customer_name, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 5, customer_email, new_x="LMARGIN", new_y="NEXT")

    if customer_address:
        for line in customer_address.strip().split("\n"):
            pdf.cell(0, 5, line, new_x="LMARGIN", new_y="NEXT")


def _draw_line_items_table(pdf: FPDF, line_items: list, currency: str) -> float:
    pdf.set_fill_color(30, 30, 46)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)

    col_desc = 82
    col_qty = 24
    col_price = 30
    col_amount = 30

    pdf.cell(col_desc, 8, "  Description", border=1, fill=True)
    pdf.cell(col_qty, 8, "Qty", border=1, fill=True, align="C")
    pdf.cell(col_price, 8, "Unit Price", border=1, fill=True, align="R")
    pdf.cell(col_amount, 8, "Amount", border=1, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(40, 40, 40)
    pdf.set_font("Helvetica", "", 9)

    subtotal = 0.0
    alt_fill = False

    for item in line_items:
        if alt_fill:
            pdf.set_fill_color(248, 248, 252)
        else:
            pdf.set_fill_color(255, 255, 255)

        description = item.get("description", "")
        quantity = item.get("quantity", 0)
        unit_price = item.get("unit_price", 0.0)
        line_amount = round(quantity * unit_price, 2)
        subtotal += line_amount

        pdf.cell(col_desc, 7, f"  {description[:60]}", border=1, fill=True)
        pdf.cell(col_qty, 7, str(quantity), border=1, fill=True, align="C")
        pdf.cell(col_price, 7, f"{unit_price:,.2f} {currency}", border=1, fill=True, align="R")
        pdf.cell(col_amount, 7, f"{line_amount:,.2f} {currency}", border=1, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")

        alt_fill = not alt_fill

    return round(subtotal, 2)


def _draw_totals(pdf: FPDF, subtotal: float, tax_rate: Optional[float], tax_amount: float, total: float, currency: str):
    pdf.ln(4)

    available_width = 190
    right_align_x = 10 + 82 + 24
    label_col = 30
    value_col = 30

    totals_start_x = right_align_x

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 60)

    pdf.set_x(totals_start_x)
    pdf.cell(label_col, 6, "Subtotal:", align="R")
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(value_col, 6, f"{subtotal:,.2f} {currency}", align="R", new_x="LMARGIN", new_y="NEXT")

    if tax_rate is not None and tax_rate > 0:
        pdf.set_x(totals_start_x)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(label_col, 6, f"Tax ({tax_rate * 100:.0f}%):", align="R")
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(value_col, 6, f"{tax_amount:,.2f} {currency}", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_draw_color(30, 30, 46)
    pdf.set_line_width(0.4)
    y_line = pdf.get_y()
    pdf.line(totals_start_x, y_line, totals_start_x + label_col + value_col, y_line)
    pdf.ln(1)

    pdf.set_x(totals_start_x)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 30, 46)
    pdf.cell(label_col, 8, "TOTAL:", align="R")
    pdf.cell(value_col, 8, f"{total:,.2f} {currency}", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(40, 40, 40)


def _draw_payment_section(pdf: FPDF, payment_terms: str):
    pdf.ln(10)
    pdf.set_fill_color(245, 245, 250)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 30, 46)
    pdf.cell(0, 8, "  PAYMENT INFORMATION", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(60, 60, 60)

    bank_details = [
        f"Bank: CaixaBank",
        f"Account Holder: {COMPANY_NAME}",
        f"IBAN: {COMPANY_IBAN}",
        f"BIC / SWIFT: {COMPANY_BIC}",
        f"Tax ID: {COMPANY_TAX_ID}",
    ]

    for line in bank_details:
        pdf.cell(0, 5, line, new_x="LMARGIN", new_y="NEXT")

    if payment_terms:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 5, "Payment Terms:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, payment_terms)


def _format_date(iso_string: str) -> str:
    if not iso_string:
        return ""
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y")
    except (ValueError, AttributeError):
        return iso_string


async def _get_tenant_logo_path(tenant_id: str, db_session=None) -> Optional[str]:
    if db_session is None:
        return None
    try:
        from sqlalchemy import select
        from app.models.tenant import Tenant

        result = await db_session.execute(
            select(Tenant.logo_url).where(Tenant.schema_name == tenant_id)
        )
        logo_url = result.scalar_one_or_none()
        if logo_url and os.path.isfile(logo_url):
            return logo_url
    except Exception:
        pass
    return None
