from typing import List, Dict, Any
import uuid
from .base import BaseTaxEngine, TaxCalculationResult

class UKTaxEngine(BaseTaxEngine):
    """UK PAYE and National Insurance calculation engine."""
    def calculate_taxes(self, annual_salary: float, rules: List[Dict[str, Any]]) -> TaxCalculationResult:
        annual_tax = 0.0
        line_items = []
        
        # Standard UK Tax Free Allowance 12,570 GBP
        allowance = 12570.0
        taxable_pay = max(0.0, annual_salary - allowance)
        
        paye_tax = 0.0
        # Basic rate 20%
        basic_band = min(taxable_pay, 37700.0)
        paye_tax += basic_band * 0.20
        
        # Higher rate 40%
        if taxable_pay > 37700.0:
            higher_band = min(taxable_pay - 37700.0, 125140.0 - 50270.0)
            paye_tax += higher_band * 0.40
            
        # Additional rate 45%
        if annual_salary > 125140.0:
            additional_band = annual_salary - 125140.0
            paye_tax += additional_band * 0.45
            
        if paye_tax > 0:
            annual_tax += paye_tax
            line_items.append({
                "id": uuid.uuid4().hex,
                "description": "UK PAYE Income Tax",
                "amount": paye_tax / 12.0,
                "type": "deduction"
            })
            
        # National Insurance (simplified Class 1)
        ni_tax = 0.0
        if annual_salary > 12570.0:
            ni_band1 = min(annual_salary - 12570.0, 50270.0 - 12570.0)
            ni_tax += ni_band1 * 0.08  # Main rate
        if annual_salary > 50270.0:
            ni_tax += (annual_salary - 50270.0) * 0.02  # Additional rate
            
        if ni_tax > 0:
            annual_tax += ni_tax
            line_items.append({
                "id": uuid.uuid4().hex,
                "description": "National Insurance (NI)",
                "amount": ni_tax / 12.0,
                "type": "deduction"
            })
            
        return TaxCalculationResult(annual_tax=annual_tax, line_items=line_items)
