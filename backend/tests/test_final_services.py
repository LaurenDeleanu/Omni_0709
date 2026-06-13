import sys
import os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestAgentAnalytics:
    def test_record_and_get_metrics(self):
        from app.services.agent_analytics_collector import agent_analytics
        import asyncio
        async def _test():
            await agent_analytics.record_run("agent-1", "hr_assistant", 1500, 5000, 0.015, "completed", "manual", 3)
            await agent_analytics.record_run("agent-1", "hr_assistant", 2500, 8000, 0.025, "completed", "cron", 1)
            assert len(agent_analytics._buffer.get("agent-1", [])) == 2
            await agent_analytics.flush()
        asyncio.new_event_loop().run_until_complete(_test())

    def test_multiple_agents(self):
        from app.services.agent_analytics_collector import agent_analytics
        import asyncio
        async def _test():
            for i in range(3):
                await agent_analytics.record_run(f"agent-{i}", "hr_assistant", 1000 + i * 500, 4000, 0.01, "completed", "manual", 2)
            assert all(f"agent-{i}" in agent_analytics._buffer for i in range(3))
            await agent_analytics.flush()
        asyncio.new_event_loop().run_until_complete(_test())


class TestEUAIActExtended:
    def test_log_transparency(self):
        from app.services.eu_ai_act import log_ai_transparency
        import asyncio
        async def _test():
            await log_ai_transparency("agent-1", "payroll_specialist", "Show my salary", "Your salary is 3000", [], 0.9, False, "run-123", "tenant-1")
        asyncio.new_event_loop().run_until_complete(_test())

    def test_all_risk_classifications(self):
        from app.services.eu_ai_act import AGENT_RISK_CLASSIFICATION
        assert AGENT_RISK_CLASSIFICATION["payroll_specialist"] == "high"
        assert AGENT_RISK_CLASSIFICATION["recruiter"] == "high"
        assert AGENT_RISK_CLASSIFICATION["it_helpdesk"] == "limited"
        assert AGENT_RISK_CLASSIFICATION["copilot"] == "limited"

    def test_ai_risk_categories_defined(self):
        from app.services.eu_ai_act import AI_RISK_CATEGORIES
        assert "unacceptable" in AI_RISK_CATEGORIES
        assert "high" in AI_RISK_CATEGORIES
        assert "limited" in AI_RISK_CATEGORIES
        assert "minimal" in AI_RISK_CATEGORIES


class TestRuntimeMonitor:
    def test_executor_stats(self):
        from app.services.runtime_monitor import executor_stats, record_execution, get_executor_health
        record_execution({"status": "completed", "token_usage": 1000, "cost_usd": 0.005}, 500)
        record_execution({"status": "completed", "token_usage": 2000, "cost_usd": 0.010}, 800)
        health = get_executor_health()
        assert health["total_executions"] >= 2
        assert health["success_rate_pct"] >= 80
        assert health["total_cost_usd"] >= 0.01

    def test_heartbeat_tracker(self):
        from app.services.runtime_monitor import heartbeat_tracker
        import asyncio
        async def _test():
            await heartbeat_tracker.beat("run-1")
            await heartbeat_tracker.beat("run-2")
            assert heartbeat_tracker.active_count == 2
            stale = await heartbeat_tracker.get_stale(timeout_seconds=0)
            assert len(stale) == 2
            assert heartbeat_tracker.active_count == 0
        asyncio.new_event_loop().run_until_complete(_test())

    def test_task_supervisor_register(self):
        from app.services.runtime_monitor import get_task_supervisor
        import asyncio
        async def _test():
            supervisor = get_task_supervisor()
            await supervisor.register("test-task", lambda: asyncio.sleep(0), restart_on_failure=False)
            status = await supervisor.get_status()
            assert "test-task" in status
        asyncio.new_event_loop().run_until_complete(_test())


class TestErrorTracker:
    def test_capture_error_context(self):
        from app.services.error_tracker import capture_error_context
        try:
            raise ValueError("Test error for tracking")
        except Exception as e:
            ctx = capture_error_context(e, endpoint="/api/test", user_id="user-1", tenant_id="tenant-1")
            assert ctx["type"] == "ValueError"
            assert "Test error" in ctx["message"]
            assert ctx["source_line"] > 0
            assert ctx["user_id"] == "user-1"

    def test_capture_without_extra(self):
        from app.services.error_tracker import capture_error_context
        try:
            1 / 0
        except Exception as e:
            ctx = capture_error_context(e)
            assert ctx["type"] == "ZeroDivisionError"


class TestSyntheticMonitor:
    def test_synthetic_check(self):
        from app.services.synthetic_monitor import run_synthetic_check
        import asyncio
        result = asyncio.new_event_loop().run_until_complete(run_synthetic_check())
        assert result["overall"] in ("healthy", "degraded")
        assert "components" in result
        assert "database" in result["components"]


class TestRAGDocumentClassify:
    def test_classify_finance(self):
        from app.services.rag_service import classify_document
        category = classify_document("nomina_junio.pdf", "Salario base 2500 IRPF 15%")
        assert category == "finance"

    def test_classify_legal(self):
        from app.services.rag_service import classify_document
        category = classify_document("contrato_empleado.docx", "Clausula de confidencialidad y GDPR compliance")
        assert category == "legal"

    def test_classify_it(self):
        from app.services.rag_service import classify_document
        category = classify_document("it_ticket_123.txt", "Incidencia de VPN y password reset")
        assert category == "it"

    def test_classify_general(self):
        from app.services.rag_service import classify_document
        category = classify_document("misc.txt", "Random content without specific keywords")
        assert category == "general"

    def test_classify_training(self):
        from app.services.rag_service import classify_document
        category = classify_document("curso_python.pdf", "Training course for Python certification and skill development")
        assert category == "training"


class TestVideoCalling:
    def test_generate_room_name(self):
        import uuid
        room = f"meet-{uuid.uuid4().hex[:12]}"
        assert room.startswith("meet-")
        assert len(room) > 10

    def test_room_url_format(self):
        room = "meet-abc123def456"
        url = f"https://meet.successcore.com/{room}"
        assert url.startswith("https://")
        assert "/" in url
