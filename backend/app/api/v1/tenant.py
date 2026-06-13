from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.dependencies import get_global_db, require_roles, get_current_user, get_current_user_optional
from app.models.tenant import Tenant
from app.services.feature_flags import get_flags, set_flag
import os
import uuid
import shutil
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class TenantSettingsUpdate(BaseModel):
    name: Optional[str] = None
    primary_color: Optional[str] = None

@router.get("/settings")
async def get_tenant_settings(
    db: AsyncSession = Depends(get_global_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Obtiene la configuración básica y apariencia del tenant."""
    tenant_id = None
    if current_user:
        app_metadata = current_user.get("https://successcore.com/app_metadata", {})
        tenant_id = app_metadata.get("tenant_id")
        if not tenant_id:
            tenant_id = current_user.get("tenant_id")
        
    if not tenant_id:
        tenant_id = "acme_corp"
        
    result = await db.execute(select(Tenant).where(Tenant.schema_name == tenant_id))
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")
        
    return {
        "id": tenant.id,
        "name": tenant.name,
        "schema_name": tenant.schema_name,
        "logo_url": tenant.logo_url,
        "primary_color": tenant.primary_color
    }

@router.put("/settings")
async def update_tenant_settings(
    settings_in: TenantSettingsUpdate,
    db: AsyncSession = Depends(get_global_db),
    current_user: dict = Depends(require_roles(["sys_admin", "hr_admin"]))
):
    """Actualiza la configuración (nombre, color)."""
    app_metadata = current_user.get("https://successcore.com/app_metadata", {})
    tenant_id = app_metadata.get("tenant_id")
    
    if not tenant_id:
        tenant_id = current_user.get("tenant_id")
        
    if not tenant_id:
        tenant_id = "acme_corp"
    
    result = await db.execute(select(Tenant).where(Tenant.schema_name == tenant_id))
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")
        
    if settings_in.name is not None:
        tenant.name = settings_in.name
    if settings_in.primary_color is not None:
        tenant.primary_color = settings_in.primary_color
        
    await db.commit()
    return {"message": "Configuración actualizada correctamente"}

@router.post("/logo")
async def upload_tenant_logo(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_global_db),
    current_user: dict = Depends(require_roles(["sys_admin", "hr_admin"]))
):
    """Sube un logo y actualiza logo_url del tenant."""
    # Validación básica (debería ser más robusta)
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")
        
    # Crear carpeta uploads si no existe
    upload_dir = os.path.join(os.getcwd(), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generar nombre único
    ext = file.filename.split(".")[-1]
    filename = f"logo_tenant-acme_{uuid.uuid4().hex[:8]}.{ext}"
    file_path = os.path.join(upload_dir, filename)
    
    # Guardar archivo
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Actualizar BD
    app_metadata = current_user.get("https://successcore.com/app_metadata", {})
    tenant_id = app_metadata.get("tenant_id")
    
    if not tenant_id:
        tenant_id = current_user.get("tenant_id")
        
    if not tenant_id:
        tenant_id = "acme_corp"
    
    result = await db.execute(select(Tenant).where(Tenant.schema_name == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant:
        tenant.logo_url = f"http://localhost:8000/uploads/{filename}"
        await db.commit()
        return {"logo_url": tenant.logo_url}


@router.get("/feature-flags")
async def get_feature_flags(
    current_user: dict = Depends(get_current_user_optional)
):
    tenant_id = current_user.get("https://successcore.com/app_metadata", {}).get("tenant_id", "") if current_user else ""
    return {"flags": get_flags(tenant_id) if tenant_id else dict(get_flags("default"))}


@router.put("/feature-flags/{flag}")
async def update_feature_flag(
    flag: str,
    body: dict,
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    tenant_id = current_user.get("https://successcore.com/app_metadata", {}).get("tenant_id", "")
    enabled = body.get("enabled", False)
    return set_flag(tenant_id, flag, enabled)
    raise HTTPException(status_code=404, detail="Tenant no encontrado")
