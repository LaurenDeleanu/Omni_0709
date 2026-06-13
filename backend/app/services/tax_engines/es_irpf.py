from typing import List, Dict, Any
from .base import BaseTaxEngine, TaxCalculationResult
from .generic import GenericTaxEngine

class ESTaxEngine(BaseTaxEngine):
    """Spain IRPF calculation engine. Currently proxies to the generic engine as rules are in DB."""
    def calculate_taxes(self, annual_salary: float, rules: List[Dict[str, Any]]) -> TaxCalculationResult:
        # ES specific logic can be added here. Currently uses generic rule logic.
        return GenericTaxEngine().calculate_taxes(annual_salary, rules)
