"""
Tests for Phase 4: Scale & Fleet Deployment.
Verifies SLA calculations, cost analytics grouping, telemetry tracing, and streaming responses.
"""
import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.models.agent import Agent, AgentConfig, AgentExecutionRun, LLMCallAudit
from app.services.agent_cost_analytics import get_agent_sla_metrics, get_agent_cost_analytics
from app.services.telemetry import trace_span, OTEL_AVAILABLE

class DummyRun:
    def __init__(self, latency_ms, status="success", created_at=None):
        self.latency_ms = latency_ms
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc)
        self.agent_id = "agent_test_123"
        self.cost_usd = 0.005

# ── SLA & PERCENTILE TESTS ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sla_metrics_calculation():
    """
    Test that get_agent_sla_metrics correctly computes latency percentiles (p50, p95, p99).
    """
    db = AsyncMock()
    
    # 10 runs with latencies 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000 ms
    runs = [DummyRun(latency_ms=i*100) for i in range(1, 11)]
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = runs
    db.execute = AsyncMock(return_value=mock_result)
    
    metrics = await get_agent_sla_metrics(db, agent_id="agent_test_123", days=30)
    
    assert metrics["agent_id"] == "agent_test_123"
    assert metrics["total_runs"] == 10
    assert metrics["success_rate"] == 100.0
    
    # Percentiles:
    # Sorted latencies: [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
    # Length = 10
    # p50 idx = int(10 * 0.5) = 5 -> 600.0
    # p95 idx = int(10 * 0.95) = 9 -> 1000.0
    # p99 idx = int(10 * 0.99) = 9 -> 1000.0
    assert metrics["p50_latency_ms"] == 600.0
    assert metrics["p95_latency_ms"] == 1000.0
    assert metrics["p99_latency_ms"] == 1000.0


@pytest.mark.asyncio
async def test_sla_metrics_empty_history():
    """
    Test SLA metrics fallback values when no run history exists.
    """
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=mock_result)
    
    metrics = await get_agent_sla_metrics(db, agent_id="agent_test_empty", days=30)
    assert metrics["total_runs"] == 0
    assert metrics["p50_latency_ms"] == 0.0
    assert metrics["p95_latency_ms"] == 0.0
    assert metrics["p99_latency_ms"] == 0.0


# ── COST ANALYTICS TESTS ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cost_analytics_grouping():
    """
    Test cost analytics logic and LLM Call Audit records grouping.
    """
    db = AsyncMock()
    
    # Mock runs return
    runs = [DummyRun(latency_ms=150, status="success")]
    mock_runs_res = MagicMock()
    mock_runs_res.scalars.return_value.all.return_value = runs
    
    # Mock agents return
    agent = Agent(id="agent_test_123", name="Fleet Coordinator")
    mock_agents_res = MagicMock()
    mock_agents_res.scalars.return_value.all.return_value = [agent]
    
    # Mock LLM Call Audits grouping return
    mock_audit_row_1 = MagicMock()
    mock_audit_row_1.__getitem__ = MagicMock(side_effect=lambda x: {0: "gpt-4o", 1: 1500, 2: 0.03, 3: 5}[x])
    mock_audit_row_2 = MagicMock()
    mock_audit_row_2.__getitem__ = MagicMock(side_effect=lambda x: {0: "claude-3-5-sonnet", 1: 800, 2: 0.024, 3: 2}[x])
    
    mock_audit_res = MagicMock()
    mock_audit_res.all.return_value = [mock_audit_row_1, mock_audit_row_2]
    
    # db.execute side effect for 3 queries: runs, agents, audits
    db.execute.side_effect = [mock_runs_res, mock_agents_res, mock_audit_res]
    
    analytics = await get_agent_cost_analytics(db, weeks=12)
    
    assert analytics["total_runs"] == 1
    assert len(analytics["model_costs"]) == 2
    
    # Model 1 assertion
    m1 = analytics["model_costs"][0]
    assert m1["model_name"] == "gpt-4o"
    assert m1["total_tokens"] == 1500
    assert m1["total_cost"] == 0.03
    assert m1["total_calls"] == 5

    # Model 2 assertion
    m2 = analytics["model_costs"][1]
    assert m2["model_name"] == "claude-3-5-sonnet"
    assert m2["total_tokens"] == 800
    assert m2["total_cost"] == 0.024
    assert m2["total_calls"] == 2


# ── OPENTELEMETRY TRACING TESTS ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_telemetry_trace_span():
    """
    Verify trace_span context manager starts and ends spans cleanly.
    """
    async with trace_span("test_span_operation", attributes={"custom.attr": "value"}) as span_data:
        assert "trace_id" in span_data
        assert "span_id" in span_data
        assert len(span_data["trace_id"]) == 32
        assert len(span_data["span_id"]) == 16


