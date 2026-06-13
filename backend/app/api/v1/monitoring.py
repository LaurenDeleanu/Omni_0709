from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Dict, Any

from app.api.dependencies import get_tenant_db, require_roles
from app.models.agent import AgentExecutionRun
from app.services.model_fallback import get_provider_health
from app.services.llm_cache import cache_stats
from app.services.api_analytics import get_analytics, reset_analytics
from app.services.agent_cost_analytics import get_agent_cost_analytics
from app.services.agent_heatmap import get_agent_heatmap
from app.services.agent_run_export import export_agent_runs_csv
from app.services.system_health import get_system_health
from app.services.concurrency_limiter import get_concurrency_status
from app.services.run_compare import compare_agent_runs
from app.services.rate_alerts import get_rate_limit_alerts, reset_rate_limit_alerts
from app.services.pool_monitor import get_db_pool_stats as fetch_db_pool_stats
from app.services.dept_usage import get_dept_usage_stats
import json

router = APIRouter()

@router.get("/metrics")
async def get_observability_metrics(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Retorna agregados históricos de costos, latencias y ejecuciones de agentes de IA para el Dashboard de Monitoreo.
    """
    # 1. Total runs count
    total_runs_stmt = select(func.count(AgentExecutionRun.id))
    total_runs_res = await db.execute(total_runs_stmt)
    total_runs = total_runs_res.scalar() or 0
    
    # 2. Status counts
    success_stmt = select(func.count(AgentExecutionRun.id)).where(AgentExecutionRun.status == "success")
    success_res = await db.execute(success_stmt)
    success_count = success_res.scalar() or 0
    
    # 3. Sum of costs, tokens, and avg latency
    aggregates_stmt = select(
        func.sum(AgentExecutionRun.cost_usd),
        func.sum(AgentExecutionRun.token_usage),
        func.avg(AgentExecutionRun.latency_ms)
    )
    agg_res = await db.execute(aggregates_stmt)
    total_cost, total_tokens, avg_latency = agg_res.first()
    
    # 4. Recent execution logs for table
    recent_runs_stmt = select(AgentExecutionRun).order_by(AgentExecutionRun.created_at.desc()).limit(15)
    recent_runs_res = await db.execute(recent_runs_stmt)
    recent_runs = recent_runs_res.scalars().all()
    
    recent_list = [
        {
            "id": r.id,
            "agent_id": r.agent_id,
            "trigger_source": r.trigger_source,
            "status": r.status,
            "token_usage": r.token_usage,
            "cost_usd": r.cost_usd,
            "latency_ms": r.latency_ms,
            "created_at": r.created_at.isoformat()
        } for r in recent_runs
    ]
    
    return {
        "summary": {
            "total_runs": total_runs,
            "success_rate": (success_count / total_runs * 100) if total_runs > 0 else 100.0,
            "failed_runs": max(0, total_runs - success_count),
            "total_cost_usd": float(total_cost or 0.0),
            "total_tokens": int(total_tokens or 0),
            "avg_latency_ms": float(avg_latency or 0.0)
        },
        "recent_runs": recent_list
    }

@router.get("/runs/{run_id}/trace")
async def get_execution_run_trace(
    run_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """
    Obtiene la traza de pasos detallada de una corrida de ejecución de agente.
    """
    res = await db.execute(select(AgentExecutionRun).where(AgentExecutionRun.id == run_id))
    run = res.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Registro de ejecución no encontrado")
        
    trace_data = []
    if run.execution_trace:
        try:
            trace_data = json.loads(run.execution_trace)
        except:
            trace_data = [{"step": "raw_log", "details": run.execution_trace}]
            
    return {
        "run_id": run.id,
        "agent_id": run.agent_id,
        "trigger_source": run.trigger_source,
        "status": run.status,
        "input_payload": run.input_payload,
        "output_result": run.output_result,
        "created_at": run.created_at.isoformat(),
        "trace": trace_data
    }


@router.get("/provider-health")
async def get_provider_health_status(
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    health = get_provider_health()
    return {"providers": health.get_all_stats()}


@router.get("/cache-stats")
async def get_cache_statistics(
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    return cache_stats()


@router.get("/api-analytics")
async def get_api_analytics(
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    return get_analytics()


@router.post("/api-analytics/reset")
async def reset_api_analytics(
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    reset_analytics()
    return {"status": "reset"}


@router.get("/agent-costs")
async def get_agent_cost_breakdown(
    weeks: int = Query(12, le=52),
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    return await get_agent_cost_analytics(db, weeks)


@router.get("/agent-heatmap")
async def get_agent_heatmap_endpoint(
    days: int = 30,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    return await get_agent_heatmap(db, days)


@router.get("/agent-runs/export-csv")
async def export_agent_runs_csv_endpoint(
    agent_id: str = Query(""),
    limit: int = Query(1000, le=5000),
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from fastapi.responses import PlainTextResponse
    csv_data = await export_agent_runs_csv(db, agent_id or None, limit)
    return PlainTextResponse(csv_data, media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=agent_runs.csv"})


@router.get("/system-health")
async def get_system_health_endpoint(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    return await get_system_health(db)


@router.get("/concurrency")
async def get_concurrency(
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    return get_concurrency_status()


@router.get("/runs/compare")
async def compare_runs(
    run_a: str = Query(...),
    run_b: str = Query(...),
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    try:
        return await compare_agent_runs(db, run_a, run_b)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/rate-alerts")
async def get_rate_alerts(
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    return {"alerts": get_rate_limit_alerts()}


@router.post("/rate-alerts/reset")
async def reset_rate_alerts_endpoint(
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    reset_rate_limit_alerts()
    return {"status": "reset"}


@router.get("/pool-stats")
async def get_db_pool_stats(
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    return fetch_db_pool_stats()


@router.get("/dept-usage")
async def get_dept_usage(
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    return get_dept_usage_stats()


@router.get("/agents/{agent_id}/sla")
async def get_agent_sla(
    agent_id: str,
    days: int = Query(30, le=90),
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Retorna las métricas de SLA (p50, p95, p99 de latencia y tasa de éxito) para un agente específico.
    """
    from app.services.agent_cost_analytics import get_agent_sla_metrics
    return await get_agent_sla_metrics(db, agent_id, days)
