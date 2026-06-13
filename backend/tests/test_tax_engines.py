import pytest
from app.services.tax_engines.uk_paye import UKTaxEngine
from app.services.tax_engines.pt_irs import PTTaxEngine
from app.services.tax_engines.de_lohnsteuer import DETaxEngine
from app.services.tax_engines.generic import GenericTaxEngine

def test_uk_tax_engine_basic_rate():
    engine = UKTaxEngine()
    result = engine.calculate_taxes(30000.0, [])
    # Allowance is 12570, taxable is 17430
    # Basic rate 20% on 17430 = 3486
    # NI 8% on 17430 = 1394.4
    # Total tax = 4880.4
    assert result.annual_tax == pytest.approx(4880.4, 0.1)
    
def test_pt_tax_engine():
    engine = PTTaxEngine()
    # 24000 / 14 = 1714 monthly -> 28.5% IRS
    result = engine.calculate_taxes(24000.0, [])
    expected_irs = 24000 * 0.285 # 6840
    expected_ss = 24000 * 0.11 # 2640
    expected_total = 6840 + 2640 # 9480
    assert result.annual_tax == pytest.approx(9480.0, 0.1)

def test_de_tax_engine():
    engine = DETaxEngine()
    result = engine.calculate_taxes(50000.0, [])
    # Taxable = 50000 - 10908 = 39092
    # Lohnsteuer = 39092 * 0.24 = 9382.08
    # Social = 50000 * (0.073 + 0.093 + 0.013 + 0.017) = 50000 * 0.196 = 9800
    # Total = 19182.08
    assert result.annual_tax == pytest.approx(19182.08, 0.1)

def test_generic_tax_engine_with_rules():
    engine = GenericTaxEngine()
    rules = [
        {"name": "Flat Tax", "calculation_type": "percentage", "rate": 0.15, "is_deduction": True, "is_marginal": False, "min_salary": None, "max_salary": None}
    ]
    result = engine.calculate_taxes(100000.0, rules)
    assert result.annual_tax == pytest.approx(15000.0, 0.1)
