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


def _get_user_id(current_user: dict) -> str:
    """Extraer el sub (user id) del token JWT y limpiar el prefijo de proveedor."""
    sub = current_user.get("sub", "unknown")
    return sub.split("|")[-1] if "|" in sub else sub


def _get_user_roles(current_user: dict) -> list:
    """Extraer roles del token, misma lógica que require_roles."""
    app_metadata = current_user.get("https://successcore.com/app_metadata", {})
    roles = app_metadata.get("roles", [])
    if not roles:
        roles = current_user.get("https://successcore.com/roles", [])
    if not roles:
        roles = current_user.get("roles", [])
    return roles or []


@router.get("")
async def list_documents(
    user_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Listar documentos de un empleado (contratos legales asociados por nombre).

    HR admin/manager pueden consultar cualquier empleado; el resto solo los suyos.
    """
    from sqlalchemy import select
    from app.models.legal import Contract
    from app.models.user import User

    roles = set(_get_user_roles(current_user))
    requester_id = _get_user_id(current_user)
    target_id = user_id or requester_id

    if target_id != requester_id and not roles & {"hr_admin", "super_admin", "manager"}:
        raise HTTPException(status_code=403, detail="No autorizado para ver documentos de otros empleados")

    result = await db.execute(select(User).where(User.id == target_id))
    user = result.scalar_one_or_none()
    if not user or not user.full_name:
        return {"documents": []}

    result = await db.execute(
        select(Contract)
        .where(Contract.party_name == user.full_name)
        .order_by(Contract.created_at.desc())
    )
    contracts = result.scalars().all()
    return {
        "documents": [
            {
                "id": c.id,
                "name": c.title,
                "type": "contract",
                "status": c.status or "active",
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "url": c.document_url,
            }
            for c in contracts
        ]
    }


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
