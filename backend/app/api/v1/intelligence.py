import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Dict, Any

from app.api.dependencies import get_tenant_db, get_current_user, require_roles
from app.models.intelligence import Dashboard, DashboardWidget, KpiAlert
from app.schemas.intelligence import (
    DashboardCreate, DashboardUpdate, DashboardResponse,
    DashboardWidgetCreate, DashboardWidgetUpdate, DashboardWidgetResponse
)
from app.api.middleware.rate_limit import RateLimiter
from app.services.digest_service import generate_notification_digest
from app.services.department_analytics import get_department_analytics
from app.core.cache import cache_get, cache_set

router = APIRouter()

WIDGET_CACHE_NS = "widget_data"
WIDGET_CACHE_TTL = 120


async def _widget_headcount_forecasting(db: AsyncSession, cache: bool = True) -> Dict[str, Any]:
    from app.models.user import User

    if cache:
        cached = await cache_get(WIDGET_CACHE_NS, "headcount_forecasting")
        if cached:
            return cached

    res = await db.execute(select(func.count(User.id)).where(User.is_active == True))
    count = res.scalar() or 0
    if count == 0:
        result = {
            "labels": ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul (Proj)", "Ago (Proj)"],
            "data": [110, 115, 122, 130, 135, 142, 150, 160]
        }
    else:
        result = {
            "labels": ["Actual", "Mes +1 (Proj)", "Mes +2 (Proj)", "Mes +3 (Proj)"],
            "data": [count, int(count * 1.05), int(count * 1.10), int(count * 1.15)]
        }

    if cache:
        await cache_set(WIDGET_CACHE_NS, "headcount_forecasting", result, ttl=WIDGET_CACHE_TTL)
    return result


async def _widget_cost_per_hire(db: AsyncSession, cache: bool = True) -> Dict[str, Any]:
    from app.models.finance import ExpenseClaim
    from app.models.hire import Candidate

    if cache:
        cached = await cache_get(WIDGET_CACHE_NS, "cost_per_hire")
        if cached:
            return cached

    exp_res = await db.execute(select(func.sum(ExpenseClaim.total_amount)).where(ExpenseClaim.category == "Recruitment", ExpenseClaim.status == "approved"))
    total_recruitment_cost = exp_res.scalar() or 0

    cand_res = await db.execute(select(func.count(Candidate.id)).where(Candidate.stage == "hired"))
    total_hires = cand_res.scalar() or 0

    if total_recruitment_cost == 0 or total_hires == 0:
        result = {
            "labels": ["Q1", "Q2", "Q3", "Q4"],
            "data": [4500, 4200, 3800, 3500],
            "benchmark": 4000
        }
    else:
        cph = total_recruitment_cost / total_hires
        result = {
            "total": f"${cph:,.2f}",
            "growth": "calculado",
            "data": [cph]
        }

    if cache:
        await cache_set(WIDGET_CACHE_NS, "cost_per_hire", result, ttl=WIDGET_CACHE_TTL)
    return result


async def _widget_training_roi(db: AsyncSession, cache: bool = True) -> Dict[str, Any]:
    from app.models.training import CourseEnrollment

    if cache:
        cached = await cache_get(WIDGET_CACHE_NS, "training_roi")
        if cached:
            return cached

    enroll_res = await db.execute(select(func.count(CourseEnrollment.id)).where(CourseEnrollment.status == "completed"))
    completed = enroll_res.scalar() or 0

    if completed == 0:
        result = {
            "labels": ["Liderazgo", "Ventas B2B", "Compliance", "IT Security"],
            "data": [85, 92, 45, 78],
            "type": "bar_chart"
        }
    else:
        result = {
            "total": f"{completed} Cursos Completados",
            "growth": "Positivo",
            "data": [completed]
        }

    if cache:
        await cache_set(WIDGET_CACHE_NS, "training_roi", result, ttl=WIDGET_CACHE_TTL)
    return result


