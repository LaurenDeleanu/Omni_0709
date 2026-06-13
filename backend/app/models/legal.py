from sqlalchemy import Column, String, Boolean, DateTime, Text, func
import uuid
from app.models.base import Base
import random
import string

def generate_tracking_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

class Contract(Base):
    __tablename__ = "legal_contracts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    party_name = Column(String, nullable=False)
    status = Column(String, default="draft") # draft, pending_signature, active, expired
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    document_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class WhistleblowerReport(Base):
    __tablename__ = "legal_whistleblower_reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tracking_code = Column(String, unique=True, default=generate_tracking_code)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String, nullable=False) # harassment, fraud, safety, other
    status = Column(String, default="open") # open, investigating, resolved
    resolution_message = Column(Text, nullable=True) # For 3-month EU rule feedback
    is_anonymous = Column(Boolean, default=True)
    # Intentionally omitted user_id foreign key to enforce anonymity as per EU law
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DSARTicket(Base):
    __tablename__ = "legal_dsar_tickets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(String, nullable=False)
    employee_name = Column(String, nullable=False)
    request_type = Column(String, nullable=False) # download_data, delete_data
    status = Column(String, default="pending") # pending, processing, completed, rejected
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

class ComplianceAudit(Base):
    __tablename__ = "legal_compliance_audits"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    frequency = Column(String, default="once") # once, monthly, quarterly, annually
    status = Column(String, default="scheduled") # scheduled, in_progress, completed, failed
    audit_type = Column(String, nullable=False) # GDPR, labor_law, contract_review, FUNDAE
    report_summary = Column(Text, nullable=True) # JSON or markdown string of findings
    created_at = Column(DateTime(timezone=True), server_default=func.now())