# ── STREAMING ROUTING & CHUNKS TESTS ─────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.services.agent_streaming.build_agent_context")
@patch("app.services.concurrency_limiter.acquire_run_slot")
@patch("app.services.concurrency_limiter.release_run_slot")
async def test_streaming_react_loop(mock_release_slot, mock_acquire_slot, mock_context):
    """
    Verify execute_agent_run_streaming routes to ReAct loop and streams thought/action steps.
    """
    from app.services.agent_streaming import execute_agent_run_streaming
    
    db = AsyncMock()
    mock_acquire_slot.return_value = True
    
    # Mock agent
    agent = Agent(
        id="react_bot_123",
        name="ReAct Agent",
        agent_type="CONVERSATIONAL",
        ai_model="gpt-4o",
        ai_temperature=0.3,
        agent_settings={"use_react_pattern": True}
    )
    
    # Mock DB query results
    mock_agent_res = MagicMock()
    mock_agent_res.scalar_one_or_none.return_value = agent
    
    config = AgentConfig(agent_id="react_bot_123", max_loops=5)
    mock_config_res = MagicMock()
    mock_config_res.scalar_one_or_none.return_value = config
    
    db.execute.side_effect = [mock_agent_res, mock_config_res]
    
    # Mock build_agent_context return
    mock_context.return_value = ([], [], "Solve HR case #42", "user_123", "tenant_acme", [])
    
    # Mock ReAct loop run_stream
    async def mock_react_run_stream(max_iterations):
        yield {"event": "react_thought", "data": "Checking employee files"}
        yield {"event": "react_action", "data": {"name": "get_employee", "args": {"id": "emp_1"}}}
        yield {"event": "react_observation", "data": "Employee is Alice"}
        yield {"event": "token", "data": "Here is the result: Alice works in HR."}
        yield {"event": "done", "data": ""}
        
    with patch("app.services.react_loop.ReActLoop") as MockReActLoopClass:
        mock_loop_instance = MagicMock()
        mock_loop_instance.run_stream = mock_react_run_stream
        mock_loop_instance._token_count = 100
        MockReActLoopClass.return_value = mock_loop_instance
        
        events = []
        async for event in execute_agent_run_streaming(
            db=db,
            agent_id="react_bot_123",
            input_payload={"message": "Solve HR case #42", "tenant_id": "tenant_acme"},
            trigger_source="manual"
        ):
            events.append(event)
            
        assert len(events) > 0
        
        # Verify sequence of streamed events
        assert events[0]["event"] == "react_thought"
        assert events[0]["data"] == "Checking employee files"
        assert events[1]["event"] == "react_action"
        assert events[1]["data"]["name"] == "get_employee"
        assert events[2]["event"] == "react_observation"
        assert events[2]["data"] == "Employee is Alice"
        assert events[3]["event"] == "token"
        assert events[3]["data"] == {"text": "Here is the result: Alice works in HR."}
        
        # Last event must be "done" containing final payload metrics
        assert events[-1]["event"] == "done"
        assert "run_id" in events[-1]["data"]
        assert events[-1]["data"]["status"] == "success"
        assert events[-1]["data"]["token_usage"] == 100


@pytest.mark.asyncio
async def test_perform_semantic_search_sqlite_fallback(db):
    """
    Verify perform_semantic_search falls back to keyword-based search on SQLite
    and returns matches from SearchIndexEntry.
    """
    from app.models.search_index import SearchIndexEntry
    from app.services.semantic_search import perform_semantic_search

    # Create dummy entries in search index
    entry1 = SearchIndexEntry(
        entity_id="emp_999",
        entity_type="employee",
        title="John Oliver Doe",
        subtitle="Staff Writer",
        content="Writes scripts and performs talk show hosting.",
        route="/dashboard/employees/emp_999",
        embedding=None
    )
    entry2 = SearchIndexEntry(
        entity_id="job_777",
        entity_type="job",
        title="Lead Comedy Writer",
        subtitle="Writing",
        content="Looking for a writer with experience in humor and political satire.",
        route="/dashboard/hire/job_777",
        embedding=None
    )
    db.add(entry1)
    db.add(entry2)
    await db.commit()

    # Query matching John
    results = await perform_semantic_search("John", db, limit=5)
    assert len(results) == 1
    assert results[0]["id"] == "emp_999"
    assert results[0]["title"] == "John Oliver Doe"
    assert results[0]["type"] == "employee"

    # Query matching writer
    results2 = await perform_semantic_search("writer", db, limit=5)
    assert len(results2) == 2
    ids = [r["id"] for r in results2]
    assert "emp_999" in ids
    assert "job_777" in ids

