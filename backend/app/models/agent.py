from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey, JSON, Boolean, Float, Integer, Text, func
from datetime import datetime, timezone
from typing import Optional
import uuid
from app.models.base import Base, GlobalBase

try:
    from pgvector.sqlalchemy import Vector
    _HAS_PGVECTOR = True
except ImportError:
    _HAS_PGVECTOR = False

class Agent(Base):
    """
    Representa un agente de IA en la plataforma.
    """
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar: Mapped[str] = mapped_column(String(255), nullable=True)
    agent_type: Mapped[str] = mapped_column(String(50), default="conversational", nullable=False) # conversational, crm, workflow, code, custom, omni_master
    
    # AI settings
    ai_model: Mapped[str] = mapped_column(String(100), default="meta-llama/llama-3.3-70b-instruct:free", nullable=False)
    ai_system_prompt: Mapped[str] = mapped_column(String, default="Eres un útil y amable asistente virtual.", nullable=False)
    ai_temperature: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    ai_tone: Mapped[str] = mapped_column(String(100), default="Profesional y amable", nullable=False)
    ai_guardrails: Mapped[str] = mapped_column(String, default="", nullable=False)
    agent_settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False) # JSON dictionary of custom settings
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Marketplace fields
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    marketplace_published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    marketplace_category: Mapped[str] = mapped_column(String(50), nullable=True)
    marketplace_price: Mapped[float] = mapped_column(Float, default=0)
    marketplace_rating: Mapped[float] = mapped_column(Float, default=0)
    marketplace_downloads: Mapped[int] = mapped_column(Integer, default=0)
    marketplace_tags: Mapped[list] = mapped_column(JSON, default=list)
    marketplace_tools: Mapped[list] = mapped_column(JSON, default=list)
    marketplace_preview_image: Mapped[str] = mapped_column(String(500), nullable=True)
    marketplace_author: Mapped[str] = mapped_column(String(200), nullable=True)
    marketplace_author_tenant: Mapped[str] = mapped_column(String(100), nullable=True)

    # Relationships
    config = relationship("AgentConfig", back_populates="agent", uselist=False, cascade="all, delete-orphan")
    execution_runs = relationship("AgentExecutionRun", back_populates="agent", cascade="all, delete-orphan")
    triggers = relationship("Trigger", back_populates="agent", cascade="all, delete-orphan")
    test_suites = relationship("TestSuite", back_populates="agent", cascade="all, delete-orphan")
    code_modules = relationship("CodeModule", back_populates="agent", cascade="all, delete-orphan")
    knowledge_docs = relationship("KnowledgeDocument", back_populates="agent", cascade="all, delete-orphan")

class AgentConfig(Base):
    """
    Configuración de límites y schemas para la ejecución de un Agente.
    """
    __tablename__ = "agent_configs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    input_schema: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False) # JSON schema para inputs
    output_schema: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False) # JSON schema para outputs
    max_loops: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    max_tokens_per_run: Mapped[int] = mapped_column(Integer, default=50000, nullable=False)

    # Relationships
    agent = relationship("Agent", back_populates="config")

class AgentExecutionRun(Base):
    """
    Historial de ejecuciones de un Agente de IA.
    """
    __tablename__ = "agent_execution_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    trigger_source: Mapped[str] = mapped_column(String(100), nullable=False) # webhook, cron, event, manual
    status: Mapped[str] = mapped_column(String(50), default="running", nullable=False) # running, success, failed
    
    input_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    output_result: Mapped[dict] = mapped_column(JSON, nullable=True)
    
    loop_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    token_usage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    execution_trace: Mapped[str] = mapped_column(String, default="", nullable=False) # JSON string of steps
    paused_state: Mapped[dict] = mapped_column(JSON, nullable=True) # Serialized pause-resume execution context
    trace_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    span_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    agent = relationship("Agent", back_populates="execution_runs")

