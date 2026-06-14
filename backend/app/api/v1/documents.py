"""
documents.py — Document generation API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import logging

from app.api.dependencies import get_tenant_db, get_current_user, require_roles
from app.services.doc_generator import get_available_templates, render_html, generate_pdf

logger = logging.getLogger("successcore.documents")

router = APIRouter(prefix="/documents", tags=["Documents"])


class GenerateRequest(BaseModel):
    template_type: str
    variables: dict
    employee_id: Optional[str] = None


@router.get("/templates")
async def list_templates(current_user: dict = Depends(get_current_user)):
    return {"templates": get_available_templates()}


@router.post("/preview")
async def preview_document(
    body: GenerateRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Return HTML preview of the document."""
    variables = dict(body.variables)

    if body.employee_id:
        variables.update(await _fetch_employee_vars(db, body.employee_id))

    try:
        html = render_html(body.template_type, variables)
        return {"html": html}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/generate")
async def generate_document_endpoint(
    body: GenerateRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin", "super_admin", "manager", "recruiter"])),
):
    """Generate PDF document and return as download."""
    variables = dict(body.variables)

    if body.employee_id:
        variables.update(await _fetch_employee_vars(db, body.employee_id))

    try:
        pdf_bytes = generate_pdf(body.template_type, variables)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise HTTPException(status_code=500, detail="PDF generation failed")

    filename = f"{body.template_type}_{variables.get('employee_name', 'document')}.pdf".replace(" ", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _fetch_employee_vars(db: AsyncSession, employee_id: str) -> dict:
    """Fetch employee data from DB to populate template variables."""
    from sqlalchemy import select
    from app.models.user import User
    result = await db.execute(select(User).where(User.id == employee_id))
    user = result.scalar_one_or_none()
    if not user:
        return {}
    return {
        "employee_name": user.full_name or "",
        "employee_email": user.email or "",
        "employee_id": user.id,
    }
