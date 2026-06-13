import os
from datetime import datetime
from app.core.logger import logger

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    logger.warning("fpdf2 no está instalado. pip install fpdf2")
    FPDF_AVAILABLE = False


TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")


def generate_executive_pdf(tenant_name: str, stats: dict) -> bytes:
    """
    Genera un PDF ejecutivo con estadísticas del tenant usando fpdf2.
    Sin dependencias nativas de OS (GTK3/Pango), funciona en Windows, Linux y Docker.
    """
    if not FPDF_AVAILABLE:
        # Fallback: return HTML bytes for debug
        html = f"""
        <html><body>
        <h1>Informe Ejecutivo — {tenant_name}</h1>
        <p>Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Total empleados: {stats.get('total', 0)}</p>
        <p>Activos: {stats.get('active', 0)}</p>
        <p>Instale fpdf2: pip install fpdf2</p>
        </body></html>
        """
        return html.encode('utf-8')

    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # ── Header ────────────────────────────────────────────────────────────
        pdf.set_fill_color(30, 30, 46)  # Dark header bg
        pdf.rect(0, 0, 210, 40, 'F')
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 22)
        pdf.set_y(10)
        pdf.cell(0, 12, f"SuccessCore", align="L", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, f"Informe Ejecutivo  |  {tenant_name}  |  {datetime.now().strftime('%d %b %Y, %H:%M')}", align="L", new_x="LMARGIN", new_y="NEXT")

        pdf.set_y(50)
        pdf.set_text_color(0, 0, 0)

        # ── KPI Summary ──────────────────────────────────────────────────────
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "Resumen de la Plantilla", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        total = stats.get("total", 0)
        active = stats.get("active", 0)
        inactive = total - active

        kpis = [
            ("Total Empleados", str(total)),
            ("Empleados Activos", str(active)),
            ("Empleados Inactivos", str(inactive)),
        ]

        pdf.set_font("Helvetica", "", 11)
        col_w = 60
        for label, value in kpis:
            pdf.set_fill_color(245, 245, 250)
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(col_w, 8, label, border=1, fill=True)
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(col_w, 8, value, border=1, new_x="LMARGIN", new_y="NEXT")

        pdf.ln(8)

        # ── Roles Breakdown ──────────────────────────────────────────────────
        roles = stats.get("roles", [])
        if roles:
            pdf.set_font("Helvetica", "B", 14)
            pdf.cell(0, 10, "Desglose por Rol", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(4)

            pdf.set_fill_color(30, 30, 46)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(90, 8, "Rol", border=1, fill=True)
            pdf.cell(30, 8, "Cantidad", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", "", 10)
            for role in roles:
                name = role.get("role", "Sin rol") if isinstance(role, dict) else str(role)
                count = role.get("count", "-") if isinstance(role, dict) else "-"
                pdf.cell(90, 7, str(name), border=1)
                pdf.cell(30, 7, str(count), border=1, new_x="LMARGIN", new_y="NEXT")

        # ── Footer ────────────────────────────────────────────────────────────
        pdf.ln(15)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 6, f"Generado automaticamente por SuccessCore Platform  |  {datetime.now().isoformat()}", align="C")

        return pdf.output()

    except Exception as e:
        logger.error(f"Error generando PDF con fpdf2: {e}")
        # Fallback to basic text
        return f"Error generando PDF: {e}".encode('utf-8')


def generate_payslip_pdf(tenant_name: str, employee_name: str, period: str, payslip: dict) -> bytes:
    """
    Genera un recibo oficial de salario (nómina) en formato PDF.
    """
    if not FPDF_AVAILABLE:
        return f"Error: fpdf2 is not available".encode('utf-8')
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # Outer border
        pdf.set_draw_color(100, 100, 150)
        pdf.rect(5, 5, 200, 287)
        
        # Header banner (dark blue)
        pdf.set_fill_color(30, 30, 46)
        pdf.rect(5, 5, 200, 35, 'F')
        
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 20)
        pdf.set_y(12)
        pdf.cell(0, 10, "SuccessCore", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 6, f"RECIBO DE SALARIO  |  {tenant_name}", align="C", new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_y(48)
        pdf.set_text_color(0, 0, 0)
        
        # Info Block
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(95, 6, "EMPRESA", new_x="RIGHT", new_y="TOP")
        pdf.cell(95, 6, "EMPLEADO", new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(95, 5, f"Organizacion: {tenant_name}", new_x="RIGHT", new_y="TOP")
        pdf.cell(95, 5, f"Nombre: {employee_name}", new_x="LMARGIN", new_y="NEXT")
        
        pdf.cell(95, 5, "Sede: Sede Central", new_x="RIGHT", new_y="TOP")
        pdf.cell(95, 5, f"ID Empleado: {payslip.get('employee_id', '')}", new_x="LMARGIN", new_y="NEXT")
        
        pdf.cell(95, 5, "Email: info@successcore.com", new_x="RIGHT", new_y="TOP")
        pdf.cell(95, 5, f"Periodo Liquidacion: {period}", new_x="LMARGIN", new_y="NEXT")
        
        pdf.ln(8)
        
        # Separator line
        pdf.set_draw_color(200, 200, 210)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        # Table Header
        pdf.set_fill_color(240, 240, 245)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(120, 8, "Concepto", border=1, fill=True)
        pdf.cell(35, 8, "Devengos (Gross)", border=1, fill=True, align="R")
        pdf.cell(35, 8, "Deducciones", border=1, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_font("Helvetica", "", 9)
        
        # Base Salary Row
        base_salary = payslip.get("gross_salary", 0.0)
        pdf.cell(120, 7, "Salario Base Mensual", border=1)
        pdf.cell(35, 7, f"{base_salary:.2f} EUR", border=1, align="R")
        pdf.cell(35, 7, "-", border=1, align="R", new_x="LMARGIN", new_y="NEXT")
        
        # Deductions Row
        deductions = payslip.get("deductions", 0.0)
        pdf.cell(120, 7, "Impuestos / Retenciones IRPF", border=1)
        pdf.cell(35, 7, "-", border=1, align="R")
        pdf.cell(35, 7, f"{deductions:.2f} EUR", border=1, align="R", new_x="LMARGIN", new_y="NEXT")
        
        # Blank spacer rows
        for label, gross, ded in [
            ("Pagas Extras Prorrateadas", 0.0, 0.0),
            ("Seguridad Social Empleado", 0.0, 0.0),
        ]:
            pdf.cell(120, 7, label, border=1)
            pdf.cell(35, 7, "-" if gross == 0 else f"{gross:.2f} EUR", border=1, align="R")
            pdf.cell(35, 7, "-" if ded == 0 else f"{ded:.2f} EUR", border=1, align="R", new_x="LMARGIN", new_y="NEXT")
            
        pdf.ln(8)
        
        # Totals box
        y_total = pdf.get_y()
        pdf.set_fill_color(245, 245, 250)
        pdf.rect(100, y_total, 100, 30, 'F')
        
        net_salary = payslip.get("net_salary", 0.0)
        
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_y(y_total + 2)
        pdf.set_x(105)
        pdf.cell(50, 6, "Total Devengado:", new_x="RIGHT")
        pdf.cell(40, 6, f"{base_salary:.2f} EUR", align="R", new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_x(105)
        pdf.cell(50, 6, "Total Deducciones:", new_x="RIGHT")
        pdf.cell(40, 6, f"{deductions:.2f} EUR", align="R", new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_x(105)
        pdf.cell(50, 8, "NETO A PERCIBIR:", new_x="RIGHT")
        pdf.cell(40, 8, f"{net_salary:.2f} EUR", align="R", new_x="LMARGIN", new_y="NEXT")
        
        # Signatures Box
        pdf.set_y(y_total + 35)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(95, 6, "Firma de la Empresa", new_x="RIGHT", new_y="TOP")
        pdf.cell(95, 6, "Firma del Empleado", new_x="LMARGIN", new_y="NEXT")
        
        pdf.rect(10, pdf.get_y(), 80, 25)
        pdf.rect(110, pdf.get_y(), 80, 25)
        
        # Footer
        pdf.set_y(280)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 6, "Este documento es un recibo oficial de salario autogenerado por la plataforma SuccessCore.", align="C")
        
        return pdf.output()
    except Exception as e:
        logger.error(f"Error generating payslip PDF: {e}")
        return f"Error: {e}".encode('utf-8')
