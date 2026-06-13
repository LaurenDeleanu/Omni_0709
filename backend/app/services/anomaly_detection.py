import statistics
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple
from collections import defaultdict

logger = logging.getLogger("successcore.anomaly")


def detect_anomalies(series: List[Tuple[str, float]], threshold: float = 2.0) -> List[dict]:
    if len(series) < 5:
        return []
    values = [v for _, v in series]
    mean = statistics.mean(values)
    stdev = statistics.stdev(values) if len(values) > 1 else 1.0
    if stdev == 0:
        return []

    anomalies = []
    for label, value in series:
        z_score = abs(value - mean) / stdev
        if z_score >= threshold:
            direction = "high" if value > mean else "low"
            anomalies.append({
                "label": label,
                "value": value,
                "mean": round(mean, 2),
                "z_score": round(z_score, 2),
                "direction": direction,
                "deviation_pct": round((value - mean) / mean * 100, 1) if mean != 0 else 0,
            })
    return anomalies


async def compute_hr_anomalies(db) -> dict:
    from sqlalchemy import select, func, extract
    from app.models.user import User
    from app.models.pay import Payslip, PayrollCycle
    from app.models.finance import ExpenseClaim
    from datetime import datetime as dt

    anomalies = {}

    # 1. Headcount change over months
    try:
        result = await db.execute(
            select(User.hire_date, User.is_active)
            .where(User.hire_date.isnot(None))
            .order_by(User.hire_date.asc())
        )
        users = result.all()
        monthly_counts: Dict[str, int] = defaultdict(int)
        for hire_date, is_active in users:
            if hire_date:
                key = hire_date.strftime("%Y-%m")
                monthly_counts[key] += 1

        series = [(k, v) for k, v in sorted(monthly_counts.items())[-12:]]
        headcount_anomalies = detect_anomalies(series, threshold=1.5)
        if headcount_anomalies:
            anomalies["headcount"] = headcount_anomalies
    except Exception as e:
        logger.warning(f"Headcount anomaly check failed: {e}")

    # 2. Payroll total anomalies
    try:
        cycle_res = await db.execute(
            select(PayrollCycle)
            .order_by(PayrollCycle.end_date.desc())
            .limit(12)
        )
        cycles = cycle_res.scalars().all()
        payroll_series = []
        for cycle in reversed(cycles):
            total = await db.execute(
                select(func.coalesce(func.sum(Payslip.gross_salary), 0))
                .where(Payslip.cycle_id == cycle.id)
            )
            gross = total.scalar() or 0
            label = cycle.end_date.strftime("%Y-%m") if cycle.end_date else cycle.id[:7]
            payroll_series.append((label, gross))
        payroll_anomalies = detect_anomalies(payroll_series, threshold=2.0)
        if payroll_anomalies:
            anomalies["payroll"] = payroll_anomalies
    except Exception as e:
        logger.warning(f"Payroll anomaly check failed: {e}")

    # 3. Expense claim volume
    try:
        expense_counts: Dict[str, int] = defaultdict(int)
        six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)
        exp_res = await db.execute(
            select(ExpenseClaim.created_at)
            .where(ExpenseClaim.created_at >= six_months_ago)
        )
        for (created_at,) in exp_res.all():
            key = created_at.strftime("%Y-%m")
            expense_counts[key] += 1
        expense_series = [(k, v) for k, v in sorted(expense_counts.items())]
        expense_anomalies = detect_anomalies(expense_series, threshold=2.0)
        if expense_anomalies:
            anomalies["expense_volume"] = expense_anomalies
    except Exception as e:
        logger.warning(f"Expense anomaly check failed: {e}")

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "anomalies_found": len(anomalies),
        "metrics": anomalies,
    }
