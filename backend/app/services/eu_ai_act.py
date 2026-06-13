import logging
import json
import uuid
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field

logger = logging.getLogger("successcore.eu_ai_act")

AI_RISK_CATEGORIES = {
    "unacceptable": {
        "label": "Unacceptable Risk",
        "description": "Prohibited under EU AI Act Article 5",
        "examples": ["social scoring", "real-time remote biometric identification in public spaces", "manipulation exploiting vulnerabilities"],
    },
    "high": {
        "label": "High Risk",
        "description": "Requires conformity assessment, risk management, transparency, human oversight (Annex III)",
        "examples": ["employment decisions", "worker management", "access to essential services", "credit scoring", "performance evaluation"],
    },
    "limited": {
        "label": "Limited Risk",
        "description": "Requires transparency obligations (Article 50)",
        "examples": ["chatbots", "emotion recognition", "content generation"],
    },
    "minimal": {
        "label": "Minimal Risk",
        "description": "No specific obligations beyond general GDPR compliance",
        "examples": ["spam filters", "simple automation", "data formatting"],
    },
}

AGENT_RISK_CLASSIFICATION = {
    "payroll_specialist": "high",
    "recruiter": "high",
    "compliance_officer": "high",
    "performance_coach": "high",
    "finance_manager": "high",
    "hr_assistant": "limited",
    "it_helpdesk": "limited",
    "sales_coach": "limited",
    "data_analyst": "limited",
    "onboarding_buddy": "limited",
    "copilot": "limited",
    "omni_master": "high",
}

TRANSPARENCY_LOG_LIMIT = 10000


@dataclass
class AITransparencyRecord:
    id: str
    agent_id: str
    agent_type: str
    risk_category: str
    user_input: str
    ai_output: str
    tools_used: List[str]
    confidence_score: Optional[float]
    human_reviewed: bool
    timestamp: str
    run_id: str
    tenant_id: str


async def classify_agent_risk(agent_type: str) -> Dict[str, str]:
    agent_lower = agent_type.lower()
    risk = AGENT_RISK_CLASSIFICATION.get(agent_lower, "limited")
    category = AI_RISK_CATEGORIES.get(risk, AI_RISK_CATEGORIES["limited"])
    return {
        "agent_type": agent_type,
        "risk_category": risk,
        "label": category["label"],
        "description": category["description"],
    }


async def get_risk_mitigations(risk_category: str) -> List[str]:
    if risk_category == "high":
        return [
            "Human oversight: all high-risk agent outputs require human review before final action",
            "Transparency: users informed they are interacting with AI, not a human",
            "Accuracy: regular accuracy testing and bias monitoring",
            "Robustness: fallback mechanisms for degraded performance",
            "Record-keeping: all decisions logged with audit trail for 5 years",
            "Data governance: training data quality and bias assessments documented",
        ]
    elif risk_category == "limited":
        return [
            "Transparency: users informed they are interacting with AI",
            "Record-keeping: 1 year audit log retention",
        ]
    return ["No specific EU AI Act obligations beyond GDPR"]


async def log_ai_transparency(
    agent_id: str,
    agent_type: str,
    user_input: str,
    ai_output: str,
    tools_used: List[str],
    confidence_score: Optional[float],
    human_reviewed: bool,
    run_id: str,
    tenant_id: str,
):
    record = AITransparencyRecord(
        id=uuid.uuid4().hex,
        agent_id=agent_id,
        agent_type=agent_type,
        risk_category=AGENT_RISK_CLASSIFICATION.get(agent_type.lower(), "limited"),
        user_input=user_input[:2000],
        ai_output=ai_output[:5000],
        tools_used=tools_used,
        confidence_score=confidence_score,
        human_reviewed=human_reviewed,
        timestamp=datetime.now(timezone.utc).isoformat(),
        run_id=run_id,
        tenant_id=tenant_id,
    )

    try:
        from app.core.redis import get_redis
        r = await get_redis()
        if r:
            key = f"ai_transparency:{tenant_id}"
            await r.lpush(key, json.dumps({
                "id": record.id, "agent_id": record.agent_id,
                "agent_type": record.agent_type,
                "risk_category": record.risk_category,
                "user_input": record.user_input[:500],
                "ai_output": record.ai_output[:1000],
                "tools_used": record.tools_used,
                "confidence_score": record.confidence_score,
                "human_reviewed": record.human_reviewed,
                "timestamp": record.timestamp,
                "run_id": record.run_id,
            }, default=str))
            await r.ltrim(key, 0, TRANSPARENCY_LOG_LIMIT - 1)
    except Exception as e:
        logger.warning(f"Transparency log failed: {e}")

    logger.info(
        f"AI_TRANSPARENCY | agent={agent_type} | risk={record.risk_category} | "
        f"tools={len(tools_used)} | reviewed={human_reviewed} | run={run_id[:8]}"
    )


async def get_transparency_report(tenant_id: str, hours: int = 24) -> Dict[str, Any]:
    try:
        from app.core.redis import get_redis
        r = await get_redis()
        if not r:
            return {"error": "Redis unavailable"}

        key = f"ai_transparency:{tenant_id}"
        entries = await r.lrange(key, 0, 999)
        if not entries:
            return {"total_entries": 0, "entries": [], "by_risk": {}, "by_agent_type": {}}

        records = []
        cutoff = datetime.now(timezone.utc).isoformat()
        by_risk: Dict[str, int] = {}
        by_agent_type: Dict[str, int] = {}
        human_reviewed = 0
        total = 0

        for entry_str in entries:
            try:
                entry = json.loads(entry_str)
                records.append(entry)
                total += 1
                risk = entry.get("risk_category", "limited")
                by_risk[risk] = by_risk.get(risk, 0) + 1
                a_type = entry.get("agent_type", "unknown")
                by_agent_type[a_type] = by_agent_type.get(a_type, 0) + 1
                if entry.get("human_reviewed"):
                    human_reviewed += 1
            except json.JSONDecodeError:
                continue

        return {
            "total_entries": total,
            "human_reviewed_ratio": round(human_reviewed / max(total, 1), 2),
            "by_risk_category": by_risk,
            "by_agent_type": by_agent_type,
            "latest_entries": records[:10],
        }
    except Exception as e:
        return {"error": str(e)}


async def get_eu_ai_act_compliance_summary(tenant_id: str) -> Dict[str, Any]:
    risks = {}
    for agent_type, risk in AGENT_RISK_CLASSIFICATION.items():
        if risk not in risks:
            risks[risk] = {"count": 0, "agents": [], "mitigations": await get_risk_mitigations(risk)}
        risks[risk]["count"] += 1
        risks[risk]["agents"].append(agent_type)

    high_risk_count = risks.get("high", {}).get("count", 0)

    return {
        "framework": "EU AI Act 2024/1689",
        "compliance_level": "partial",
        "total_agent_types": len(AGENT_RISK_CLASSIFICATION),
        "high_risk_count": high_risk_count,
        "high_risk_requires_audit": high_risk_count > 0,
        "risk_classifications": risks,
        "required_actions": [
            "Implement mandatory human oversight for high-risk agents",
            "Conduct bias audit on recruitment and performance evaluation agents",
            "Document training data provenance for high-risk models",
            "Establish AI incident response plan",
            "Register high-risk AI systems in EU database",
            "Conduct conformity assessment for Annex III systems",
        ],
        "next_review_date": "2026-08-02",
    }
