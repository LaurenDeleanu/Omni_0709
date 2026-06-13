from sqlalchemy import Column, String, Float, DateTime, ForeignKey, func, Boolean
from sqlalchemy.orm import relationship
import uuid
from app.models.base import Base

class PayrollCycle(Base):
    __tablename__ = "pay_cycles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    period_name = Column(String, nullable=False) # e.g. "May 2026"
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, default="draft") # draft, processing, paid
    total_gross = Column(Float, default=0.0)
    total_net = Column(Float, default=0.0)
    currency = Column(String(3), default="EUR", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    payslips = relationship("Payslip", back_populates="cycle", cascade="all, delete")

class Payslip(Base):
    __tablename__ = "pay_payslips"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cycle_id = Column(String, ForeignKey("pay_cycles.id"), nullable=False)
    employee_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Financial data
    gross_salary = Column(Float, nullable=False, default=0.0)
    deductions = Column(Float, nullable=False, default=0.0)
    net_salary = Column(Float, nullable=False, default=0.0)
    currency = Column(String(3), default="EUR", nullable=False)
    
    status = Column(String, default="draft") # draft, finalized
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    cycle = relationship("PayrollCycle", back_populates="payslips")
    employee = relationship("User")
    line_items = relationship("PayslipLineItem", back_populates="payslip", cascade="all, delete")

class PayslipLineItem(Base):
    __tablename__ = "pay_payslip_lines"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    payslip_id = Column(String, ForeignKey("pay_payslips.id"), nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String, nullable=False) # earning, deduction
    
    payslip = relationship("Payslip", back_populates="line_items")

class TaxRule(Base):
    __tablename__ = "pay_tax_rules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    country_code = Column(String(2), nullable=False) # ES, PT, FR, DE, IT, NL, UK
    name = Column(String, nullable=False) # e.g. "IRPF Tramo 1"
    calculation_type = Column(String, nullable=False) # percentage, fixed_amount
    rate = Column(Float, nullable=False) # 0.19 for 19%, or 50.0 for 50 fixed
    min_salary = Column(Float, nullable=True) # For marginal brackets
    max_salary = Column(Float, nullable=True) # For marginal brackets
    is_deduction = Column(Boolean, default=True)
    is_marginal = Column(Boolean, default=True) # Added based on user preference
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Bonus(Base):
    __tablename__ = "pay_bonuses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(String, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    type = Column(String, nullable=False) # standard, kpi
    status = Column(String, default="pending") # pending, paid
    payslip_id = Column(String, ForeignKey("pay_payslips.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    employee = relationship("User")
    payslip = relationship("Payslip")