class AgentOrchestrationRun(Base):
    """
    Orchestration run record for hierarchical multi-agent executions.
    """
    __tablename__ = "agent_orchestration_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    mode: Mapped[str] = mapped_column(String(50), default="hierarchical", nullable=False)
    agent_ids: Mapped[str] = mapped_column(String, default="[]", nullable=False)
    input_message: Mapped[str] = mapped_column(String, default="", nullable=False)
    output_result: Mapped[str] = mapped_column(String, nullable=True)
    execution_trace: Mapped[str] = mapped_column(String, nullable=True)
    token_usage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="running", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_components: Mapped[dict] = mapped_column(JSON, nullable=True)
    changed_by: Mapped[str] = mapped_column(String, nullable=True)
    change_description: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class ModelPerformance(Base):
    __tablename__ = "model_performance"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    task_category: Mapped[str] = mapped_column(String, nullable=True)
    avg_latency_ms: Mapped[float] = mapped_column(Float, default=0)
    success_rate: Mapped[float] = mapped_column(Float, default=1.0)
    avg_tokens_per_query: Mapped[int] = mapped_column(Integer, default=0)
    cost_per_1000_queries_usd: Mapped[float] = mapped_column(Float, default=0)
    total_calls: Mapped[int] = mapped_column(Integer, default=0)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class ConversationEpoch(Base):
    __tablename__ = "conversation_epochs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    epoch_number: Mapped[int] = mapped_column(Integer, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    turn_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    turn_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class EpisodicMemory(Base):
    __tablename__ = "episodic_memories"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    memory_type: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_info: Mapped[dict] = mapped_column(JSON, nullable=True)
    entities: Mapped[dict] = mapped_column(JSON, nullable=True)
    importance_score: Mapped[float] = mapped_column(Float, default=0.5)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    if _HAS_PGVECTOR:
        embedding: Mapped[list] = mapped_column(Vector(1536), nullable=True)
    else:
        embedding: Mapped[str] = mapped_column(Text, nullable=True)


class UserMemoryPreference(Base):
    __tablename__ = "user_memory_preferences"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    preferences: Mapped[dict] = mapped_column(JSON, nullable=False)
    frequently_used_tools: Mapped[dict] = mapped_column(JSON, nullable=True)
    last_active_module: Mapped[str] = mapped_column(String, nullable=True)
    total_conversations: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False)
    conversation_history: Mapped[dict] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String, default="active")
    context_snapshot: Mapped[dict] = mapped_column(JSON, nullable=True)
    total_turns: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentTriggerConfig(Base):
    __tablename__ = "agent_event_trigger_configs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    filter_condition: Mapped[dict] = mapped_column(JSON, nullable=True)
    input_template: Mapped[str] = mapped_column(Text, nullable=True)
    auto_approve: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    max_executions_per_hour: Mapped[int] = mapped_column(Integer, default=10)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())


class AgentTriggerQueue(Base):
    __tablename__ = "agent_trigger_queue"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    trigger_id: Mapped[str] = mapped_column(String, ForeignKey("agent_event_trigger_configs.id"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False)
    event_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    generated_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending")
    execution_run_id: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str] = mapped_column(String, nullable=True)


class AgentSchedule(Base):
    __tablename__ = "agent_schedules"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    cron_expression: Mapped[str] = mapped_column(String, nullable=False)
    input_template: Mapped[str] = mapped_column(Text, nullable=False)
    input_variables: Mapped[dict] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_status: Mapped[str] = mapped_column(String, nullable=True)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())


class AgentBudgetCap(Base):
    __tablename__ = "agent_budget_caps"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False, unique=True)
    daily_limit_usd: Mapped[float] = mapped_column(Float, default=10.0)
    monthly_limit_usd: Mapped[float] = mapped_column(Float, default=200.0)
    warning_threshold: Mapped[float] = mapped_column(Float, default=0.8)
    is_enforced: Mapped[bool] = mapped_column(Boolean, default=True)
    daily_spent: Mapped[float] = mapped_column(Float, default=0.0)
    monthly_spent: Mapped[float] = mapped_column(Float, default=0.0)
    last_reset_daily: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    last_reset_monthly: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())


class HumanApprovalRequest(Base):
    __tablename__ = "human_approval_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("agent_execution_runs.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    action_description: Mapped[str] = mapped_column(Text, nullable=False)
    action_type: Mapped[str] = mapped_column(String, nullable=False)
    tool_name: Mapped[str] = mapped_column(String, nullable=False)
    tool_args: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending")
    approver_id: Mapped[str] = mapped_column(String, nullable=True)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())


