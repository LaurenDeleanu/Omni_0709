"""
finance_forecasting.py — Financial forecasting and predictive analytics.
Cash flow projections, budget variance analysis, anomaly detection, financial reports.
"""
import logging
import statistics
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from pydantic import BaseModel

logger = logging.getLogger("successcore.forecasting")


class CashFlowPoint(BaseModel):
    month: str
    projected_income: float
    projected_expenses: float
    net_cashflow: float
    cumulative: float


class BudgetVariance(BaseModel):
    category: str
    budgeted: float
    actual: float
    variance: float
    variance_pct: float


class Anomaly(BaseModel):
    id: str
    date: str
    description: str
    amount: float
    z_score: float


async def forecast_cash_flow(
    tenant_id: str,
    db: AsyncSession,
    months_ahead: int = 12,
) -> list[CashFlowPoint]:
    """
    Project cash flow using linear regression on historical data.
    Uses last 12 months of income/expenses to predict future.
    """
    from app.models.finance import JournalEntry, JournalLine
    cutoff = datetime.now(timezone.utc) - timedelta(days=365)

    result = await db.execute(
        select(JournalLine)
        .options(joinedload(JournalLine.entry))
        .join(JournalEntry)
        .where(JournalEntry.created_at >= cutoff)
    )
    lines = result.scalars().all()

    monthly_income = {}
    monthly_expenses = {}
    for line in lines:
        month_key = line.entry.created_at.strftime("%Y-%m")
        amount = float(line.debit - line.credit)
        if amount > 0:
            monthly_income[month_key] = monthly_income.get(month_key, 0) + abs(amount)
        else:
            monthly_expenses[month_key] = monthly_expenses.get(month_key, 0) + abs(amount)

    income_values = list(monthly_income.values()) or [0]
    expense_values = list(monthly_expenses.values()) or [0]

    avg_income = statistics.mean(income_values[-6:]) if len(income_values) >= 3 else statistics.mean(income_values)
    avg_expenses = statistics.mean(expense_values[-6:]) if len(expense_values) >= 3 else statistics.mean(expense_values)

    # Simple linear trend
    income_trend = _linear_trend(income_values, months_ahead)
    expense_trend = _linear_trend(expense_values, months_ahead)

    forecast = []
    cumulative = 0
    for i in range(months_ahead):
        month = (datetime.now(timezone.utc) + timedelta(days=30 * (i + 1))).strftime("%Y-%m")
        projected_income = max(income_trend[i], avg_income * 0.5) if income_trend else avg_income
        projected_expenses = max(expense_trend[i], avg_expenses * 0.3) if expense_trend else avg_expenses
        net = round(projected_income - projected_expenses, 2)
        cumulative += net
        forecast.append(CashFlowPoint(
            month=month,
            projected_income=round(projected_income, 2),
            projected_expenses=round(projected_expenses, 2),
            net_cashflow=net,
            cumulative=round(cumulative, 2),
        ))

    return forecast


async def analyze_budget_variance(
    tenant_id: str,
    db: AsyncSession,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
) -> list[BudgetVariance]:
    """Compare actual spending vs budget by category."""
    from app.models.finance import JournalEntry, JournalLine, Budget, BudgetLine

    if not period_start:
        period_start = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    if not period_end:
        period_end = datetime.now(timezone.utc).isoformat()

    budgets_result = await db.execute(select(Budget))
    budgets = budgets_result.scalars().all()

    variances = []
    for budget in budgets:
        lines_result = await db.execute(
            select(BudgetLine).where(BudgetLine.budget_id == budget.id)
        )
        for line in lines_result.scalars().all():
            actual_result = await db.execute(
                select(func.coalesce(func.sum(JournalLine.debit), 0))
                .join(JournalEntry)
                .where(
                    JournalEntry.created_at >= period_start,
                    JournalEntry.created_at <= period_end,
                )
            )
            actual = float(actual_result.scalar() or 0)
            budgeted = line.planned_amount or 0
            variance = round(actual - budgeted, 2)
            variance_pct = round((variance / budgeted * 100), 1) if budgeted else 0
            variances.append(BudgetVariance(
                category=line.description or "Unknown",
                budgeted=budgeted,
                actual=actual,
                variance=variance,
                variance_pct=variance_pct,
            ))

    return sorted(variances, key=lambda v: abs(v.variance), reverse=True)


async def detect_anomalies(
    tenant_id: str,
    db: AsyncSession,
    lookback_days: int = 90,
) -> list[Anomaly]:
    """Detect anomalies — transactions more than 2 standard deviations from mean."""
    from app.models.finance import JournalEntry, JournalLine
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    result = await db.execute(
        select(JournalLine)
        .options(joinedload(JournalLine.entry))
        .join(JournalEntry)
        .where(JournalEntry.created_at >= cutoff)
    )
    lines = result.scalars().all()

    if len(lines) < 10:
        return []

    amounts = [abs(float(line.debit - line.credit)) for line in lines]
    mean = statistics.mean(amounts)
    stdev = statistics.stdev(amounts) if len(amounts) > 1 else 0

    if stdev == 0:
        return []

    anomalies = []
    for line in lines:
        amount = float(line.debit - line.credit)
        z = (abs(amount) - mean) / stdev if stdev > 0 else 0
        if abs(z) > 2.0:
            anomalies.append(Anomaly(
                id=line.id,
                date=line.entry.created_at.isoformat(),
                description=line.entry.description or f"Transaction {line.id[:8]}",
                amount=round(amount, 2),
                z_score=round(z, 2),
            ))

    return sorted(anomalies, key=lambda a: abs(a.z_score), reverse=True)[:20]


async def generate_financial_report(
    tenant_id: str,
    db: AsyncSession,
    report_type: str = "summary",
) -> dict:
    """Generate structured financial summary."""
    from app.models.finance import JournalEntry, JournalLine, Invoice
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    income_result = await db.execute(
        select(func.coalesce(func.sum(JournalLine.debit), 0))
        .join(JournalEntry)
        .where(
            JournalLine.debit > 0,
            JournalEntry.created_at >= cutoff,
        )
    )
    expense_result = await db.execute(
        select(func.coalesce(func.sum(JournalLine.debit), 0))
        .join(JournalEntry)
        .where(
            JournalLine.debit < 0,
            JournalEntry.created_at >= cutoff,
        )
    )
    pending_invoices = await db.execute(
        select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
            Invoice.status == "pending",
        )
    )

    total_income = round(abs(income_result.scalar() or 0), 2)
    total_expenses = round(abs(expense_result.scalar() or 0), 2)
    pending = round(abs(pending_invoices.scalar() or 0), 2)

    return {
        "report_type": report_type,
        "period": "last_30_days",
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_income": round(total_income - total_expenses, 2),
        "profit_margin": round((total_income - total_expenses) / total_income * 100, 1) if total_income else 0,
        "pending_invoices": pending,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _linear_trend(values: list[float], periods_ahead: int) -> list[float]:
    """Simple linear regression projection."""
    if not values:
        return []
    if len(values) < 2:
        return [values[-1]] * periods_ahead

    n = len(values)
    x_mean = (n - 1) / 2
    y_mean = statistics.mean(values)

    numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    slope = numerator / denominator if denominator != 0 else 0
    intercept = y_mean - slope * x_mean

    return [max(intercept + slope * (n + i), 0) for i in range(periods_ahead)]
