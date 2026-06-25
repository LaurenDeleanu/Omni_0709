import pytest
import json
from datetime import datetime, timezone
from app.models.user import User
from app.models.hire import JobPosting, Candidate, Interview
from app.services.platform_tools_business import (
    tool_create_job_posting,
    tool_add_candidate,
    tool_move_candidate_stage,
    tool_schedule_interview
)

@pytest.mark.asyncio
async def test_recruitment_pipeline_flow(db):
    # 1. Create a Job Posting
    job_resp_json = await tool_create_job_posting(
        db=db,
        title="Senior Python Developer",
        department="Engineering",
        description="Looking for an expert Python coder with SQLAlchemy experience.",
        location="Madrid, Spain",
        employment_type="full-time"
    )
    job_resp = json.loads(job_resp_json)
    assert job_resp["success"] is True
    job_id = job_resp["job_id"]

    # Verify JobPosting exists in DB
    job_in_db = await db.get(JobPosting, job_id)
    assert job_in_db is not None
    assert job_in_db.title == "Senior Python Developer"

    # 2. Add a Candidate to the Job Posting
    cand_resp_json = await tool_add_candidate(
        db=db,
        job_id=job_id,
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@example.com",
        phone="+34600112233",
        source="LinkedIn",
        notes="Strong candidate with FastAPI background"
    )
    cand_resp = json.loads(cand_resp_json)
    assert cand_resp["success"] is True
    candidate_id = cand_resp["candidate_id"]

    # Verify Candidate exists in DB
    cand_in_db = await db.get(Candidate, candidate_id)
    assert cand_in_db is not None
    assert cand_in_db.first_name == "Jane"
    assert cand_in_db.stage == "applied"

    # 3. Move Candidate Stage to screening
    move_resp_json = await tool_move_candidate_stage(
        db=db,
        candidate_id=candidate_id,
        new_stage="screening"
    )
    move_resp = json.loads(move_resp_json)
    assert move_resp["success"] is True
    assert move_resp["new_stage"] == "screening"

    # Verify stage changed in DB
    await db.refresh(cand_in_db)
    assert cand_in_db.stage == "screening"

    # 4. Schedule an Interview
    # First, create a User to act as the interviewer
    interviewer = User(
        id="interviewer_user_1",
        email="interviewer@successcore.com",
        full_name="Alex Interviewer",
        is_active=True
    )
    db.add(interviewer)
    await db.commit()

    scheduled_time = datetime(2026, 7, 10, 10, 0, 0, tzinfo=timezone.utc).isoformat()
    interview_resp_json = await tool_schedule_interview(
        db=db,
        candidate_id=candidate_id,
        interviewer_id=interviewer.id,
        scheduled_at=scheduled_time,
        duration_minutes=45,
        interview_type="Technical"
    )
    interview_resp = json.loads(interview_resp_json)
    assert interview_resp["success"] is True
    interview_id = interview_resp["interview_id"]

    # Verify Interview exists in DB
    interview_in_db = await db.get(Interview, interview_id)
    assert interview_in_db is not None
    assert interview_in_db.interview_type == "Technical"
    assert interview_in_db.duration_minutes == 45

    # Move stage to rejected to test invalid / other stages
    reject_resp_json = await tool_move_candidate_stage(
        db=db,
        candidate_id=candidate_id,
        new_stage="rejected"
    )
    reject_resp = json.loads(reject_resp_json)
    assert reject_resp["success"] is True
    
    # Try invalid stage
    invalid_resp_json = await tool_move_candidate_stage(
        db=db,
        candidate_id=candidate_id,
        new_stage="invalid_stage"
    )
    invalid_resp = json.loads(invalid_resp_json)
    assert "error" in invalid_resp
