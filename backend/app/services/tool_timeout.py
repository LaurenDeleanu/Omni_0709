import asyncio
import logging
import time
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("successcore.tool_timeout")

DEFAULT_TOOL_TIMEOUT_SECONDS = 15.0
TOOL_TIMEOUTS: Dict[str, float] = {
    "process_payroll": 60.0,
    "create_payroll_cycle": 30.0,
    "get_financial_ledger": 20.0,
    "get_org_chart": 10.0,
    "generate_compliance_report": 60.0,
    "run_compliance_audit": 60.0,
    "negotiate_with_agents": 120.0,
    "search_it_knowledge_base": 10.0,
    "get_pipeline_stats": 15.0,
    "get_department_stats": 15.0,
    "screen_candidate": 30.0,
    "screen_resume": 30.0,
    "rank_candidates": 30.0,
}


def get_tool_timeout(tool_name: str) -> float:
    return TOOL_TIMEOUTS.get(tool_name, DEFAULT_TOOL_TIMEOUT_SECONDS)


async def execute_with_timeout(
    db: AsyncSession,
    tool_name: str,
    tool_args: dict,
    handler_func,
    user_payload: dict = None,
    agent_id: str = "",
    run_id: str = "",
) -> str:
    timeout = get_tool_timeout(tool_name)
    start_time = time.monotonic()

    try:
        result = await asyncio.wait_for(
            handler_func(db=db, arguments=tool_args, user_payload=user_payload, agent_id=agent_id, run_id=run_id),
            timeout=timeout,
        )
        elapsed = time.monotonic() - start_time
        if elapsed > timeout * 0.75:
            logger.warning(f"Tool '{tool_name}' completed in {elapsed:.1f}s (75%+ of {timeout}s timeout)")
        return result
    except asyncio.TimeoutError:
        elapsed = time.monotonic() - start_time
        logger.error(f"Tool '{tool_name}' timed out after {elapsed:.1f}s (limit: {timeout}s)")
        return json.dumps({
            "error": "tool_timeout",
            "message": f"Tool '{tool_name}' exceeded the {timeout}s timeout limit",
            "timeout_seconds": timeout,
        })
    except Exception as e:
        elapsed = time.monotonic() - start_time
        logger.error(f"Tool '{tool_name}' failed after {elapsed:.1f}s: {e}")
        raise


import json
