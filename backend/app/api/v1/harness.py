from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.api.dependencies import get_tenant_db, require_roles
from app.models.harness import TestSuite, TestCase, TestRun
from app.services.harness_service import run_evaluation_suite
from app.services.agent_runtime import execute_agent_run
from app.services.llm_router import get_llm_client
import uuid
import json
import time

router = APIRouter()

# --- Pydantic Schemas ---
class TestSuiteCreate(BaseModel):
    name: str
    description: Optional[str] = None

class TestCaseCreate(BaseModel):
    name: str
    input_payload: str
    expected_criteria: str
    mock_collected_data: Optional[dict] = None

# --- Routes ---

@router.get("/agents/{agent_id}/suites")
async def list_test_suites(
    agent_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """
    Lista todos los suites de pruebas de un agente.
    """
    result = await db.execute(
        select(TestSuite)
        .where(TestSuite.agent_id == agent_id)
        .order_by(TestSuite.created_at.desc())
    )
    suites = result.scalars().all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "created_at": s.created_at.isoformat()
        } for s in suites
    ]

@router.post("/agents/{agent_id}/suites", status_code=status.HTTP_201_CREATED)
async def create_test_suite(
    agent_id: str,
    payload: TestSuiteCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Crea un nuevo suite de pruebas para un agente.
    """
    suite = TestSuite(
        id=uuid.uuid4().hex,
        agent_id=agent_id,
        name=payload.name,
        description=payload.description
    )
    db.add(suite)
    await db.commit()
    await db.refresh(suite)
    return {
        "id": suite.id,
        "name": suite.name,
        "description": suite.description
    }

@router.get("/suites/{suite_id}/cases")
async def list_test_cases(
    suite_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """
    Lista los casos de prueba contenidos en un suite.
    """
    result = await db.execute(
        select(TestCase)
        .where(TestCase.suite_id == suite_id)
        .order_by(TestCase.created_at.asc())
    )
    cases = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "input_payload": c.input_payload,
            "expected_criteria": c.expected_criteria,
            "mock_collected_data": c.mock_collected_data
        } for c in cases
    ]

@router.post("/suites/{suite_id}/cases", status_code=status.HTTP_201_CREATED)
async def create_test_case(
    suite_id: str,
    payload: TestCaseCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Crea un nuevo caso de prueba e inyecta la plantilla de criterios a evaluar.
    """
    case = TestCase(
        id=uuid.uuid4().hex,
        suite_id=suite_id,
        name=payload.name,
        input_payload=payload.input_payload,
        expected_criteria=payload.expected_criteria,
        mock_collected_data=payload.mock_collected_data or {}
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)
    return {
        "id": case.id,
        "name": case.name,
        "input_payload": case.input_payload
    }

@router.post("/agents/{agent_id}/suites/{suite_id}/run")
async def execute_test_suite_evaluation(
    agent_id: str,
    suite_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Ejecuta el suite de pruebas en el sandbox y califica con LLM-as-a-Judge.
    """
    try:
        results = await run_evaluation_suite(db, agent_id, suite_id)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/suites/{suite_id}/runs")
async def list_historical_suite_runs(
    suite_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """
    Lista el historial de ejecuciones evaluadas de este suite de pruebas.
    """
    result = await db.execute(
        select(TestRun)
        .where(TestRun.suite_id == suite_id)
        .order_by(TestRun.created_at.desc())
        .limit(10)
    )
    runs = result.scalars().all()
    return [
        {
            "id": r.id,
            "status": r.status,
            "passed_count": r.passed_count,
            "failed_count": r.failed_count,
            "total_count": r.total_count,
            "avg_latency_ms": r.avg_latency_ms,
            "total_cost_usd": r.total_cost_usd,
            "log_details": r.log_details,
            "created_at": r.created_at.isoformat()
        } for r in runs
    ]


@router.post("/agents/{agent_id}/ab-test")
async def run_ab_test(
    agent_id: str,
    body: dict,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    suite_id = body.get("suite_id")
    test_message = body.get("message", "Hello")
    config_a = body.get("config_a", {})
    config_b = body.get("config_b", {})

    if not suite_id:
        raise HTTPException(status_code=400, detail="suite_id is required")

    suite_res = await db.execute(select(TestSuite).where(TestSuite.id == suite_id, TestSuite.agent_id == agent_id))
    suite = suite_res.scalar_one_or_none()
    if not suite:
        raise HTTPException(status_code=404, detail="TestSuite not found")

    from app.models.agent import Agent
    agent_res = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = agent_res.scalar_one_or_none()

    results = []
    for label, config in [("A", config_a), ("B", config_b)]:
        if not config:
            results.append({"variant": label, "status": "skipped", "reason": "no config"})
            continue
        start = time.monotonic()
        variant_agent = agent
        run_result = await execute_agent_run(
            db, agent_id,
            input_payload={"message": test_message},
            trigger_source="harness_ab",
        )
        latency = int((time.monotonic() - start) * 1000)
        results.append({
            "variant": label,
            "config": config,
            "reply": run_result.get("reply", "")[:500],
            "latency_ms": latency,
            "cost_usd": run_result.get("cost_usd", 0),
            "trace_steps": len(run_result.get("trace", [])),
        })

    return {
        "suite_id": suite_id,
        "agent_id": agent_id,
        "message": test_message,
        "variants": results,
        "comparison": {
            "latency_diff_ms": round(results[0].get("latency_ms", 0) - results[1].get("latency_ms", 0), 1) if len(results) == 2 else 0,
        }
    }


@router.post("/agents/{agent_id}/optimize-prompt")
async def optimize_agent_prompt(
    agent_id: str,
    body: dict,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    suite_id = body.get("suite_id")
    if not suite_id:
        raise HTTPException(status_code=400, detail="suite_id is required")

    suite_res = await db.execute(select(TestSuite).where(TestSuite.id == suite_id, TestSuite.agent_id == agent_id))
    if not suite_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="TestSuite not found")

    from app.services.prompt_optimizer import optimize_prompt
    results = await optimize_prompt(db, agent_id, suite_id)
    return results