async def _widget_department_pl(db: AsyncSession, cache: bool = True) -> Dict[str, Any]:
    from app.models.finance import ExpenseClaim
    from app.models.user import User

    if cache:
        cached = await cache_get(WIDGET_CACHE_NS, "department_pl")
        if cached:
            return cached

    dept_res = await db.execute(
        select(User.department, func.sum(ExpenseClaim.total_amount))
        .join(ExpenseClaim, ExpenseClaim.user_id == User.id)
        .where(ExpenseClaim.status == "approved")
        .group_by(User.department)
        .order_by(func.sum(ExpenseClaim.total_amount).desc())
        .limit(8)
    )
    rows = dept_res.all()
    if rows:
        result = {
            "labels": [r[0] or "Sin departamento" for r in rows],
            "data": [float(r[1] or 0) for r in rows],
            "type": "pie_chart",
            "is_demo": False
        }
    else:
        result = {
            "labels": ["Ingenieria", "Ventas", "Marketing", "Operaciones"],
            "data": [120000, 350000, 80000, 95000],
            "type": "pie_chart",
            "is_demo": True,
            "message": "Datos de ejemplo — no hay gastos aprobados registrados aun."
        }

    if cache:
        await cache_set(WIDGET_CACHE_NS, "department_pl", result, ttl=WIDGET_CACHE_TTL)
    return result


async def _widget_sales_revenue(db: AsyncSession, cache: bool = True) -> Dict[str, Any]:
    result = {
        "labels": ["Ene", "Feb", "Mar", "Abr", "May", "Jun"],
        "data": [12000, 19000, 15000, 22000, 25000, 30000]
    }
    return result


async def _widget_employee_count(db: AsyncSession, cache: bool = True) -> Dict[str, Any]:
    from app.models.user import User

    if cache:
        cached = await cache_get(WIDGET_CACHE_NS, "employee_count")
        if cached:
            return cached

    res = await db.execute(select(func.count(User.id)))
    count = res.scalar() or 142
    result = {
        "total": count,
        "growth": "+5%"
    }

    if cache:
        await cache_set(WIDGET_CACHE_NS, "employee_count", result, ttl=WIDGET_CACHE_TTL)
    return result


async def _widget_task_completion(db: AsyncSession, cache: bool = True) -> Dict[str, Any]:
    result = {
        "labels": ["To Do", "In Progress", "Review", "Done"],
        "data": [45, 20, 15, 80]
    }
    return result


WIDGET_SOURCES: Dict[str, Any] = {
    "headcount_forecasting": _widget_headcount_forecasting,
    "cost_per_hire": _widget_cost_per_hire,
    "training_roi": _widget_training_roi,
    "department_pl": _widget_department_pl,
    "sales_revenue": _widget_sales_revenue,
    "employee_count": _widget_employee_count,
    "task_completion": _widget_task_completion,
}


def _register_widget_source(name: str, func):
    WIDGET_SOURCES[name] = func


async def _evaluate_kpi_alerts(data_source: str, response_data: dict, db: AsyncSession, current_user: dict) -> None:
    """Evaluate KPI alerts for the current user and send push notifications if thresholds are crossed."""
    import json

    sub = current_user.get("sub", "")
    user_id = sub.split("|")[-1] if "|" in sub else sub

    alerts_query = select(KpiAlert).join(DashboardWidget).where(
        KpiAlert.user_id == user_id,
        KpiAlert.is_active == True,
        DashboardWidget.data_source == data_source
    )
    alerts_res = await db.execute(alerts_query)
    alerts = alerts_res.scalars().all()

    current_val = None
    if "total" in response_data and isinstance(response_data["total"], (int, float)):
        current_val = response_data["total"]
    elif "data" in response_data and len(response_data.get("data", [])) > 0:
        data_values = [v for v in response_data["data"] if isinstance(v, (int, float))]
        if data_values:
            current_val = data_values[-1]

    if not current_val or not alerts:
        return

    try:
        from app.models.push import PushSubscription
        from app.api.v1.notifications import send_web_push

        subscriptions = await db.execute(
            select(PushSubscription).where(PushSubscription.user_id == user_id)
        )
        subs = subscriptions.scalars().all()

        for alert in alerts:
            triggered = False
            if alert.condition == ">" and current_val > alert.threshold:
                triggered = True
            elif alert.condition == "<" and current_val < alert.threshold:
                triggered = True

            if triggered:
                payload = {
                    "title": "Alerta de KPI",
                    "body": f"La metrica {data_source} ha superado el limite de {alert.threshold}. Valor actual: {current_val}",
                    "url": "/dashboard/intelligence"
                }
                for sub in subs:
                    try:
                        await send_web_push(db, user_id, payload)
                    except Exception:
                        pass

                alert.is_active = False
                db.add(alert)
        await db.commit()
    except Exception:
        pass


# --- Dashboards ---

