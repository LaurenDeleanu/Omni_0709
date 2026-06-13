from typing import List, Dict, Any
from dataclasses import dataclass
import uuid

@dataclass
class TaxCalculationResult:
    annual_tax: float
    line_items: List[Dict[str, Any]]

class BaseTaxEngine:
    """Abstract base class for country-specific tax calculations."""
    def calculate_taxes(self, annual_salary: float, rules: List[Dict[str, Any]]) -> TaxCalculationResult:
        raise NotImplementedError("Subclasses must implement calculate_taxes")
