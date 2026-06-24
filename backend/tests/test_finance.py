import pytest
from datetime import datetime, timezone, timedelta
from app.models.finance import JournalEntry, JournalLine, Budget, BudgetLine, Invoice
from app.services.finance_forecasting import (
    forecast_cash_flow,
    analyze_budget_variance,
    detect_anomalies,
    generate_financial_report
)

@pytest.mark.asyncio
async def test_budget_variance_and_reports(db):
    # 1. Create a dummy Budget and BudgetLine
    budget = Budget(
        name="Engineering Budget",
        fiscal_year=2026,
        total_amount=1000.0,
        spent_amount=200.0,
        department="Engineering"
    )
    db.add(budget)
    await db.flush()

    budget_line = BudgetLine(
        budget_id=budget.id,
        description="Software Licenses",
        planned_amount=800.0,
        actual_amount=200.0
    )
    db.add(budget_line)

    # 2. Create Journal Entries and Lines
    entry = JournalEntry(
        reference="TXN-001",
        description="SaaS Subscription payment",
        created_at=datetime.now(timezone.utc)
    )
    db.add(entry)
    await db.flush()

    line = JournalLine(
        entry_id=entry.id,
        account_code="629000",
        account_name="Software Expense",
        debit=200.0,
        credit=0.0
    )
    db.add(line)

    # 3. Create a pending Invoice
    invoice = Invoice(
        invoice_number="INV-ENG-001",
        type="payable",
        vendor_client="GitHub",
        amount=150.0,
        tax_amount=30.0,
        total_amount=180.0,
        status="pending"
    )
    db.add(invoice)
    await db.commit()

    # 4. Run forecasting and variance functions
    variances = await analyze_budget_variance(tenant_id="test_tenant", db=db)
    assert len(variances) > 0
    assert variances[0].category == "Software Licenses"
    assert variances[0].budgeted == 800.0
    assert variances[0].actual == 200.0
    assert variances[0].variance == -600.0

    report = await generate_financial_report(tenant_id="test_tenant", db=db)
    assert report["total_income"] == 200.0  # debit > 0
    assert report["total_expenses"] == 0.0
    assert report["pending_invoices"] == 180.0

@pytest.mark.asyncio
async def test_forecast_cash_flow_linear(db):
    # Insert multiple historical transactions to allow linear trend
    now = datetime.now(timezone.utc)
    for i in range(12):
        created_date = now - timedelta(days=30 * i)
        entry = JournalEntry(
            reference=f"TXN-HIST-{i}",
            description=f"Monthly bill {i}",
            created_at=created_date
        )
        db.add(entry)
        await db.flush()

        # Income vs Expense pattern
        debit_val = 1000.0 + (i * 50.0)
        credit_val = 600.0 + (i * 20.0)
        line1 = JournalLine(
            entry_id=entry.id,
            account_code="100000",
            account_name="Bank",
            debit=debit_val,
            credit=0.0
        )
        line2 = JournalLine(
            entry_id=entry.id,
            account_code="600000",
            account_name="Expense",
            debit=0.0,
            credit=credit_val
        )
        db.add(line1)
        db.add(line2)

    await db.commit()

    forecast = await forecast_cash_flow(tenant_id="test_tenant", db=db, months_ahead=6)
    assert len(forecast) == 6
    for pt in forecast:
        assert pt.projected_income > 0
        assert pt.projected_expenses > 0
        assert pt.net_cashflow != 0

@pytest.mark.asyncio
async def test_detect_anomalies(db):
    now = datetime.now(timezone.utc)
    
    # Add 12 baseline normal transactions (e.g. ~100 USD)
    for i in range(12):
        entry = JournalEntry(
            reference=f"TXN-NORM-{i}",
            description=f"Regular charge {i}",
            created_at=now - timedelta(days=i)
        )
        db.add(entry)
        await db.flush()

        line = JournalLine(
            entry_id=entry.id,
            account_code="600000",
            account_name="Standard Expense",
            debit=100.0,
            credit=0.0
        )
        db.add(line)

    # Add 1 anomaly transaction (e.g. 5000 USD, which is > 2 stdev away)
    anomaly_entry = JournalEntry(
        reference="TXN-ANOMALY",
        description="Huge out-of-pattern expense",
        created_at=now
    )
    db.add(anomaly_entry)
    await db.flush()

    anomaly_line = JournalLine(
        entry_id=anomaly_entry.id,
        account_code="600000",
        account_name="Special Expense",
        debit=5000.0,
        credit=0.0
    )
    db.add(anomaly_line)
    await db.commit()

    anomalies = await detect_anomalies(tenant_id="test_tenant", db=db, lookback_days=30)
    assert len(anomalies) > 0
    assert anomalies[0].amount == 5000.0
    assert anomalies[0].z_score > 2.0
