import pytest
import os
import sys
import asyncio
from typing import AsyncGenerator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-32chars")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-32chars--")
os.environ.setdefault("DEBUG_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_HOST", "")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    from app.models.base import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


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
        "company": {"name": "Test Corp", "tax_id": "B12345678", "address": "Calle Test 123, Madrid", "iban": "ES9121000418450200051332", "bic": "CAIXESBBXXX"},
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
        "totals": {"cc_base": 2725.00, "cc_employer_pct": 23.6, "cc_employee_pct": 4.7, "cp_base": 2725.00, "cp_employer_pct": 1.5, "cp_employee_pct": 0.0, "unemp_base": 2725.00, "unemp_employer_pct": 5.5, "unemp_employee_pct": 1.55, "fogasa_base": 2725.00, "fogasa_employer_pct": 0.2, "fp_base": 2725.00, "fp_employer_pct": 0.6, "fp_employee_pct": 0.1},
    }
