import logging
from typing import Dict, List
from collections import defaultdict

logger = logging.getLogger("successcore.dept_usage")

_dept_api_calls: Dict[str, int] = defaultdict(int)
_dept_agent_runs: Dict[str, int] = defaultdict(int)


def record_api_call_by_dept(dept: str):
    _dept_api_calls[dept or "Unknown"] += 1


def record_agent_run_by_dept(dept: str):
    _dept_agent_runs[dept or "Unknown"] += 1


def get_dept_usage_stats() -> dict:
    total_api = sum(_dept_api_calls.values())
    total_agent = sum(_dept_agent_runs.values())

    departments = []
    all_depts = set(_dept_api_calls.keys()) | set(_dept_agent_runs.keys())
    for dept in sorted(all_depts):
        api_calls = _dept_api_calls.get(dept, 0)
        agent_runs = _dept_agent_runs.get(dept, 0)
        departments.append({
            "department": dept,
            "api_calls": api_calls,
            "api_pct": round(api_calls / max(total_api, 1) * 100, 1),
            "agent_runs": agent_runs,
            "agent_pct": round(agent_runs / max(total_agent, 1) * 100, 1),
        })

    departments.sort(key=lambda d: d["api_calls"], reverse=True)
    return {"departments": departments, "total_api_calls": total_api, "total_agent_runs": total_agent}
