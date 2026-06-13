from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.api.dependencies import get_tenant_db, get_current_user
from app.models.agent import DemoSession, DemoSkill
from app.services.demo_recorder import DemonstrationRecorder
from app.services.skill_discovery import SkillDiscovery

router = APIRouter()

demo_recorder = DemonstrationRecorder()
skill_discovery = SkillDiscovery()

# --- Pydantic Schemas ---

class StartRecordingRequest(BaseModel):
    agent_id: str
    recording_name: Optional[str] = None

class RecordActionRequest(BaseModel):
    type: str
    target: str
    payload: Optional[dict] = None
    duration_ms: Optional[int] = None

class ReplayRequest(BaseModel):
    target_agent_id: str

# --- Demo Recorder Endpoints ---

@router.post("/recordings/start")
async def start_recording(
    body: StartRecordingRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("sub", "unknown")
    recording_id = await demo_recorder.start_recording(
        session_id=body.recording_name or "untitled",
        agent_id=body.agent_id,
        user_id=user_id,
        db=db,
    )
    return {"recording_id": recording_id, "status": "recording"}


@router.post("/recordings/{recording_id}/action")
async def record_action(
    recording_id: str,
    body: RecordActionRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    action = {
        "type": body.type,
        "target": body.target,
        "payload": body.payload,
        "duration_ms": body.duration_ms,
    }
    await demo_recorder.record_action(recording_id, action, db)
    return {"status": "recorded", "recording_id": recording_id}


@router.post("/recordings/{recording_id}/stop")
async def stop_recording(
    recording_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    summary = await demo_recorder.stop_recording(recording_id, db)
    return summary


@router.post("/recordings/{recording_id}/convert")
async def convert_recording(
    recording_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    result = await demo_recorder.convert_to_agent_skill(recording_id, db)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return {
        "skill_id": result.skill_id,
        "name": result.name,
        "steps_count": result.steps_count,
        "success": result.success,
    }


@router.post("/recordings/{recording_id}/replay")
async def replay_recording(
    recording_id: str,
    body: ReplayRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("sub", "unknown")
    result = await demo_recorder.replay_demonstration(
        recording_id=recording_id,
        target_agent_id=body.target_agent_id,
        user_id=user_id,
        db=db,
    )
    return result


@router.get("/recordings")
async def list_recordings(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    from sqlalchemy import select
    result = await db.execute(
        select(DemoSession).order_by(DemoSession.created_at.desc()).limit(50)
    )
    recordings = result.scalars().all()
    return [
        {
            "id": r.id,
            "agent_id": r.agent_id,
            "recording_name": r.recording_name,
            "status": r.status,
            "event_count": r.event_count,
            "total_duration_ms": r.total_duration_ms,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in recordings
    ]


@router.get("/skills")
async def list_skills(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    from sqlalchemy import select
    result = await db.execute(
        select(DemoSkill).order_by(DemoSkill.created_at.desc()).limit(50)
    )
    skills = result.scalars().all()
    return [
        {
            "id": s.id,
            "recording_id": s.recording_id,
            "agent_id": s.agent_id,
            "name": s.name,
            "description": s.description,
            "is_active": s.is_active,
            "replay_success_rate": s.replay_success_rate,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in skills
    ]


# --- Skill Discovery Endpoints ---

@router.post("/discovery/analyze")
async def trigger_discovery(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    report = await skill_discovery.generate_discovery_report(db)
    return {
        "analysis": {
            "top_tools": report.analysis.top_tools if report.analysis else [],
            "top_patterns": report.analysis.top_patterns if report.analysis else [],
        },
        "tasks_discovered": [
            {
                "name": t.name,
                "frequency": t.frequency,
                "suggested_skill": t.suggested_skill,
                "potential_savings_hours": t.potential_savings_hours,
            }
            for t in report.tasks
        ],
        "tools_suggested": [
            {
                "name": s.name,
                "module": s.module,
                "description": s.description,
                "demand_rating": s.demand_rating,
            }
            for s in report.suggestions
        ],
        "confidence_scores": report.confidence_scores,
    }


@router.get("/discovery/reports")
async def list_discovery_reports(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    reports = await skill_discovery.get_discovery_reports(db)
    return [
        {
            "id": r.id,
            "report_type": r.report_type,
            "status": r.status,
            "executive_summary": r.executive_summary,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reports
    ]


@router.get("/discovery/reports/{report_id}")
async def get_discovery_report(
    report_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    report = await skill_discovery.get_discovery_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "id": report.id,
        "report_type": report.report_type,
        "status": report.status,
        "executive_summary": report.executive_summary,
        "analysis_data": report.analysis_data,
        "tasks_discovered": report.tasks_discovered,
        "tools_suggested": report.tools_suggested,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


@router.get("/discovery/tasks")
async def list_discovered_tasks(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    tasks = await skill_discovery.discover_repetitive_tasks(db, min_frequency=5)
    return [
        {
            "name": t.name,
            "tool_sequence": t.tool_sequence,
            "frequency": t.frequency,
            "users_affected": t.users_affected,
            "potential_savings_hours": t.potential_savings_hours,
            "suggested_skill": t.suggested_skill,
        }
        for t in tasks
    ]


@router.get("/discovery/suggestions")
async def list_tool_suggestions(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    suggestions = await skill_discovery.suggest_new_tools(db)
    return [
        {
            "name": s.name,
            "module": s.module,
            "description": s.description,
            "inputs": s.inputs,
            "outputs": s.outputs,
            "demand_rating": s.demand_rating,
        }
        for s in suggestions
    ]
