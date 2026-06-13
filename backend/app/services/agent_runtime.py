# SuccessCore SAS — Agent Runtime Facade
# This file exposes the unified API for agent execution.
# Original implementation was refactored into:
# - agent_executor.py: core synchronous loops and cascade resolution
# - agent_context_builder.py: assembly of system prompt, memory, and RAG contexts
# - agent_cost_tracker.py: token calculations and reseller billing/budget hooks
# - agent_streaming.py: SSE streaming execution loop

from app.services.agent_executor import execute_agent_run, _surface_tool_errors
from app.services.agent_streaming import execute_agent_run_streaming
from app.services.agent_cost_tracker import calculate_token_cost
from app.services.agent_context_builder import build_agent_context
from app.services.runtime_monitor import executor_stats, heartbeat_tracker, get_executor_health, record_execution
from app.services.runtime_monitor import start_heartbeat_monitor, get_task_supervisor

__all__ = [
    "execute_agent_run",
    "execute_agent_run_streaming",
    "calculate_token_cost",
    "build_agent_context",
    "_surface_tool_errors",
    "executor_stats",
    "heartbeat_tracker",
    "get_executor_health",
    "record_execution",
    "start_heartbeat_monitor",
    "get_task_supervisor",
]
