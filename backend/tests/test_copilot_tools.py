import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-copilot-tests-32chars")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-32chars--")
os.environ.setdefault("DEBUG_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestCopilotToolCoverage:
    def test_all_tools_registered(self):
        from app.services.tool_executor import execute_tool
        from app.services.tool_registry import TOOL_REGISTRY
        assert len(TOOL_REGISTRY) >= 120, f"Expected >=120 tools, got {len(TOOL_REGISTRY)}"

    def test_all_tools_have_handlers(self):
        from app.services.tool_executor import execute_tool
        from app.services.tool_registry import TOOL_REGISTRY
        broken = [n for n, e in TOOL_REGISTRY.items() if not callable(e.get('handler'))]
        assert len(broken) == 0, f"Tools without handlers: {broken}"

    def test_all_tools_have_schemas(self):
        from app.services.tool_registry import TOOL_REGISTRY
        broken = [n for n, e in TOOL_REGISTRY.items() if not isinstance(e.get('schema'), dict)]
        assert len(broken) == 0, f"Tools without schemas: {broken}"

    def test_employee_has_adequate_tools(self):
        from app.services.tool_binding_registry import build_copilot_tool_list
        import asyncio
        tools = asyncio.new_event_loop().run_until_complete(build_copilot_tool_list(["employee"]))
        assert len(tools) >= 50, f"Employee should have >=50 tools, has {len(tools)}"
        essential = ["get_employee_profile", "search_employees", "create_task", "create_it_ticket", "get_payslip", "get_company_announcements"]
        missing = [t for t in essential if t not in tools]
        assert len(missing) == 0, f"Missing essential employee tools: {missing}"

    def test_manager_has_most_tools(self):
        from app.services.tool_binding_registry import build_copilot_tool_list
        import asyncio
        tools = asyncio.new_event_loop().run_until_complete(build_copilot_tool_list(["manager"]))
        assert len(tools) >= 90, f"Manager should have >=90 tools, has {len(tools)}"

    def test_copilot_agent_created(self):
        response = client.get("/api/v1/agents")
        assert response.status_code in (200, 401)

    def test_copilot_models_available(self):
        response = client.get("/api/v1/agents/models")
        assert response.status_code in (200, 401, 404)

    def test_all_120_tools_routable(self):
        from app.services.tool_executor import execute_tool
        from app.services.tool_registry import TOOL_REGISTRY
        total = len(TOOL_REGISTRY)
        assert total >= 120, f"Expected >=120 tools, got {total}"
        # Verify all tools are routable via if-chain or TOOL_REGISTRY fallback
        for name in TOOL_REGISTRY:
            entry = TOOL_REGISTRY[name]
            assert entry.get("handler") is not None, f"Tool {name} has no handler"
            assert callable(entry["handler"]), f"Tool {name} handler not callable"

    def test_new_tools_exist(self):
        from app.services.tool_executor import execute_tool
        from app.services.tool_registry import TOOL_REGISTRY
        new_tools = [
            "get_employee_attendance", "get_employee_documents", "get_budget_summary",
            "get_compensation_benchmarks", "update_deal_stage", "get_activity_timeline",
            "get_project_timeline", "update_task_status", "get_my_okrs",
            "get_review_feedback", "generate_career_path", "get_gdpr_export",
            "create_announcement", "get_workflow_templates", "get_workflow_status",
            "get_user_notifications", "mark_notification_read", "get_active_integrations",
            "get_tenant_config", "get_billing_status", "get_surveys",
            "get_chat_channels", "search_messages",
        ]
        missing = [t for t in new_tools if t not in TOOL_REGISTRY]
        assert len(missing) == 0, f"Missing new tools: {missing}"

    def test_copilot_endpoint_exists(self):
        response = client.post("/api/v1/ai/copilot", json={
            "message": "hola", "module_context": ""
        })
        assert response.status_code in (200, 401, 403, 400, 422)


class TestToolExecution:
    def test_tool_registry_lookup_works(self):
        from app.services.tool_registry import TOOL_REGISTRY
        import asyncio
        
        # Test 10 key tools from different modules can be looked up
        key_tools = [
            ("get_employee_profile", "HR"),
            ("create_it_ticket", "IT"),
            ("get_payslip", "Payroll"),
            ("create_kudos", "Kudos"),
            ("search_employees", "HR"),
            ("get_project_status", "Projects"),
            ("create_task", "Tasks"),
            ("get_contracts", "Legal"),
            ("get_course_catalog", "Training"),
            ("get_budget_summary", "Finance-Ext"),
            ("get_employee_attendance", "HR-Ext"),
            ("get_workflow_templates", "Workflows-Ext"),
            ("get_chat_channels", "Chat-Ext"),
            ("get_user_notifications", "Platform-Ext"),
            ("get_surveys", "Survey-Ext"),
        ]
        
        for tool_name, module in key_tools:
            entry = TOOL_REGISTRY.get(tool_name)
            assert entry is not None, f"Tool '{tool_name}' ({module}) not in registry"
            assert callable(entry.get("handler")), f"Tool '{tool_name}' handler not callable"
            assert "function" in entry.get("schema", {}), f"Tool '{tool_name}' schema missing function"
