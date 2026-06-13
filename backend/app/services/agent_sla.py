import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("successcore.agent_sla")


@dataclass
class SLABreach:
    agent_id: str
    agent_name: str
    metric: str
    threshold: float
    actual: float
    timestamp: float


DEFAULT_SLA_THRESHOLDS = {
    "max_latency_ms": 5000,
    "min_success_rate_pct": 85.0,
    "max_cost_per_run_usd": 0.05,
    "max_consecutive_failures": 5,
}

AGENT_TYPE_SLA = {
    "hr_assistant": {"max_latency_ms": 3000, "min_success_rate_pct": 90.0},
    "payroll_specialist": {"max_latency_ms": 10000, "min_success_rate_pct": 95.0, "max_cost_per_run_usd": 0.10},
    "it_helpdesk": {"max_latency_ms": 5000, "min_success_rate_pct": 90.0},
    "recruiter": {"max_latency_ms": 8000, "min_success_rate_pct": 85.0, "max_cost_per_run_usd": 0.08},
    "sales_coach": {"max_latency_ms": 5000, "min_success_rate_pct": 85.0},
    "performance_coach": {"max_latency_ms": 5000, "min_success_rate_pct": 90.0},
    "compliance_officer": {"max_latency_ms": 10000, "min_success_rate_pct": 95.0},
    "data_analyst": {"max_latency_ms": 8000, "min_success_rate_pct": 85.0, "max_cost_per_run_usd": 0.06},
    "finance_manager": {"max_latency_ms": 5000, "min_success_rate_pct": 90.0, "max_cost_per_run_usd": 0.08},
}


def get_sla_thresholds(agent_type: str) -> Dict[str, Any]:
    base = dict(DEFAULT_SLA_THRESHOLDS)
    base.update(AGENT_TYPE_SLA.get(agent_type, {}))
    return base


def check_sla_compliance(
    agent_id: str,
    agent_name: str,
    agent_type: str,
    metrics: Dict[str, Any],
) -> List[SLABreach]:
    thresholds = get_sla_thresholds(agent_type)
    breaches = []

    avg_lat = metrics.get("avg_latency_ms", 0)
    if avg_lat > thresholds["max_latency_ms"]:
        breaches.append(SLABreach(
            agent_id=agent_id, agent_name=agent_name,
            metric="max_latency_ms",
            threshold=thresholds["max_latency_ms"],
            actual=avg_lat,
            timestamp=time.time(),
        ))

    success_rate = metrics.get("success_rate_pct", 100)
    if success_rate < thresholds["min_success_rate_pct"]:
        breaches.append(SLABreach(
            agent_id=agent_id, agent_name=agent_name,
            metric="min_success_rate_pct",
            threshold=thresholds["min_success_rate_pct"],
            actual=success_rate,
            timestamp=time.time(),
        ))

    cost_per_run = metrics.get("total_cost_usd", 0) / max(metrics.get("total_runs", 1), 1)
    max_cost = thresholds.get("max_cost_per_run_usd", 0.05)
    if cost_per_run > max_cost:
        breaches.append(SLABreach(
            agent_id=agent_id, agent_name=agent_name,
            metric="max_cost_per_run_usd",
            threshold=max_cost,
            actual=cost_per_run,
            timestamp=time.time(),
        ))

    if breaches:
        logger.warning(
            f"SLA BREACH: agent={agent_name} type={agent_type} breaches={len(breaches)} "
            + ", ".join(f"{b.metric}={b.actual:.1f} (limit={b.threshold:.1f})" for b in breaches)
        )

    return breaches


def get_sla_status(
    agent_id: str,
    agent_name: str,
    agent_type: str,
    metrics: Dict[str, Any],
) -> Dict[str, Any]:
    thresholds = get_sla_thresholds(agent_type)
    breaches = check_sla_compliance(agent_id, agent_name, agent_type, metrics)
    return {
        "agent_id": agent_id,
        "agent_name": agent_name,
        "agent_type": agent_type,
        "sla_compliant": len(breaches) == 0,
        "breach_count": len(breaches),
        "thresholds": thresholds,
        "breaches": [
            {
                "metric": b.metric,
                "threshold": b.threshold,
                "actual": b.actual,
            }
            for b in breaches
        ],
    }
