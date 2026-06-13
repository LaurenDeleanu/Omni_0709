import logging
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger("successcore.accrual")

DEFAULT_ACCRUAL_RULES = {
    "ES": {"base_days_per_year": 30, "tenure_bonus": {5: 2, 10: 4, 15: 6}},
    "FR": {"base_days_per_year": 25, "tenure_bonus": {5: 2, 10: 3, 15: 5}},
    "DE": {"base_days_per_year": 24, "tenure_bonus": {5: 2, 10: 4, 15: 5}},
    "UK": {"base_days_per_year": 28, "tenure_bonus": {5: 2, 10: 3, 15: 4}},
    "US": {"base_days_per_year": 15, "tenure_bonus": {3: 3, 5: 5, 10: 7}},
    "MX": {"base_days_per_year": 12, "tenure_bonus": {1: 2, 2: 4, 3: 6, 4: 8, 5: 10}},
}


def calculate_accrual(hire_date: date, country: str = "ES", custom_rules: Optional[dict] = None) -> dict:
    rules = custom_rules or DEFAULT_ACCRUAL_RULES.get(country.upper(), DEFAULT_ACCRUAL_RULES["ES"])
    base_days = rules["base_days_per_year"]
    tenure_bonus = rules.get("tenure_bonus", {})

    today = date.today()
    years_employed = max(0, (today - hire_date).days / 365.25)

    bonus_days = 0
    for years_needed, bonus in sorted(tenure_bonus.items()):
        if years_employed >= years_needed:
            bonus_days = bonus

    total_annual = base_days + bonus_days
    accrued_today = round(total_annual * (min(years_employed, 1.0) if years_employed < 1 else 1.0), 1)

    return {
        "country": country.upper(),
        "hire_date": hire_date.isoformat(),
        "years_employed": round(years_employed, 2),
        "base_days": base_days,
        "tenure_bonus_days": bonus_days,
        "total_annual_days": total_annual,
        "accrued_today": accrued_today,
    }