class AgentHealthRecord(Base):
    __tablename__ = "agent_health_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    response_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())


class AgentApiKey(Base):
    __tablename__ = "agent_api_keys"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    key_hash: Mapped[str] = mapped_column(String, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String, nullable=False)
    allowed_agents: Mapped[dict] = mapped_column(JSON, nullable=True)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class SkillCertification(Base):
    __tablename__ = "skill_certifications"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False)
    skill_name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    test_results: Mapped[dict] = mapped_column(JSON, nullable=True)
    certified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())


class AgentReputationScore(Base):
    __tablename__ = "agent_reputation_scores"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, default=50.0)
    user_rating_score: Mapped[float] = mapped_column(Float, default=50.0)
    completion_score: Mapped[float] = mapped_column(Float, default=50.0)
    quality_score: Mapped[float] = mapped_column(Float, default=50.0)
    cost_efficiency_score: Mapped[float] = mapped_column(Float, default=50.0)
    total_runs_evaluated: Mapped[int] = mapped_column(Integer, default=0)
    trend: Mapped[str] = mapped_column(String, default="stable")
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())


class GlobalSharedContextEntry(GlobalBase):
    __tablename__ = "global_shared_context_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    orchestration_id: Mapped[str] = mapped_column(String, nullable=False)
    agent_id: Mapped[str] = mapped_column(String, nullable=False)
    topic: Mapped[str] = mapped_column(String, nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    ttl_seconds: Mapped[int] = mapped_column(Integer, default=300)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    if _HAS_PGVECTOR:
        embedding = mapped_column(Vector(1536), nullable=True)
    else:
        embedding: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False)
    agent_type: Mapped[str] = mapped_column(String, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    scenarios_total: Mapped[int] = mapped_column(Integer, default=20)
    scenarios_ran: Mapped[int] = mapped_column(Integer, default=0)
    scenario_results: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    avg_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(50), default="running")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())


class CollaborativeRoom(Base):
    __tablename__ = "collaborative_rooms"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_session_id: Mapped[str] = mapped_column(String, ForeignKey("agent_sessions.id"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=True)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())


class CollaborativeRoomParticipant(Base):
    __tablename__ = "collaborative_room_participants"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    room_id: Mapped[str] = mapped_column(String, ForeignKey("collaborative_rooms.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    left_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class CollaborativeMessage(Base):
    __tablename__ = "collaborative_messages"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    room_id: Mapped[str] = mapped_column(String, ForeignKey("collaborative_rooms.id"), nullable=False)
    sender_user_id: Mapped[str] = mapped_column(String, nullable=True)
    sender_agent_id: Mapped[str] = mapped_column(String, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String, default="message")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())


class DemoSession(Base):
    __tablename__ = "demo_sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    recording_name: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="recording")
    events: Mapped[dict] = mapped_column(JSON, nullable=True)
    event_count: Mapped[int] = mapped_column(Integer, default=0)
    total_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    converted_skill_id: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class DemoSkill(Base):
    __tablename__ = "demo_skills"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    recording_id: Mapped[str] = mapped_column(String, ForeignKey("demo_sessions.id"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    steps: Mapped[dict] = mapped_column(JSON, nullable=False)
    triggers: Mapped[dict] = mapped_column(JSON, nullable=True)
    preconditions: Mapped[dict] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    replay_success_rate: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())


class DiscoveryReport(Base):
    __tablename__ = "discovery_reports"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    report_type: Mapped[str] = mapped_column(String, default="weekly")
    analysis_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    tasks_discovered: Mapped[dict] = mapped_column(JSON, nullable=True)
    tools_suggested: Mapped[dict] = mapped_column(JSON, nullable=True)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="generated")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())


class LLMCallAudit(Base):
    __tablename__ = "llm_call_audits"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    run_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("agent_execution_runs.id", ondelete="SET NULL"), nullable=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    completion_text: Mapped[str] = mapped_column(Text, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class SharedContextEntry(Base):
    __tablename__ = "shared_context_entries"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    orchestration_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False, default="default")
    topic: Mapped[str] = mapped_column(String, nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    ttl_seconds: Mapped[int] = mapped_column(Integer, default=300)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
