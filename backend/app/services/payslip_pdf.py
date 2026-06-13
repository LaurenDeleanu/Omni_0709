import logging
import io
from typing import Dict, Any, List, Optional

logger = logging.getLogger("successcore.payslip_pdf")


def generate_payslip_html(data: Dict[str, Any]) -> str:
    employee = data.get("employee", {})
    company = data.get("company", {})
    period = data.get("period", {})
    earnings = data.get("earnings", [])
    deductions = data.get("deductions", [])
    totals = data.get("totals", {})

    gross_total = sum(e.get("amount", 0) for e in earnings)
    deductions_total = sum(d.get("amount", 0) for d in deductions)
    net_total = gross_total - deductions_total

    earnings_rows = "".join(
        f'<tr><td>{e.get("concept", "")}</td><td class="num">{e.get("amount", 0):,.2f} {data.get("currency", "EUR")}</td></tr>'
        for e in earnings
    )
    deductions_rows = "".join(
        f'<tr><td>{d.get("concept", "")} ({d.get("rate_pct", 0):.1f}%)</td><td class="num">{d.get("amount", 0):,.2f} {data.get("currency", "EUR")}</td></tr>'
        for d in deductions
    )

    html = f"""<!DOCTYPE html>
<html lang="{data.get('language', 'es')}">
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; color: #1a1a2e; font-size: 12px; }}
  .header {{ display: flex; justify-content: space-between; border-bottom: 3px solid #1a1a2e; padding-bottom: 15px; margin-bottom: 20px; }}
  .company {{ font-size: 14px; font-weight: bold; }}
  .title {{ font-size: 18px; font-weight: bold; text-align: center; margin: 15px 0; color: #1a1a2e; }}
  .section {{ margin: 20px 0; }}
  .section-title {{ background: #1a1a2e; color: white; padding: 6px 10px; font-size: 13px; font-weight: bold; }}
  table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
  th {{ background: #f0f0f0; text-align: left; padding: 6px 8px; font-size: 11px; border-bottom: 2px solid #1a1a2e; }}
  td {{ padding: 5px 8px; font-size: 11px; border-bottom: 1px solid #e0e0e0; }}
  .num {{ text-align: right; font-family: 'Consolas', monospace; }}
  .total {{ font-size: 14px; font-weight: bold; }}
  .footer {{ margin-top: 40px; font-size: 10px; color: #666; border-top: 1px solid #ccc; padding-top: 15px; }}
  .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
  .info-item {{ font-size: 11px; }}
  .info-label {{ font-weight: bold; color: #555; }}
  .net-pay {{ background: #e8f5e9; padding: 12px; border-radius: 4px; margin: 15px 0; text-align: center; font-size: 16px; font-weight: bold; }}
</style>
</head>
<body>

<div class="header">
  <div class="company">
    {company.get('name', 'SuccessCore HR')}<br>
    {company.get('address', '')}<br>
    {company.get('tax_id', '')}
  </div>
  <div style="text-align:right;">
    <strong>{data.get('doc_type', 'NÓMINA')}</strong><br>
    Periodo: {period.get('label', '')}<br>
    Fecha: {data.get('issue_date', '')}
  </div>
</div>

<div class="title">RECIBO DE NÓMINA</div>

<div class="section">
  <div class="section-title">DATOS DEL EMPLEADO</div>
  <div class="info-grid">
    <div class="info-item"><span class="info-label">Nombre:</span> {employee.get('full_name', '')}</div>
    <div class="info-item"><span class="info-label">NIF/NIE:</span> {employee.get('tax_id', '')}</div>
    <div class="info-item"><span class="info-label">Departamento:</span> {employee.get('department', '')}</div>
    <div class="info-item"><span class="info-label">Puesto:</span> {employee.get('position', '')}</div>
    <div class="info-item"><span class="info-label">Categoría:</span> {employee.get('category', '')}</div>
    <div class="info-item"><span class="info-label">Grupo Cotización:</span> {employee.get('contribution_group', '')}</div>
    <div class="info-item"><span class="info-label">Nº Afiliación SS:</span> {employee.get('ss_number', '')}</div>
    <div class="info-item"><span class="info-label">Antigüedad:</span> {employee.get('seniority', '')}</div>
  </div>
</div>

<div class="section">
  <div class="section-title">DEVENGOS</div>
  <table>
    <tr><th>Concepto</th><th style="text-align:right;">Importe</th></tr>
    {earnings_rows}
    <tr style="font-weight:bold; border-top: 2px solid #1a1a2e;">
      <td>Total Devengado</td>
      <td class="num">{gross_total:,.2f} {data.get('currency', 'EUR')}</td>
    </tr>
  </table>
</div>

<div class="section">
  <div class="section-title">DEDUCCIONES</div>
  <table>
    <tr><th>Concepto</th><th style="text-align:right;">Importe</th></tr>
    {deductions_rows}
    <tr style="font-weight:bold; border-top: 2px solid #1a1a2e;">
      <td>Total Deducciones</td>
      <td class="num">{deductions_total:,.2f} {data.get('currency', 'EUR')}</td>
    </tr>
  </table>
</div>

<div class="net-pay">
  LÍQUIDO A PERCIBIR: {net_total:,.2f} {data.get('currency', 'EUR')}
</div>

<div class="section">
  <div class="section-title">BASES DE COTIZACIÓN</div>
  <table>
    <tr><th>Concepto</th><th style="text-align:right;">Base</th><th style="text-align:right;">Tipo Empresa</th><th style="text-align:right;">Tipo Trabajador</th></tr>
    <tr><td>Contingencias Comunes</td><td class="num">{totals.get('cc_base', gross_total):,.2f}</td><td class="num">{totals.get('cc_employer_pct', 23.60):.1f}%</td><td class="num">{totals.get('cc_employee_pct', 4.70):.1f}%</td></tr>
    <tr><td>Contingencias Profesionales</td><td class="num">{totals.get('cp_base', gross_total):,.2f}</td><td class="num">{totals.get('cp_employer_pct', 1.50):.1f}%</td><td class="num">{totals.get('cp_employee_pct', 0.00):.1f}%</td></tr>
    <tr><td>Desempleo</td><td class="num">{totals.get('unemp_base', gross_total):,.2f}</td><td class="num">{totals.get('unemp_employer_pct', 5.50):.1f}%</td><td class="num">{totals.get('unemp_employee_pct', 1.55):.1f}%</td></tr>
    <tr><td>FOGASA</td><td class="num">{totals.get('fogasa_base', gross_total):,.2f}</td><td class="num">{totals.get('fogasa_employer_pct', 0.20):.1f}%</td><td class="num">-</td></tr>
    <tr><td>Formación Profesional</td><td class="num">{totals.get('fp_base', gross_total):,.2f}</td><td class="num">{totals.get('fp_employer_pct', 0.60):.1f}%</td><td class="num">{totals.get('fp_employee_pct', 0.10):.1f}%</td></tr>
  </table>
</div>

<div class="footer">
  <p>Este documento es un recibo de nómina generado por SuccessCore HR conforme a la legislación laboral española.</p>
  <p>IRPF aplicado: {data.get('irpf_rate', 0):.1f}% | Tipo de contrato: {employee.get('contract_type', '')} | Jornada: {employee.get('workday_type', '')}</p>
  <p style="margin-top:10px;">Documento generado el {data.get('generated_at', '')} | ID: {data.get('payslip_id', '')}</p>
</div>

</body>
</html>"""
    return html


def generate_payslip_pdf(data: Dict[str, Any]) -> bytes:
    html = generate_payslip_html(data)
    try:
        import fpdf2
        from fpdf import FPDF, HTMLMixin

        class PDF(FPDF, HTMLMixin):
            pass

        pdf = PDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.write_html(html)
        return pdf.output()
    except ImportError:
        try:
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", size=10)
            for line in _html_to_text(html).split("\\n"):
                pdf.cell(0, 6, line, ln=True)
            return pdf.output()
        except ImportError:
            return html.encode("utf-8")


def _html_to_text(html: str) -> str:
    import re
    text = re.sub(r'<[^>]+>', '', html)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
