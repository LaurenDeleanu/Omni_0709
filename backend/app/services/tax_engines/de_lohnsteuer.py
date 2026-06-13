from typing import List, Dict, Any
import uuid
from .base import BaseTaxEngine, TaxCalculationResult

class DETaxEngine(BaseTaxEngine):
    """Germany Lohnsteuer calculation engine (simplified)."""
    def calculate_taxes(self, annual_salary: float, rules: List[Dict[str, Any]]) -> TaxCalculationResult:
        annual_tax = 0.0
        line_items = []
        
        # Lohnsteuer (Income Tax) - simplified progressive
        allowance = 10908.0
        taxable_pay = max(0.0, annual_salary - allowance)
        
        lohnsteuer = 0.0
        if taxable_pay > 0:
            if annual_salary <= 62810:
                lohnsteuer = taxable_pay * 0.24 # Average basic progressive
            elif annual_salary <= 277826:
                lohnsteuer = (62810 - allowance) * 0.24 + (annual_salary - 62810) * 0.42
            else:
                lohnsteuer = (62810 - allowance) * 0.24 + (277826 - 62810) * 0.42 + (annual_salary - 277826) * 0.45
                
        if lohnsteuer > 0:
            annual_tax += lohnsteuer
            line_items.append({
                "id": uuid.uuid4().hex,
                "description": "Lohnsteuer (Income Tax)",
                "amount": lohnsteuer / 12.0,
                "type": "deduction"
            })
            
        # Social contributions (Rentenversicherung, Krankenversicherung, etc.) - simplified flat rates
        health_ins = annual_salary * 0.073  # Krankenversicherung ~7.3%
        pension_ins = annual_salary * 0.093 # Rentenversicherung ~9.3%
        unemployment_ins = annual_salary * 0.013 # Arbeitslosenversicherung ~1.3%
        care_ins = annual_salary * 0.017 # Pflegeversicherung ~1.7%
        
        social_tax = health_ins + pension_ins + unemployment_ins + care_ins
        
        if social_tax > 0:
            annual_tax += social_tax
            line_items.append({
                "id": uuid.uuid4().hex,
                "description": "Sozialversicherung (Social Security)",
                "amount": social_tax / 12.0,
                "type": "deduction"
            })
            
        return TaxCalculationResult(annual_tax=annual_tax, line_items=line_items)
