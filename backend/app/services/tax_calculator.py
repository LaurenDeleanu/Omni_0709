"""
tax_calculator.py — Tax calculation engine with configurable brackets from DB.
Falls back to built-in defaults if no DB brackets configured for a country.
"""
import logging
from typing import Optional

logger = logging.getLogger("successcore.tax_calculator")

# Default built-in brackets (fallback if DB has none)
DEFAULT_BRACKETS = {
    "ES": {
        "name": "IRPF España", "currency": "EUR",
        "brackets": [(0, 12450, 0.19), (12450, 20200, 0.24), (20200, 35200, 0.30), (35200, 60000, 0.37), (60000, 300000, 0.45), (300000, float("inf"), 0.47)],
        "social_security_employee": 0.0635, "social_security_employer": 0.296, "personal_allowance": 5550,
    },
    "DE": {
        "name": "Einkommensteuer", "currency": "EUR",
        "brackets": [(0, 10908, 0.0), (10908, 62810, 0.14), (62810, 277826, 0.42), (277826, float("inf"), 0.45)],
        "social_security_employee": 0.207, "social_security_employer": 0.207, "personal_allowance": 10908,
    },
    "FR": {
        "name": "Impôt sur le revenu", "currency": "EUR",
        "brackets": [(0, 10777, 0.0), (10777, 27478, 0.11), (27478, 78570, 0.30), (78570, 168994, 0.41), (168994, float("inf"), 0.45)],
        "social_security_employee": 0.22, "social_security_employer": 0.42,
    },
    "IT": {
        "name": "IRPEF", "currency": "EUR",
        "brackets": [(0, 15000, 0.23), (15000, 28000, 0.25), (28000, 50000, 0.35), (50000, float("inf"), 0.43)],
        "social_security_employee": 0.099, "social_security_employer": 0.30,
    },
    "US": {
        "name": "Federal Income Tax", "currency": "USD",
        "brackets": [(0, 11000, 0.10), (11000, 44725, 0.12), (44725, 95375, 0.22), (95375, 182100, 0.24), (182100, 231250, 0.32), (231250, 578125, 0.35), (578125, float("inf"), 0.37)],
        "social_security_employee": 0.0765, "social_security_employer": 0.0765, "standard_deduction": 13850,
    },
    "GB": {
        "name": "Income Tax", "currency": "GBP",
        "brackets": [(0, 12570, 0.0), (12570, 50270, 0.20), (50270, 125140, 0.40), (125140, float("inf"), 0.45)],
        "social_security_employee": 0.10, "social_security_employer": 0.138, "personal_allowance": 12570,
    },
    "PT": {
        "name": "IRS Portugal", "currency": "EUR",
        "brackets": [(0, 7703, 0.13), (7703, 11623, 0.165), (11623, 16472, 0.22), (16472, 21321, 0.25), (21321, 27146, 0.32), (27146, 39791, 0.355), (39791, 51997, 0.435), (51997, 81199, 0.45), (81199, float("inf"), 0.48)],
        "social_security_employee": 0.11, "social_security_employer": 0.2375,
    },
}

_cache: dict[str, dict] = {}


def _load_default(country_code: str) -> Optional[dict]:
    """Load default brackets for a country."""
    return DEFAULT_BRACKETS.get(country_code.upper())


async def _load_from_db(country_code: str, tax_year: int = 2026) -> Optional[dict]:
    """Load configured brackets from the database."""
    try:
        from app.core.database import engine
        from sqlalchemy import select, text
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

        maker = async_sessionmaker(bind=engine, class_=AsyncSession)
        async with maker() as db:
            from app.models.tax_bracket import TaxBracket
            result = await db.execute(
                select(TaxBracket).where(
                    TaxBracket.country_code == country_code.upper(),
                    TaxBracket.tax_year == tax_year,
                    TaxBracket.is_active == True,
                ).order_by(TaxBracket.is_custom.desc()).limit(1)
            )
            bracket = result.scalar_one_or_none()
            if bracket:
                return {
                    "name": bracket.name, "currency": bracket.currency,
                    "brackets": [(b[0], b[1], b[2]) for b in bracket.brackets],
                    "social_security_employee": bracket.social_security_employee,
                    "social_security_employer": bracket.social_security_employer,
                    "personal_allowance": bracket.personal_allowance,
                    "standard_deduction": bracket.standard_deduction,
                    "vat_rate": bracket.vat_rate,
                    "source": bracket.source,
                }
    except Exception as e:
        logger.warning(f"DB tax lookup failed for {country_code}: {e}")
    return None


