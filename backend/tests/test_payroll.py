import pytest
from app.services.tax_calculator import calculate_tax, DEFAULT_BRACKETS

@pytest.mark.asyncio
async def test_calculate_tax_spain():
    # Test for Spain with gross salary of 30,000
    res = await calculate_tax(gross_salary=30000.0, country_code="ES")
    assert res["country_code"] == "ES"
    assert res["currency"] == "EUR"
    assert res["gross_salary"] == 30000.0
    assert res["personal_allowance"] == 5550
    assert res["income_tax"] > 0
    assert res["social_security"] > 0
    assert res["net_salary"] < 30000.0
    assert res["total_deductions"] == res["income_tax"] + res["social_security"]
    assert res["net_salary"] == round(30000.0 - res["total_deductions"], 2)

@pytest.mark.asyncio
async def test_calculate_tax_germany():
    # Test for Germany with gross salary of 50,000
    res = await calculate_tax(gross_salary=50000.0, country_code="DE")
    assert res["country_code"] == "DE"
    assert res["personal_allowance"] == 10908
    assert res["income_tax"] > 0
    assert res["social_security"] > 0
    assert res["net_salary"] < 50000.0

@pytest.mark.asyncio
async def test_calculate_tax_unsupported_country():
    # Test for an unsupported country code
    res = await calculate_tax(gross_salary=40000.0, country_code="XYZ")
    assert res["country_code"] == "XYZ"
    assert res["gross_salary"] == 40000.0
    assert res["net_salary"] == 40000.0
    assert res["income_tax"] == 0
    assert res["social_security"] == 0
    assert "No tax brackets configured" in res["error"]
