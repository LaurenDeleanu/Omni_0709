from sqlalchemy import Column, String, Float, Integer, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
import uuid
from app.models.base import Base

class Project(Base):
    __tablename__ = "work_projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    client_id = Column(String, ForeignKey("sales_clients.id"), nullable=True)
    status = Column(String, default="planning") # planning, active, on_hold, completed
    due_date = Column(DateTime(timezone=True), nullable=True)
    budget = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    tasks = relationship("app.models.work.Task", back_populates="project", cascade="all, delete")

class KanbanBoard(Base):
    __tablename__ = "work_boards"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("work_projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    
    project = relationship("app.models.work.Project")
    columns = relationship("app.models.work.BoardColumn", back_populates="board", cascade="all, delete")

class BoardColumn(Base):
    __tablename__ = "work_columns"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    board_id = Column(String, ForeignKey("work_boards.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    order_index = Column(Integer, default=0)
    
    board = relationship("app.models.work.KanbanBoard", back_populates="columns")

class Sprint(Base):
    __tablename__ = "work_sprints"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("work_projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="planned") # planned, active, completed

class WikiPage(Base):
    __tablename__ = "work_wiki_pages"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    author_id = Column(String, ForeignKey("users.id"), nullable=True)
    project_id = Column(String, ForeignKey("work_projects.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Task(Base):
    __tablename__ = "work_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("work_projects.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    assignee_id = Column(String, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="todo") # legacy
    column_id = Column(String, ForeignKey("work_columns.id", ondelete="SET NULL"), nullable=True)
    sprint_id = Column(String, ForeignKey("work_sprints.id", ondelete="SET NULL"), nullable=True)
    order_index = Column(Integer, default=0)
    priority = Column(String, default="medium") # low, medium, high
    due_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    project = relationship("app.models.work.Project", back_populates="tasks")
