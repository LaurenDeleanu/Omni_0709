from typing import List, Dict, Any
import uuid
from .base import BaseTaxEngine, TaxCalculationResult

class PTTaxEngine(BaseTaxEngine):
    """Portugal IRS calculation engine (simplified)."""
    def calculate_taxes(self, annual_salary: float, rules: List[Dict[str, Any]]) -> TaxCalculationResult:
        annual_tax = 0.0
        line_items = []
        
        # Simplified IRS Brackets for Portugal
        irs_tax = 0.0
        monthly_salary = annual_salary / 14.0 # Portugal uses 14 months salary structure typically
        
        if monthly_salary > 762:
            if monthly_salary <= 1146:
                irs_tax = (annual_salary * 0.145)
            elif monthly_salary <= 1650:
                irs_tax = (annual_salary * 0.23)
            elif monthly_salary <= 2500:
                irs_tax = (annual_salary * 0.285)
            else:
                irs_tax = (annual_salary * 0.35)
                
        if irs_tax > 0:
            annual_tax += irs_tax
            line_items.append({
                "id": uuid.uuid4().hex,
                "description": "Portugal IRS",
                "amount": irs_tax / 12.0, # Normalizing to 12 monthly payments for SAS
                "type": "deduction"
            })
            
        # Social Security (Segurança Social) 11% for employee
        ss_tax = annual_salary * 0.11
        if ss_tax > 0:
            annual_tax += ss_tax
            line_items.append({
                "id": uuid.uuid4().hex,
                "description": "Segurança Social (11%)",
                "amount": ss_tax / 12.0,
                "type": "deduction"
            })
            
        return TaxCalculationResult(annual_tax=annual_tax, line_items=line_items)
