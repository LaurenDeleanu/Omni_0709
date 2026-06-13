from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    client_id: Optional[str] = None
    status: Optional[str] = "planning"
    due_date: Optional[datetime] = None
    budget: Optional[float] = 0.0

class ProjectResponse(ProjectCreate):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class BoardColumnCreate(BaseModel):
    name: str
    order_index: Optional[int] = 0

class BoardColumnResponse(BoardColumnCreate):
    id: str
    board_id: str

    class Config:
        from_attributes = True

class KanbanBoardCreate(BaseModel):
    project_id: str
    name: str

class KanbanBoardResponse(KanbanBoardCreate):
    id: str
    columns: List[BoardColumnResponse] = []

    class Config:
        from_attributes = True

class TaskCreate(BaseModel):
    project_id: str
    title: str
    description: Optional[str] = None
    assignee_id: Optional[str] = None
    status: Optional[str] = "todo"
    column_id: Optional[str] = None
    sprint_id: Optional[str] = None
    order_index: Optional[int] = 0
    priority: Optional[str] = "medium"
    due_date: Optional[datetime] = None

class TaskResponse(TaskCreate):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True

class TaskMoveUpdate(BaseModel):
    column_id: Optional[str] = None
    order_index: Optional[int] = None
    status: Optional[str] = None

class WikiPageCreate(BaseModel):
    title: str
    content: Optional[str] = None
    project_id: Optional[str] = None

class WikiPageResponse(WikiPageCreate):
    id: str
    author_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class SprintCreate(BaseModel):
    project_id: str
    name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = "planned"

class SprintResponse(SprintCreate):
    id: str

    class Config:
        from_attributes = True

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    client_id: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None
    budget: Optional[float] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[str] = None
    status: Optional[str] = None
    column_id: Optional[str] = None
    sprint_id: Optional[str] = None
    order_index: Optional[int] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None

