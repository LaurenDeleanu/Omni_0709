import logging
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user import User

logger = logging.getLogger("successcore.compensation")

DEFAULT_SALARY_BANDS: Dict[str, List[dict]] = {
    "ES": [
        {"level": "Junior", "min": 18000, "max": 30000, "midpoint": 24000},
        {"level": "Mid", "min": 30000, "max": 50000, "midpoint": 40000},
        {"level": "Senior", "min": 45000, "max": 70000, "midpoint": 57500},
        {"level": "Lead", "min": 65000, "max": 90000, "midpoint": 77500},
        {"level": "Director", "min": 85000, "max": 130000, "midpoint": 107500},
        {"level": "VP", "min": 120000, "max": 200000, "midpoint": 160000},
    ],
    "US": [
        {"level": "Junior", "min": 50000, "max": 75000, "midpoint": 62500},
        {"level": "Mid", "min": 75000, "max": 120000, "midpoint": 97500},
        {"level": "Senior", "min": 110000, "max": 170000, "midpoint": 140000},
        {"level": "Lead", "min": 160000, "max": 220000, "midpoint": 190000},
        {"level": "Director", "min": 200000, "max": 300000, "midpoint": 250000},
        {"level": "VP", "min": 280000, "max": 500000, "midpoint": 390000},
    ],
    "UK": [
        {"level": "Junior", "min": 25000, "max": 40000, "midpoint": 32500},
        {"level": "Mid", "min": 40000, "max": 65000, "midpoint": 52500},
        {"level": "Senior", "min": 60000, "max": 90000, "midpoint": 75000},
        {"level": "Lead", "min": 85000, "max": 120000, "midpoint": 102500},
        {"level": "Director", "min": 110000, "max": 180000, "midpoint": 145000},
        {"level": "VP", "min": 160000, "max": 300000, "midpoint": 230000},
    ],
}


def get_band_for_level(level: str, country: str = "ES") -> Optional[dict]:
    bands = DEFAULT_SALARY_BANDS.get(country.upper(), DEFAULT_SALARY_BANDS["ES"])
    for band in bands:
        if band["level"].lower() == level.lower():
            return band
    return None


def compute_compa_ratio(salary: float, band_midpoint: float) -> float:
    if band_midpoint == 0:
        return 0
    return round(salary / band_midpoint, 4)


async def get_compensation_analysis(db: AsyncSession) -> dict:
    result = await db.execute(
        select(User).where(User.is_active == True, User.base_salary > 0)
    )
    employees = result.scalars().all()

    outliers_below_band: list = []
    outliers_above_band: list = []
    compa_data: list = []
    department_stats: Dict[str, list] = {}

    for emp in employees:
        band = get_band_for_level(emp.role or "employee", emp.country or "ES")
        if not band:
            continue
        compa = compute_compa_ratio(emp.base_salary, band["midpoint"])
        entry = {
            "user_id": emp.id,
            "name": emp.full_name or emp.email,
            "department": emp.department,
            "role": emp.role,
            "salary": emp.base_salary,
            "band": band["level"],
            "band_range": f"{band['min']}-{band['max']}",
            "band_midpoint": band["midpoint"],
            "compa_ratio": compa,
        }

        if emp.base_salary < band["min"]:
            outliers_below_band.append(entry)
        elif emp.base_salary > band["max"]:
            outliers_above_band.append(entry)

        compa_data.append(entry)
        dept = emp.department or "Unknown"
        if dept not in department_stats:
            department_stats[dept] = []
        department_stats[dept].append(compa)

    dept_avg = {}
    for dept, compas in department_stats.items():
        dept_avg[dept] = round(sum(compas) / len(compas), 3) if compas else 0

    return {
        "total_analyzed": len(compa_data),
        "outliers_below_band": outliers_below_band,
        "outliers_above_band": outliers_above_band,
        "avg_compa_ratio_by_department": dept_avg,
        "compa_data": compa_data[:200],
    }
