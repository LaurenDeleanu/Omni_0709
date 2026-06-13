from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query as QueryParam
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List

from app.api.dependencies import get_tenant_db, get_current_user
from app.models.work import Project, Task, KanbanBoard, BoardColumn, WikiPage, Sprint
from app.schemas.work import (
    ProjectCreate, ProjectResponse, ProjectUpdate,
    KanbanBoardCreate, KanbanBoardResponse,
    BoardColumnCreate, BoardColumnResponse,
    TaskCreate, TaskResponse, TaskMoveUpdate, TaskUpdate,
    WikiPageCreate, WikiPageResponse,
    SprintCreate, SprintResponse
)
from app.services.kanban_ws import connect_kanban, disconnect_kanban, broadcast_kanban_change

router = APIRouter()


@router.websocket("/boards/{board_id}/ws")
async def kanban_websocket(board_id: str, ws: WebSocket):
    await connect_kanban(board_id, ws)
    try:
        while True:
            data = await ws.receive_json()
            event = data.get("event", "unknown")
            await broadcast_kanban_change(board_id, event, data.get("data", {}), sender=ws)
    except WebSocketDisconnect:
        disconnect_kanban(board_id, ws)

# --- Projects ---

@router.get("/projects", response_model=List[ProjectResponse])
async def get_projects(db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    return result.scalars().all()

@router.post("/projects", response_model=ProjectResponse)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_tenant_db)):
    db_proj = Project(**data.model_dump())
    db.add(db_proj)
    await db.commit()
    await db.refresh(db_proj)
    return db_proj

# --- Tasks ---

@router.get("/projects/{project_id}/tasks", response_model=List[TaskResponse])
async def get_project_tasks(project_id: str, db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(Task).where(Task.project_id == project_id).order_by(Task.created_at.desc()))
    return result.scalars().all()

@router.post("/tasks", response_model=TaskResponse)
async def create_task(data: TaskCreate, db: AsyncSession = Depends(get_tenant_db)):
    db_task = Task(**data.model_dump())
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task

@router.put("/tasks/{task_id}/move")
async def move_task(task_id: str, payload: TaskMoveUpdate, db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if payload.column_id is not None:
        task.column_id = payload.column_id
    if payload.order_index is not None:
        task.order_index = payload.order_index
    if payload.status is not None:
        task.status = payload.status
        
    await db.commit()
    return {"message": "Task moved successfully"}

# --- Kanban Boards ---

@router.get("/projects/{project_id}/boards", response_model=List[KanbanBoardResponse])
async def get_project_boards(project_id: str, db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(KanbanBoard).where(KanbanBoard.project_id == project_id).options(selectinload(KanbanBoard.columns)))
    return result.scalars().all()

@router.post("/boards", response_model=KanbanBoardResponse)
async def create_board(data: KanbanBoardCreate, db: AsyncSession = Depends(get_tenant_db)):
    db_board = KanbanBoard(**data.model_dump())
    db.add(db_board)
    await db.commit()
    await db.refresh(db_board)
    
    # Reload with columns
    result = await db.execute(select(KanbanBoard).where(KanbanBoard.id == db_board.id).options(selectinload(KanbanBoard.columns)))
    return result.scalars().first()

@router.post("/boards/{board_id}/columns", response_model=BoardColumnResponse)
async def create_board_column(board_id: str, data: BoardColumnCreate, db: AsyncSession = Depends(get_tenant_db)):
    db_col = BoardColumn(board_id=board_id, **data.model_dump())
    db.add(db_col)
    await db.commit()
    await db.refresh(db_col)
    return db_col

# --- Wiki Pages ---

@router.get("/wiki", response_model=List[WikiPageResponse])
async def get_wiki_pages(project_id: str = None, db: AsyncSession = Depends(get_tenant_db)):
    query = select(WikiPage).order_by(WikiPage.created_at.desc())
    if project_id:
        query = query.where(WikiPage.project_id == project_id)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/wiki", response_model=WikiPageResponse)
async def create_wiki_page(data: WikiPageCreate, db: AsyncSession = Depends(get_tenant_db), current_user = Depends(get_current_user)):
    db_page = WikiPage(**data.model_dump(), author_id=current_user.get("id"))
    db.add(db_page)
    await db.commit()
    await db.refresh(db_page)
    return db_page

@router.put("/wiki/{page_id}", response_model=WikiPageResponse)
async def update_wiki_page(page_id: str, data: WikiPageCreate, db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(WikiPage).where(WikiPage.id == page_id))
    page = result.scalars().first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
        
    page.title = data.title
    page.content = data.content
    await db.commit()
    await db.refresh(page)
    return page

@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, data: ProjectUpdate, db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)
        
    await db.commit()
    await db.refresh(project)
    return project

@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    await db.delete(project)
    await db.commit()
    return {"message": "Project deleted successfully"}

@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, data: TaskUpdate, db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)
        
    await db.commit()
    await db.refresh(task)
    return task

@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    await db.delete(task)
    await db.commit()
    return {"message": "Task deleted successfully"}

@router.delete("/wiki/{page_id}")
async def delete_wiki_page(page_id: str, db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(WikiPage).where(WikiPage.id == page_id))
    page = result.scalars().first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
        
    await db.delete(page)
    await db.commit()
    return {"message": "Page deleted successfully"}
