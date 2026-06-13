import logging
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.pay import Payslip, PayslipLineItem, TaxRule
from app.services.llm_router import get_llm_client

logger = logging.getLogger("successcore.payroll_intelligence")

async def explain_payslip_differences(
    db: AsyncSession,
    employee_id: str,
    current_payslip_id: str,
    prev_payslip_id: Optional[str] = None
) -> str:
    """
    Compares the current payslip with a previous one and uses an LLM to generate
    a clear, user-friendly explanation of why their net pay changed.
    """
    # 1. Fetch current payslip
    curr_stmt = (
        select(Payslip)
        .where(Payslip.id == current_payslip_id)
        .options(selectinload(Payslip.line_items), selectinload(Payslip.employee))
    )
    curr_res = await db.execute(curr_stmt)
    curr_payslip = curr_res.scalar_one_or_none()
    
    if not curr_payslip:
        return "Current payslip not found."
        
    # Verify employee ownership
    if curr_payslip.employee_id != employee_id:
        return "Unauthorized: Payslip does not belong to this employee."

    # 2. Fetch previous payslip
    prev_payslip = None
    if prev_payslip_id:
        prev_stmt = (
            select(Payslip)
            .where(Payslip.id == prev_payslip_id, Payslip.employee_id == employee_id)
            .options(selectinload(Payslip.line_items))
        )
        prev_res = await db.execute(prev_stmt)
        prev_payslip = prev_res.scalar_one_or_none()
    else:
        # Get the most recent finalized/paid payslip before this one
        prev_stmt = (
            select(Payslip)
            .where(
                Payslip.employee_id == employee_id,
                Payslip.id != current_payslip_id,
                Payslip.status == "finalized"
            )
            .options(selectinload(Payslip.line_items))
            .order_by(Payslip.created_at.desc())
            .limit(1)
        )
        prev_res = await db.execute(prev_stmt)
        prev_payslip = prev_res.scalar_one_or_none()

    # If no previous payslip is found, construct explanation based on base salary
    if not prev_payslip:
        base_salary = curr_payslip.employee.base_salary if curr_payslip.employee else 50000.0
        monthly_base = base_salary / 12.0
        
        comparison_info = (
            f"Employee has no previous payslips on record.\n"
            f"Active Annual Base Salary: {base_salary:.2f} EUR (Monthly Base: {monthly_base:.2f} EUR).\n"
            f"Current Payslip Gross: {curr_payslip.gross_salary:.2f} EUR.\n"
            f"Current Payslip Net: {curr_payslip.net_salary:.2f} EUR.\n"
            f"Current Payslip Deductions: {curr_payslip.deductions:.2f} EUR.\n"
            f"Current Line Items:\n"
        )
        for item in curr_payslip.line_items:
            comparison_info += f"- {item.description}: {item.amount:.2f} EUR ({item.type})\n"
            
        prompt = (
            "You are an HR and Payroll Assistant. This is the employee's first payslip. "
            "Explain their current payslip structure (base salary, any bonuses, and deductions) "
            "clearly in a professional and friendly tone. Offer information in Spanish and English.\n\n"
            f"Data:\n{comparison_info}"
        )
    else:
        # Compare current vs previous
        curr_items = {item.description: (item.amount, item.type) for item in curr_payslip.line_items}
        prev_items = {item.description: (item.amount, item.type) for item in prev_payslip.line_items}
        
        comparison_info = (
            f"Current Payslip: Gross={curr_payslip.gross_salary:.2f} EUR, Deductions={curr_payslip.deductions:.2f} EUR, Net={curr_payslip.net_salary:.2f} EUR\n"
            f"Previous Payslip: Gross={prev_payslip.gross_salary:.2f} EUR, Deductions={prev_payslip.deductions:.2f} EUR, Net={prev_payslip.net_salary:.2f} EUR\n"
            f"Difference Net: {(curr_payslip.net_salary - prev_payslip.net_salary):.2f} EUR\n"
            f"Difference Gross: {(curr_payslip.gross_salary - prev_payslip.gross_salary):.2f} EUR\n"
            f"Difference Deductions: {(curr_payslip.deductions - prev_payslip.deductions):.2f} EUR\n\n"
            f"Current Line Items:\n"
        )
        for desc, (amt, t) in curr_items.items():
            comparison_info += f"- {desc}: {amt:.2f} EUR ({t})\n"
            
        comparison_info += "\nPrevious Line Items:\n"
        for desc, (amt, t) in prev_items.items():
            comparison_info += f"- {desc}: {amt:.2f} EUR ({t})\n"
            
        prompt = (
            "You are an HR and Payroll Assistant. Compare the employee's current and previous payslips. "
            "Write a concise, clear breakdown in a professional tone explaining why their net salary has changed "
            "(e.g., changes in base salary, new bonuses, differences in tax/IRPF deductions, or overtime hours). "
            "Provide the explanation in both Spanish and English.\n\n"
            f"Data:\n{comparison_info}"
        )

    try:
        client, _ = await get_llm_client("gpt-4o-mini", None, db)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            max_tokens=400,
            messages=[
                {"role": "system", "content": "You are a professional HR specialist explaining payroll entries."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error calling LLM for payslip explanation: {e}")
        return f"Could not generate automated explanation due to LLM error. Gross: {curr_payslip.gross_salary:.2f} EUR, Net: {curr_payslip.net_salary:.2f} EUR."

async def get_tax_optimization_recommendations(db: AsyncSession, employee_id: str) -> List[Dict[str, Any]]:
    """
    Computes potential tax savings for employees based on Spanish flexible compensation (Retribución Flexible) guidelines.
    Includes Tarjeta Restaurante, Tarjeta Transporte, Seguro Médico, and Cheque Guardería.
    """
    stmt = select(User).where(User.id == employee_id)
    res = await db.execute(stmt)
    employee = res.scalar_one_or_none()
    
    if not employee:
        return []
        
    country = (employee.country or "ES").upper()
    if country not in ["ES", "SPAIN"]:
        # Only Spain is supported for specific tax rules
        return []
        
    base_salary = employee.base_salary if hasattr(employee, "base_salary") and employee.base_salary else 50000.0
    
    # Calculate Spanish marginal tax rate (IRPF 2026 Brackets)
    # Brackets:
    # 0 - 12,450: 19%
    # 12,450 - 20,200: 24%
    # 20,200 - 35,200: 30%
    # 35,200 - 60,000: 37%
    # 60,000 - 300,000: 45%
    # 300,000+: 47%
    if base_salary <= 12450:
        marginal_rate = 0.19
    elif base_salary <= 20200:
        marginal_rate = 0.24
    elif base_salary <= 35200:
        marginal_rate = 0.30
    elif base_salary <= 60000:
        marginal_rate = 0.37
    elif base_salary <= 300000:
        marginal_rate = 0.45
    else:
        marginal_rate = 0.47
        
    recommendations = []
    
    # 1. Restaurant Card (11€/day max, let's assume 220 working days = 2420€/year)
    restaurant_amount = 2420.0
    if restaurant_amount < base_salary * 0.30: # Max 30% of salary can be flexible benefits in Spain
        savings = restaurant_amount * marginal_rate
        recommendations.append({
            "benefit_name": "Tarjeta Restaurante / Restaurant Card",
            "annual_allowance": restaurant_amount,
            "monthly_equivalent": 220.0,
            "estimated_annual_savings": round(savings, 2),
            "description": "Exento de IRPF hasta 11€ al día para comidas de trabajo. / Tax-free up to 11€/day for working meals."
        })
        
    # 2. Transport Card (Up to 1,500€/year)
    transport_amount = 1500.0
    if transport_amount < base_salary * 0.30:
        savings = transport_amount * marginal_rate
        recommendations.append({
            "benefit_name": "Tarjeta Transporte / Public Transport Card",
            "annual_allowance": transport_amount,
            "monthly_equivalent": 125.0,
            "estimated_annual_savings": round(savings, 2),
            "description": "Exento de IRPF hasta 1.500€ anuales para transporte público. / Tax-free up to 1,500€/year for public transit."
        })
        
    # 3. Health Insurance (Up to 500€/year per family member)
    health_amount = 500.0
    if health_amount < base_salary * 0.30:
        savings = health_amount * marginal_rate
        recommendations.append({
            "benefit_name": "Seguro de Salud / Health Insurance",
            "annual_allowance": health_amount,
            "monthly_equivalent": 41.67,
            "estimated_annual_savings": round(savings, 2),
            "description": "Exento de IRPF hasta 500€ anuales por persona (empleado, cónyuge, descendientes). / Tax-free up to 500€/year per family member."
        })
        
    # 4. Childcare Voucher (Cheque Guardería - assuming average cost of 150€/month = 1800€/year)
    guarderia_amount = 1800.0
    if guarderia_amount < base_salary * 0.30:
        savings = guarderia_amount * marginal_rate
        recommendations.append({
            "benefit_name": "Cheque Guardería / Childcare Vouchers",
            "annual_allowance": guarderia_amount,
            "monthly_equivalent": 150.0,
            "estimated_annual_savings": round(savings, 2),
            "description": "Exención total del IRPF para gastos de educación infantil de 0 a 3 años. / Fully tax-free for early education (0-3 years)."
        })
        
    return recommendations

async def detect_payroll_cycle_anomalies(db: AsyncSession, cycle_id: str) -> List[Dict[str, Any]]:
    """
    Scans all draft payslips in a payroll cycle and flags those with a >15% deviation
    compared to the employee's historical average.
    """
    # 1. Fetch draft payslips in the cycle
    stmt = (
        select(Payslip)
        .where(Payslip.cycle_id == cycle_id)
        .options(selectinload(Payslip.line_items), selectinload(Payslip.employee))
    )
    res = await db.execute(stmt)
    payslips = res.scalars().all()
    
    anomalies = []
    
    for payslip in payslips:
        employee = payslip.employee
        if not employee:
            continue
            
        # Get historical finalized/paid payslips (up to last 3)
        hist_stmt = (
            select(Payslip)
            .where(
                Payslip.employee_id == employee.id,
                Payslip.cycle_id != cycle_id,
                Payslip.status == "finalized"
            )
            .order_by(Payslip.created_at.desc())
            .limit(3)
        )
        hist_res = await db.execute(hist_stmt)
        hist_payslips = hist_res.scalars().all()
        
        # Calculate historical average gross salary
        if hist_payslips:
            historical_average = sum(p.gross_salary for p in hist_payslips) / len(hist_payslips)
        else:
            # Fall back to base salary divided by 12
            base_sal = employee.base_salary if hasattr(employee, "base_salary") and employee.base_salary else 50000.0
            historical_average = base_sal / 12.0
            
        if historical_average <= 0:
            continue
            
        deviation = abs(payslip.gross_salary - historical_average) / historical_average
        
        if deviation > 0.15:
            # Find the differences/reasons
            reasons = []
            
            # Look at line items of type earning that might be causing it
            for item in payslip.line_items:
                if item.type == "earning" and "Salario Base" not in item.description:
                    reasons.append(f"Additional earning: {item.description} ({item.amount:.2f} EUR)")
                    
            if not reasons:
                reasons.append("Base salary rate adjustment or structural compensation change.")
                
            anomalies.append({
                "employee_id": employee.id,
                "employee_name": employee.full_name or employee.email,
                "department": employee.department or "Unknown",
                "payslip_id": payslip.id,
                "current_gross": round(payslip.gross_salary, 2),
                "historical_average_gross": round(historical_average, 2),
                "deviation_pct": round(deviation * 100, 1),
                "reasons": reasons
            })
            
    return anomalies
