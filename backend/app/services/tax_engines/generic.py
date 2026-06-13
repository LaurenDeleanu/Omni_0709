from typing import List, Dict, Any
import uuid
from .base import BaseTaxEngine, TaxCalculationResult

class GenericTaxEngine(BaseTaxEngine):
    """Generic fallback engine that runs the legacy generic DB rules."""
    def calculate_taxes(self, annual_salary: float, rules: List[Dict[str, Any]]) -> TaxCalculationResult:
        annual_tax = 0.0
        line_items = []
        for rule in sorted(rules, key=lambda x: x.get("min_salary") or 0):
            if rule.get("is_marginal"):
                if not rule.get("is_deduction"):
                    continue
                min_sal = rule.get("min_salary") or 0
                max_sal = rule.get("max_salary") or float('inf')
                if annual_salary > min_sal:
                    taxable_in_bracket = min(annual_salary, max_sal) - min_sal
                    if rule.get("calculation_type") == "percentage":
                        bracket_tax = taxable_in_bracket * rule.get("rate", 0)
                        annual_tax += bracket_tax
                        if bracket_tax > 0:
                            line_items.append({
                                "id": uuid.uuid4().hex,
                                "description": f"{rule.get('name')} (Anual prorrateado)",
                                "amount": bracket_tax / 12.0,
                                "type": "deduction"
                            })
                    elif rule.get("calculation_type") == "fixed_amount":
                        annual_tax += rule.get("rate", 0)
                        line_items.append({
                            "id": uuid.uuid4().hex,
                            "description": f"{rule.get('name')}",
                            "amount": rule.get("rate", 0) / 12.0,
                            "type": "deduction"
                        })
            else:
                applicable_salary = annual_salary
                if rule.get("max_salary") and applicable_salary > rule["max_salary"]:
                    applicable_salary = rule["max_salary"]
                if rule.get("calculation_type") == "percentage":
                    amount = applicable_salary * rule.get("rate", 0)
                    if rule.get("is_deduction"):
                        annual_tax += amount
                        line_items.append({
                            "id": uuid.uuid4().hex,
                            "description": f"{rule.get('name')}",
                            "amount": amount / 12.0,
                            "type": "deduction"
                        })
                    else:
                        line_items.append({
                            "id": uuid.uuid4().hex,
                            "description": f"{rule.get('name')}",
                            "amount": amount / 12.0,
                            "type": "employer_cost"
                        })
        return TaxCalculationResult(annual_tax=annual_tax, line_items=line_items)