async def _get_brackets(country_code: str, tax_year: int = 2026) -> Optional[dict]:
    """Get brackets: DB first, cache second, defaults third."""
    cache_key = f"{country_code.upper()}:{tax_year}"
    if cache_key in _cache:
        return _cache[cache_key]

    db_result = await _load_from_db(country_code, tax_year)
    if db_result:
        _cache[cache_key] = db_result
        return db_result

    default = _load_default(country_code)
    if default:
        _cache[cache_key] = default
        return default

    return None


def _calculate_progressive(gross_salary: float, brackets: list[tuple]) -> float:
    """Calculate progressive tax on gross salary."""
    total_tax = 0
    previous_max = 0
    for bracket_min, bracket_max, rate in brackets:
        if gross_salary > previous_max:
            taxable = min(gross_salary, bracket_max) - previous_max
            if taxable > 0:
                total_tax += taxable * rate
        previous_max = bracket_max
        if gross_salary <= bracket_max:
            break
    return round(total_tax, 2)


async def calculate_tax(gross_salary: float, country_code: str, tax_year: int = 2026) -> dict:
    """Calculate income tax, social security, and net salary for a gross salary."""
    brackets = await _get_brackets(country_code.upper(), tax_year)

    if not brackets:
        return {
            "country_code": country_code.upper(),
            "gross_salary": gross_salary,
            "net_salary": gross_salary,
            "income_tax": 0,
            "social_security": 0,
            "total_deductions": 0,
            "effective_tax_rate": 0,
            "currency": "EUR",
            "error": f"No tax brackets configured for {country_code.upper()}",
        }

    allowance = brackets.get("personal_allowance", 0)
    deduction = brackets.get("standard_deduction", 0)
    taxable_income = max(0, gross_salary - allowance - deduction)

    income_tax = _calculate_progressive(taxable_income, brackets["brackets"])
    ss_rate = brackets.get("social_security_employee", 0)
    social_security = round(taxable_income * ss_rate, 2)
    total_deductions = income_tax + social_security
    net_salary = round(gross_salary - total_deductions, 2)
    effective_rate = round(total_deductions / gross_salary * 100, 1) if gross_salary > 0 else 0

    return {
        "country_code": country_code.upper(),
        "country_name": brackets.get("name", country_code),
        "tax_year": tax_year,
        "currency": brackets.get("currency", "EUR"),
        "gross_salary": gross_salary,
        "taxable_income": round(taxable_income, 2),
        "personal_allowance": allowance,
        "standard_deduction": deduction,
        "income_tax": income_tax,
        "social_security": social_security,
        "total_deductions": total_deductions,
        "net_salary": net_salary,
        "effective_tax_rate": effective_rate,
        "employer_cost": round(gross_salary * (1 + brackets.get("social_security_employer", 0)), 2),
        "source": brackets.get("source", "default"),
        "brackets_used": len(brackets.get("brackets", [])),
    }


async def get_all_countries() -> list[dict]:
    """List all available countries with brief info."""
    result = []
    for code, data in DEFAULT_BRACKETS.items():
        result.append({
            "country_code": code,
            "name": data["name"],
            "currency": data["currency"],
            "bracket_count": len(data["brackets"]),
        })
    return sorted(result, key=lambda x: x["country_code"])


async def get_tax_brackets(country_code: str, tax_year: int = 2026) -> dict:
    """Get full tax bracket details for a country."""
    brackets = await _get_brackets(country_code.upper(), tax_year)
    if not brackets:
        return {"error": f"No brackets for {country_code.upper()}"}
    return brackets


def clear_cache():
    """Clear the tax bracket cache (e.g., after admin updates)."""
    _cache.clear()
