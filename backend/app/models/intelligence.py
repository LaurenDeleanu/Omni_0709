from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
import uuid
from app.models.base import Base

class Dashboard(Base):
    __tablename__ = "intel_dashboards"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    owner_id = Column(String, ForeignKey("users.id"), nullable=True)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    widgets = relationship("DashboardWidget", back_populates="dashboard", cascade="all, delete-orphan")

class DashboardWidget(Base):
    __tablename__ = "intel_widgets"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dashboard_id = Column(String, ForeignKey("intel_dashboards.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    widget_type = Column(String, nullable=False) # "bar_chart", "pie_chart", "line_chart", "stat_card"
    data_source = Column(String, nullable=False) # E.g., "sales_revenue", "employee_count", "task_completion"
    config = Column(JSON, nullable=True) # Additional configuration (colors, filters)
    layout_x = Column(Integer, default=0) # Grid X position
    layout_y = Column(Integer, default=0) # Grid Y position
    layout_w = Column(Integer, default=1) # Grid width
    layout_h = Column(Integer, default=1) # Grid height
    
    dashboard = relationship("Dashboard", back_populates="widgets")
    alerts = relationship("KpiAlert", back_populates="widget", cascade="all, delete-orphan")

class KpiAlert(Base):
    __tablename__ = "intel_kpi_alerts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    widget_id = Column(String, ForeignKey("intel_widgets.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    condition = Column(String, nullable=False) # ">", "<", "=="
    threshold = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    
    widget = relationship("DashboardWidget", back_populates="alerts")
