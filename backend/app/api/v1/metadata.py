from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.api.dependencies import get_tenant_db, require_roles
from app.models.metadata import PageMetadata
from app.schemas.metadata import PageMetadataCreate, PageMetadataUpdate, PageMetadataResponse
import uuid

router = APIRouter()

@router.get("/", response_model=List[PageMetadataResponse])
async def get_all_metadata(db: AsyncSession = Depends(get_tenant_db)):
    """Obtener todas las configuraciones de páginas dinámicas."""
    result = await db.execute(select(PageMetadata).order_by(PageMetadata.module_name, PageMetadata.page_name))
    return result.scalars().all()

@router.get("/{module_name}/{page_name}", response_model=PageMetadataResponse)
async def get_page_metadata(module_name: str, page_name: str, db: AsyncSession = Depends(get_tenant_db)):
    """Obtener la configuración de una página dinámica específica."""
    result = await db.execute(
        select(PageMetadata)
        .where(PageMetadata.module_name == module_name, PageMetadata.page_name == page_name)
    )
    metadata = result.scalar_one_or_none()
    if not metadata:
        raise HTTPException(status_code=404, detail="Metadatos no encontrados")
    return metadata

@router.post("/", response_model=PageMetadataResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(["hr_admin", "sys_admin"]))])
async def create_metadata(data: PageMetadataCreate, db: AsyncSession = Depends(get_tenant_db)):
    """Crear nueva configuración dinámica de página."""
    result = await db.execute(
        select(PageMetadata)
        .where(PageMetadata.module_name == data.module_name, PageMetadata.page_name == data.page_name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Ya existe una configuración para esta página y módulo.")

    new_meta = PageMetadata(
        id=uuid.uuid4().hex,
        **data.model_dump()
    )
    db.add(new_meta)
    await db.commit()
    await db.refresh(new_meta)
    return new_meta

@router.put("/{module_name}/{page_name}", response_model=PageMetadataResponse, dependencies=[Depends(require_roles(["hr_admin", "sys_admin"]))])
async def update_metadata(module_name: str, page_name: str, data: PageMetadataUpdate, db: AsyncSession = Depends(get_tenant_db)):
    """Actualizar configuración dinámica de una página."""
    result = await db.execute(
        select(PageMetadata)
        .where(PageMetadata.module_name == module_name, PageMetadata.page_name == page_name)
    )
    metadata = result.scalar_one_or_none()
    if not metadata:
        raise HTTPException(status_code=404, detail="Metadatos no encontrados")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(metadata, field, value)

    await db.commit()
    await db.refresh(metadata)
    return metadata

@router.delete("/{module_name}/{page_name}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles(["sys_admin"]))])
async def delete_metadata(module_name: str, page_name: str, db: AsyncSession = Depends(get_tenant_db)):
    """Eliminar configuración dinámica de página."""
    result = await db.execute(
        select(PageMetadata)
        .where(PageMetadata.module_name == module_name, PageMetadata.page_name == page_name)
    )
    metadata = result.scalar_one_or_none()
    if not metadata:
        raise HTTPException(status_code=404, detail="Metadatos no encontrados")

    await db.delete(metadata)
    await db.commit()
    return None
