from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Dict, Any

from app.api.dependencies import get_tenant_db, require_roles
from app.services.workflow_engine import execute_workflow

router = APIRouter()


class WorkflowExecuteRequest(BaseModel):
    definition: dict
    input_data: dict = {}


class WorkflowDefinition(BaseModel):
    name: str
    description: str = ""
    nodes: list
    edges: list


@router.post("/execute")
async def execute_workflow_endpoint(
    body: WorkflowExecuteRequest,
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    try:
        result = await execute_workflow(body.definition, body.input_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connectors")
async def list_connectors(
    _: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    from app.services.workflow_engine import NODE_TYPES
    return {
        "connectors": [
            {"type": k, "params": list(v["params"])} for k, v in NODE_TYPES.items()
        ]
    }
