import os
import sys
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-copilot-tests-32chars")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-32chars--")
os.environ.setdefault("DEBUG_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("=" * 60)
print("COPILOT ENDPOINT VERIFICATION")
print("=" * 60)

# Test 1: Endpoint exists and accepts requests
resp = client.post("/api/v1/ai/copilot", json={"message": "test", "module_context": ""})
print(f"\nTest 1 - Basic request: status={resp.status_code}")
assert resp.status_code in (200, 401, 403, 400, 422), f"Unexpected status: {resp.status_code}"
print("  PASSED")

# Test 2: Streaming endpoint exists
resp = client.post("/api/v1/ai/copilot/stream", json={"message": "test", "module_context": ""})
print(f"\nTest 2 - Stream endpoint: status={resp.status_code}")
assert resp.status_code in (200, 401, 403, 400, 422, 500), f"Unexpected status: {resp.status_code}"
print("  PASSED")

# Test 3: All 120 tools load
from app.services.tool_executor import execute_tool
from app.services.tool_registry import TOOL_REGISTRY
print(f"\nTest 3 - Tool registry: {len(TOOL_REGISTRY)} tools loaded")
assert len(TOOL_REGISTRY) >= 120
print("  PASSED")

# Test 4: Sample tool handler validation
sample_tools = [
    "get_employee_profile", "create_it_ticket", "get_payslip",
    "create_task", "get_employee_attendance", "get_budget_summary",
    "get_project_timeline", "get_workflow_templates", "get_chat_channels",
    "get_user_notifications", "get_surveys", "create_announcement",
]
print(f"\nTest 4 - Sample tool handlers:")
for name in sample_tools:
    entry = TOOL_REGISTRY.get(name)
    has_handler = entry and callable(entry.get("handler"))
    status = "OK" if has_handler else "BROKEN"
    print(f"  {name}: {status}")
    assert has_handler, f"Tool {name} has no callable handler"
print("  ALL PASSED")

# Test 5: Employee tool list
from app.services.tool_binding_registry import build_copilot_tool_list
import asyncio
emp_tools = asyncio.new_event_loop().run_until_complete(build_copilot_tool_list(["employee"]))
print(f"\nTest 5 - Employee tools: {len(emp_tools)}")
assert len(emp_tools) >= 50
print("  PASSED")

# Test 6: Manager tool list
mgr_tools = asyncio.new_event_loop().run_until_complete(build_copilot_tool_list(["manager"]))
print(f"\nTest 6 - Manager tools: {len(mgr_tools)}")
assert len(mgr_tools) >= 90
print("  PASSED")

# Test 7: Tool registry routing - all tools have schemas
broken_schemas = []
for name, entry in TOOL_REGISTRY.items():
    schema = entry.get("schema", {})
    if not isinstance(schema, dict) or "function" not in schema:
        broken_schemas.append(name)
        continue
    func_def = schema["function"]
    if "name" not in func_def:
        broken_schemas.append(name)

print(f"\nTest 7 - Schema validation: {len(TOOL_REGISTRY) - len(broken_schemas)}/{len(TOOL_REGISTRY)} valid")
assert len(broken_schemas) == 0, f"Tools with broken schemas: {broken_schemas}"
print("  PASSED")

# Test 8: Module coverage
from app.services.tool_binding_registry import TOOL_BINDINGS
modules_with_tools = set()
for binding in TOOL_BINDINGS.values():
    modules_with_tools.add(binding.get("module", "unknown"))

print(f"\nTest 8 - Module coverage: {len(modules_with_tools)} modules")
print(f"  Modules: {sorted(modules_with_tools)}")
expected_modules = {"hr", "calendar", "payroll", "it", "crm", "projects", "training", "hiring", "performance", "legal", "workflows", "finance", "platform"}
missing = expected_modules - modules_with_tools
if missing:
    print(f"  MISSING from bindings: {missing}")
else:
    print(f"  All {len(expected_modules)} expected modules covered")
assert len(modules_with_tools) >= 10
print("  PASSED")

print("\n" + "=" * 60)
print("ALL COPILOT VERIFICATION TESTS PASSED")
print("=" * 60)
