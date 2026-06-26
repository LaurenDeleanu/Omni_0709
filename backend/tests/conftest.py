import os
import sys
import tempfile
import atexit
import asyncio
from typing import AsyncGenerator

_db_file = os.path.join(tempfile.gettempdir(), f"pytest_omnius_{os.getpid()}.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-32chars--")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-for-pytest--")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_db_file}")
os.environ.setdefault("REDIS_HOST", "")
os.environ.setdefault("DEBUG_MODE", "true")


def _cleanup_db():
    for path in (_db_file, _db_file + "-wal", _db_file + "-shm"):
        try:
            os.remove(path)
        except OSError:
            pass


atexit.register(_cleanup_db)

import pytest
from contextlib import asynccontextmanager
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


def pytest_configure(config):
    config.inicfg["asyncio_mode"] = "auto"

@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


import slowapi

_slowapi_noop = lambda self, *a, **kw: (lambda f: f)
slowapi.Limiter.limit = _slowapi_noop


# Monkey-patch redis — prevent connection attempts during tests
from app.core import redis as _redis_module


async def _mock_get_redis():
    return None


_redis_module.get_redis = _mock_get_redis


# ── Build test app ──────────────────────────────────────────────────────────

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.database import engine as _app_engine


@asynccontextmanager
async def _test_lifespan(app: FastAPI):
    yield


_test_app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Test app",
    version=settings.VERSION,
    lifespan=_test_lifespan,
)


_test_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from app.api.v1 import users, signup, documents, agents

_test_app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["Users"])
_test_app.include_router(signup.router, prefix=f"{settings.API_V1_STR}", tags=["Public Signup"])
_test_app.include_router(documents.router, prefix=f"{settings.API_V1_STR}", tags=["Documents"])
_test_app.include_router(agents.router, prefix=f"{settings.API_V1_STR}/agents", tags=["AI Agents"])


@_test_app.get("/health", tags=["System"])
async def test_health_check():
    return {"status": "ok", "message": "Test health"}


# ── Shared session factory ──────────────────────────────────────────────────

TestSessionLocal = async_sessionmaker(
    bind=_app_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def _override_get_global_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


async def _override_get_tenant_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        session.info["tenant_id"] = "test_tenant"
        yield session


async def _override_get_current_user():
    return {
        "sub": "test-user-id",
        "email": "test@test.com",
        "tenant_id": "test_tenant",
        "https://successcore.com/app_metadata": {
            "tenant_id": "test_tenant",
            "roles": ["hr_admin", "super_admin"],
        },
        "roles": ["hr_admin", "super_admin"],
    }


from app.api.dependencies import get_global_db, get_tenant_db, get_current_user

_test_app.dependency_overrides[get_current_user] = _override_get_current_user
_test_app.dependency_overrides[get_tenant_db] = _override_get_tenant_db
_test_app.dependency_overrides[get_global_db] = _override_get_global_db


# ── Table creation fixture ──────────────────────────────────────────────────


@pytest.fixture(scope="session", autouse=True)
def _create_tables_once():
    import app.models.user
    import app.models.tenant
    import app.models.agent
    from app.models.base import Base, GlobalBase
    import asyncio as _asyncio

    async def _create():
        async with _app_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(GlobalBase.metadata.create_all)

    _asyncio.run(_create())


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=_test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        session.info["tenant_id"] = "test_tenant"
        yield session


@pytest.fixture(scope="session")
async def db_engine():
    from app.models.base import Base, GlobalBase
    import app.models.user
    import app.models.tenant
    import app.models.agent

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(GlobalBase.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db(db_engine):
    session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
def auth_headers() -> dict:
    from jose import jwt as jose_jwt
    from app.core.config import settings
    from datetime import datetime, timedelta, timezone

    token_payload = {
        "sub": "test-user-id",
        "email": "test@test.com",
        "tenant_id": "test_tenant",
        "jti": "test-jti",
        "roles": ["hr_admin", "super_admin"],
        "https://successcore.com/app_metadata": {
            "tenant_id": "test_tenant",
            "roles": ["hr_admin", "super_admin"],
        },
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
        "iat": datetime.now(timezone.utc),
    }
    token = jose_jwt.encode(token_payload, settings.SECRET_KEY, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_agent_data():
    return {
        "name": "Test Agent",
        "agent_type": "hr_assistant",
        "ai_model": "gpt-4o-mini",
        "ai_system_prompt": "You are a test assistant.",
        "ai_temperature": 0.5,
        "ai_tone": "Professional",
    }


@pytest.fixture
def sample_user_data():
    return {
        "email": "test@successcore.com",
        "full_name": "Test User",
        "role": "employee",
        "department": "Engineering",
        "is_active": True,
    }


@pytest.fixture
def sample_payslip_data():
    return {
        "employee": {
            "full_name": "María García López",
            "tax_id": "12345678Z",
            "department": "Engineering",
            "position": "Senior Developer",
            "category": "Técnico Titulado",
            "contribution_group": "1",
            "ss_number": "281234567890",
            "seniority": "3 años",
            "contract_type": "Indefinido",
            "workday_type": "Completa",
        },
        "company": {
            "name": "Test Corp",
            "tax_id": "B12345678",
            "address": "Calle Test 123, Madrid",
            "iban": "ES9121000418450200051332",
            "bic": "CAIXESBBXXX",
        },
        "period": {"label": "Junio 2026"},
        "doc_type": "NÓMINA",
        "language": "es",
        "currency": "EUR",
        "issue_date": "30/06/2026",
        "generated_at": "2026-06-30T00:00:00",
        "payslip_id": "test-payslip-001",
        "irpf_rate": 15.0,
        "earnings": [
            {"concept": "Salario Base", "amount": 2500.00},
            {"concept": "Plus Convenio", "amount": 150.00},
            {"concept": "Antigüedad", "amount": 75.00},
        ],
        "deductions": [
            {"concept": "Contingencias Comunes", "rate_pct": 4.7, "amount": 128.08},
            {"concept": "Desempleo", "rate_pct": 1.55, "amount": 42.24},
            {"concept": "Formación Profesional", "rate_pct": 0.1, "amount": 2.73},
            {"concept": "IRPF", "rate_pct": 15.0, "amount": 408.75},
        ],
        "totals": {
            "cc_base": 2725.00,
            "cc_employer_pct": 23.6,
            "cc_employee_pct": 4.7,
            "cp_base": 2725.00,
            "cp_employer_pct": 1.5,
            "cp_employee_pct": 0.0,
            "unemp_base": 2725.00,
            "unemp_employer_pct": 5.5,
            "unemp_employee_pct": 1.55,
            "fogasa_base": 2725.00,
            "fogasa_employer_pct": 0.2,
            "fp_base": 2725.00,
            "fp_employer_pct": 0.6,
            "fp_employee_pct": 0.1,
        },
    }
