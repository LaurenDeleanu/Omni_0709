import pytest


@pytest.mark.asyncio
async def test_signup_valid(async_client, test_db):
    response = await async_client.post(
        "/api/v1/signup",
        json={
            "company_name": "TestCorp",
            "admin_email": "admin@testcorp.com",
            "admin_password": "securepass123",
            "admin_name": "Admin User",
            "tier": "FREE",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "tenant_id" in data
    assert data["tier"] == "FREE"


@pytest.mark.asyncio
async def test_signup_missing_fields(async_client):
    response = await async_client.post(
        "/api/v1/signup",
        json={
            "company_name": "TestCorp",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_signup_validate_available(async_client):
    response = await async_client.post(
        "/api/v1/signup/validate",
        json={
            "company_name": "UniqueName12345",
            "email": "unique@neverexists.com",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
