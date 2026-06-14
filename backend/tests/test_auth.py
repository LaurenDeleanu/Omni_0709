import pytest
from app.core.auth import hash_password
from app.models.user import User
from app.models.tenant import Tenant
from sqlalchemy import select
import uuid
from datetime import datetime, timezone


async def _seed_login_user(db):
    tenant_id = "test_tenant"
    schema = "tenant_test_tenant"

    existing = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if not existing:
        tenant = Tenant(
            id=tenant_id,
            name="Test Company",
            schema_name=schema,
            tier="FREE",
            subscription_status="active",
        )
        db.add(tenant)
        await db.flush()

    existing_user = (await db.execute(select(User).where(User.email == "login-test@test.com"))).scalar_one_or_none()
    if not existing_user:
        user = User(
            id=uuid.uuid4().hex,
            email="login-test@test.com",
            full_name="Login Test User",
            hashed_password=hash_password("testpass123"),
            role="hr_admin",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(user)
        await db.flush()
    await db.commit()


@pytest.mark.asyncio
async def test_login_valid_credentials(async_client, test_db):
    await _seed_login_user(test_db)

    response = await async_client.post(
        "/api/v1/users/login",
        json={
            "email": "login-test@test.com",
            "password": "testpass123",
            "tenant_id": "test_tenant",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "accessToken" in data
    assert data["user"]["email"] == "login-test@test.com"


@pytest.mark.asyncio
async def test_login_invalid_credentials(async_client, test_db):
    await _seed_login_user(test_db)

    response = await async_client.post(
        "/api/v1/users/login",
        json={
            "email": "login-test@test.com",
            "password": "wrongpassword",
            "tenant_id": "test_tenant",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_missing_fields(async_client):
    response = await async_client.post(
        "/api/v1/users/login",
        json={"email": "someone@test.com"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_missing_tenant_id(async_client):
    response = await async_client.post(
        "/api/v1/users/login",
        json={
            "email": "someone@test.com",
            "password": "testpass123",
        },
    )
    assert response.status_code in (401, 422)