@router.get("/dashboards", response_model=List[DashboardResponse])
async def get_dashboards(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    query = select(Dashboard).options(selectinload(Dashboard.widgets))
    result = await db.execute(query)
    return result.scalars().unique().all()


@router.post("/dashboards", response_model=DashboardResponse)
async def create_dashboard(
    data: DashboardCreate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    db_dashboard = Dashboard(**data.model_dump())
    db.add(db_dashboard)
    await db.commit()
    await db.refresh(db_dashboard)

    query = select(Dashboard).options(selectinload(Dashboard.widgets)).where(Dashboard.id == db_dashboard.id)
    result = await db.execute(query)
    return result.scalars().first()


@router.delete("/dashboards/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dashboard(
    dashboard_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    result = await db.execute(select(Dashboard).where(Dashboard.id == dashboard_id))
    dashboard = result.scalars().first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    await db.delete(dashboard)
    await db.commit()


# --- Widgets ---

@router.post("/widgets", response_model=DashboardWidgetResponse)
async def create_widget(
    data: DashboardWidgetCreate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    result = await db.execute(select(Dashboard).where(Dashboard.id == data.dashboard_id))
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Dashboard not found")

    db_widget = DashboardWidget(**data.model_dump())
    db.add(db_widget)
    await db.commit()
    await db.refresh(db_widget)
    return db_widget


@router.delete("/widgets/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_widget(
    widget_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    result = await db.execute(select(DashboardWidget).where(DashboardWidget.id == widget_id))
    widget = result.scalars().first()
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")

    await db.delete(widget)
    await db.commit()


@router.get("/data/{data_source}")
async def get_widget_data(
    data_source: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    source_func = WIDGET_SOURCES.get(data_source)
    if source_func is None:
        raise HTTPException(status_code=404, detail=f"Unknown data source: {data_source}")

    response_data = await source_func(db, cache=True)
    await _evaluate_kpi_alerts(data_source, response_data, db, current_user)
    return response_data


@router.get("/dashboard/{dashboard_id}/data")
async def get_dashboard_widgets_data(
    dashboard_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Loads all widgets for a dashboard and fetches their data in parallel via asyncio.gather.
    Each widget's data source query is executed concurrently.
    """
    result = await db.execute(
        select(DashboardWidget).where(DashboardWidget.dashboard_id == dashboard_id)
        .order_by(DashboardWidget.layout_y, DashboardWidget.layout_x)
    )
    widgets = result.scalars().all()

    if not widgets:
        return {"widgets": {}}

    async def fetch_widget(w: DashboardWidget) -> Dict[str, Any]:
        source_func = WIDGET_SOURCES.get(w.data_source)
        if source_func is None:
            return {"widget_id": w.id, "data_source": w.data_source, "error": "Unknown source"}
        data = await source_func(db, cache=True)
        return {"widget_id": w.id, "data_source": w.data_source, "data": data}

    tasks = [fetch_widget(w) for w in widgets]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    widget_data = {}
    for i, w in enumerate(widgets):
        r = results[i]
        if isinstance(r, Exception):
            widget_data[w.id] = {"data_source": w.data_source, "error": str(r)}
        else:
            widget_data[w.id] = r

    return {"widgets": widget_data}


# --- People Analytics widget sources (M4) ---

def _register_people_analytics_sources():
    from app.services.people_analytics import (
        get_headcount_trends,
        get_turnover_analysis,
        get_diversity_metrics,
        get_span_of_control,
        get_time_to_hire,
        get_training_roi as pa_training_roi,
    )

    async def _pa_wrapper(func, name, db, cache=True):
        if cache:
            cached = await cache_get(WIDGET_CACHE_NS, name)
            if cached:
                return cached
        result = await func(db)
        if cache:
            await cache_set(WIDGET_CACHE_NS, name, result, ttl=WIDGET_CACHE_TTL)
        return result

    async def _headcount_trend(db, cache=True):
        return await _pa_wrapper(get_headcount_trends, "headcount_trend", db, cache)

    async def _turnover_analysis(db, cache=True):
        return await _pa_wrapper(get_turnover_analysis, "turnover_analysis", db, cache)

    async def _diversity_metrics(db, cache=True):
        return await _pa_wrapper(get_diversity_metrics, "diversity_metrics", db, cache)

    async def _span_control(db, cache=True):
        return await _pa_wrapper(get_span_of_control, "span_control", db, cache)

    async def _time_to_hire(db, cache=True):
        return await _pa_wrapper(get_time_to_hire, "time_to_hire", db, cache)

    async def _training_roi_pa(db, cache=True):
        return await _pa_wrapper(pa_training_roi, "training_roi_m4", db, cache)

    _register_widget_source("headcount_trend", _headcount_trend)
    _register_widget_source("turnover_analysis", _turnover_analysis)
    _register_widget_source("diversity_metrics", _diversity_metrics)
    _register_widget_source("span_control", _span_control)
    _register_widget_source("time_to_hire", _time_to_hire)
    _register_widget_source("training_roi_m4", _training_roi_pa)


_register_people_analytics_sources()


# --- KPI Alerts ---

from pydantic import BaseModel


class KpiAlertCreate(BaseModel):
    condition: str
    threshold: int


@router.post("/widgets/{widget_id}/alerts")
async def create_kpi_alert(
    widget_id: str,
    payload: KpiAlertCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    sub = current_user.get("sub", "")
    user_id = sub.split("|")[-1] if "|" in sub else sub

    alert = KpiAlert(
        widget_id=widget_id,
        user_id=user_id,
        condition=payload.condition,
        threshold=payload.threshold
    )
    db.add(alert)
    await db.commit()
    return {"message": "Alerta configurada exitosamente"}


# --- Skills Matrix ---

@router.get("/skills-matrix")
async def get_skills_matrix(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    from app.services.skills_matrix import get_skills_matrix as compute_matrix
    return await compute_matrix(db)


@router.get("/skills-gap/{user_id}")
async def get_skills_gap_endpoint(
    user_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    sub = current_user.get("sub", "")
    current_uid = sub.split("|")[-1] if "|" in sub else sub
    
    role = current_user.get("role", "employee")
    if role not in ["hr_admin", "sys_admin"] and current_uid != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view other employees' skills gap analysis")
        
    from app.services.skills_matrix import get_skills_gap_analysis
    return await get_skills_gap_analysis(user_id, db)


@router.get("/skills-recommendations/{user_id}")
async def get_skills_recommendations_endpoint(
    user_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    sub = current_user.get("sub", "")
    current_uid = sub.split("|")[-1] if "|" in sub else sub
    
    role = current_user.get("role", "employee")
    if role not in ["hr_admin", "sys_admin"] and current_uid != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view other employees' learning path recommendations")
        
    from app.services.skills_matrix import recommend_learning_path
    return await recommend_learning_path(user_id, db)



@router.get("/anomalies")
async def get_hr_anomalies(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.services.anomaly_detection import compute_hr_anomalies
    return await compute_hr_anomalies(db)


@router.get("/compensation-analysis")
async def get_compensation_analysis(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.services.compensation import get_compensation_analysis as analyze
    return await analyze(db)


@router.post("/pulse-surveys/respond")
async def respond_pulse_survey(
    body: dict,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("sub", "").split("|")[-1]
    survey_id = body.get("survey_id")
    answers = body.get("answers", {})
    from app.services.pulse_surveys import record_pulse_response
    if not survey_id:
        raise HTTPException(status_code=400, detail="survey_id required")
    return await record_pulse_response(db, survey_id, user_id, answers)


@router.get("/pulse-surveys/trends")
async def get_pulse_trends(
    weeks: int = 8,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.services.pulse_surveys import get_pulse_trends as trends
    return await trends(db, weeks)


@router.get("/digest")
async def get_daily_digest(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    return await generate_notification_digest(db)


@router.get("/department-analytics")
async def get_dept_analytics(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    return await get_department_analytics(db)


@router.get("/attrition-prediction", dependencies=[Depends(RateLimiter("10/minute"))])
async def get_attrition_prediction_endpoint(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.services.predictive_analytics import get_attrition_prediction
    return await get_attrition_prediction(db)


@router.get("/headcount-forecast", dependencies=[Depends(RateLimiter("10/minute"))])
async def get_headcount_forecast_endpoint(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.services.predictive_analytics import get_headcount_forecast
    return await get_headcount_forecast(db)


@router.get("/compensation-benchmarking", dependencies=[Depends(RateLimiter("10/minute"))])
async def get_compensation_benchmarking_endpoint(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.services.predictive_analytics import get_compensation_benchmarking
    return await get_compensation_benchmarking(db)


@router.get("/recruitment-funnel-prediction", dependencies=[Depends(RateLimiter("10/minute"))])
async def get_recruitment_funnel_prediction_endpoint(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.services.predictive_analytics import get_recruitment_funnel_prediction
    return await get_recruitment_funnel_prediction(db)

