from fastapi import APIRouter, Depends, HTTPException, FastAPI, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid

from app.api.dependencies import get_tenant_db, get_current_user, require_roles
from app.models.hire import JobPosting, Candidate
from app.models.user import User
from sqlalchemy import func

router = APIRouter()


class PublicJobListing(BaseModel):
    id: str
    title: str
    department: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    description: Optional[str] = None
    posted_date: Optional[str] = None
    status: str


class JobBoardResponse(BaseModel):
    company_name: str = "SuccessCore"
    total_openings: int
    departments: list
    locations: list
    jobs: list


@router.get("/public-jobs", response_model=JobBoardResponse)
async def get_public_jobs(
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(
        select(JobPosting).where(JobPosting.status == "open").order_by(JobPosting.created_at.desc())
    )
    jobs = result.scalars().all()

    listings = []
    departments = set()
    locations = set()
    for j in jobs:
        listings.append(PublicJobListing(
            id=j.id,
            title=j.title,
            department=getattr(j, "department", None),
            location=getattr(j, "location", None),
            employment_type=getattr(j, "employment_type", None),
            description=getattr(j, "description", None),
            posted_date=j.created_at.isoformat() if j.created_at else None,
            status="open",
        ))
        if getattr(j, "department", None):
            departments.add(getattr(j, "department"))
        if getattr(j, "location", None):
            locations.add(getattr(j, "location"))

    return JobBoardResponse(
        total_openings=len(jobs),
        departments=sorted(list(departments)),
        locations=sorted(list(locations)),
        jobs=[l.model_dump() for l in listings],
    )


@router.get("/public-jobs/xml", response_model=None)
async def get_public_jobs_xml(
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(
        select(JobPosting).where(JobPosting.status == "open").order_by(JobPosting.created_at.desc())
    )
    jobs = result.scalars().all()

    base_url = str(request.base_url).rstrip("/")
    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<source>',
        f'  <publisher>SuccessCore HR</publisher>',
        f'  <publisherurl>{base_url}</publisherurl>',
        f'  <lastBuildDate>{datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")}</lastBuildDate>',
    ]
    for j in jobs:
        xml_parts.extend([
            '  <job>',
            f'    <title><![CDATA[{j.title}]]></title>',
            f'    <date><![CDATA[{j.created_at.isoformat() if j.created_at else ""}]]></date>',
            f'    <referencenumber><![CDATA[{j.id}]]></referencenumber>',
            f'    <url><![CDATA[{base_url}/jobs/{j.id}]]></url>',
            f'    <company><![CDATA[SuccessCore]]></company>',
            f'    <city><![CDATA[{getattr(j, "location", "") or ""}]]></city>',
            f'    <state><![CDATA[]]></state>',
            f'    <country><![CDATA[ES]]></country>',
            f'    <description><![CDATA[{getattr(j, "description", "") or ""}]]></description>',
            f'    <jobtype><![CDATA[{getattr(j, "employment_type", "") or ""}]]></jobtype>',
            '  </job>',
        ])
    xml_parts.append('</source>')

    from fastapi.responses import Response
    return Response(content="\n".join(xml_parts), media_type="application/xml")
