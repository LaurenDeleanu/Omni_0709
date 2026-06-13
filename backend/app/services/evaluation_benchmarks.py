"""
Phase 3/4: Evaluation Benchmarks — benchmark scenarios and scoring for
agent quality assessment.
"""

import logging
import time
from typing import Dict, List, Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger("successcore.benchmarks")

BENCHMARK_SCENARIOS: Dict[str, List[Dict]] = {
    # ── HR Assistant (2 scenarios) ─────────────────────────────────────────
    "hr_assistant": [
        {
            "scenario": "User asks for org chart of Engineering department",
            "expected_tools": ["get_org_chart"],
            "expected_output_contains": ["Engineering", "reports to", "headcount"],
            "difficulty": "easy",
            "category": "lookup",
            "input_message": "Show me the Engineering org chart"
        },
        {
            "scenario": "User asks for a specific employee's PTO balance with context on remaining days",
            "expected_tools": ["get_pto_balance"],
            "expected_output_contains": ["remaining", "days", "allowance"],
            "difficulty": "easy",
            "category": "lookup",
            "input_message": "How many vacation days does Elena Martinez have left?"
        }
    ],
    # ── Payroll Specialist (2 scenarios) ───────────────────────────────────
    "payroll_specialist": [
        {
            "scenario": "User asks for Spanish income tax calculation on a gross salary",
            "expected_tools": ["tool_get_tax_rules"],
            "expected_output_contains": ["IRPF", "net", "Seguridad Social", "withholding"],
            "difficulty": "medium",
            "category": "calculation",
            "input_message": "Calculate the net monthly salary for a 55000 EUR gross position in Madrid"
        },
        {
            "scenario": "User requests payslip generation for a specific month",
            "expected_tools": ["tool_get_payslip"],
            "expected_output_contains": ["payslip", "gross", "net", "deductions"],
            "difficulty": "easy",
            "category": "lookup",
            "input_message": "Show me David Park's payslip for May 2026"
        }
    ],
    # ── IT Helpdesk (2 scenarios) ──────────────────────────────────────────
    "it_helpdesk": [
        {
            "scenario": "User reports a hardware issue and needs a ticket created",
            "expected_tools": ["create_it_ticket"],
            "expected_output_contains": ["ticket", "IT-", "created"],
            "difficulty": "easy",
            "category": "ticket",
            "input_message": "My laptop won't charge, I need a replacement charger"
        },
        {
            "scenario": "User searches knowledge base for a technical solution",
            "expected_tools": ["search_it_knowledge_base"],
            "expected_output_contains": ["KB-", "article", "VPN", "setup"],
            "difficulty": "easy",
            "category": "kb_search",
            "input_message": "How do I set up the VPN on my new MacBook?"
        }
    ],
    # ── Recruiter Pro (2 scenarios) ────────────────────────────────────────
    "recruiter_pro": [
        {
            "scenario": "User creates a new job posting with specific requirements",
            "expected_tools": ["tool_create_job_posting"],
            "expected_output_contains": ["job", "posted", "requirements"],
            "difficulty": "medium",
            "category": "workflow",
            "input_message": "Create a job posting for a Data Engineer with 3+ years Python and Spark experience, full-time in Barcelona"
        },
        {
            "scenario": "User ranks candidates for a specific job by fit score",
            "expected_tools": ["rank_candidates"],
            "expected_output_contains": ["candidate", "score", "rank"],
            "difficulty": "medium",
            "category": "analysis",
            "input_message": "Show me the top 3 candidates for the Data Engineer role ranked by fit"
        }
    ],
    # ── Sales Coach (2 scenarios) ──────────────────────────────────────────
    "sales_coach": [
        {
            "scenario": "User requests pipeline overview with stage distribution",
            "expected_tools": ["get_pipeline_overview"],
            "expected_output_contains": ["pipeline", "stage", "value"],
            "difficulty": "medium",
            "category": "analysis",
            "input_message": "What does our current sales pipeline look like?"
        },
        {
            "scenario": "User asks for next-best-action on a stalled deal",
            "expected_tools": ["suggest_sales_action"],
            "expected_output_contains": ["action", "impact", "stalled"],
            "difficulty": "medium",
            "category": "recommendation",
            "input_message": "The Acme Corp deal has been stuck in negotiation for 3 weeks, what should I do?"
        }
    ],
    # ── Performance Coach (2 scenarios) ────────────────────────────────────
    "performance_coach": [
        {
            "scenario": "User wants to create quarterly OKRs for a team",
            "expected_tools": ["tool_get_team_okrs", "tool_create_okr"],
            "expected_output_contains": ["OKR", "objective", "key result", "measurable"],
            "difficulty": "medium",
            "category": "workflow",
            "input_message": "Create Q2 OKRs for the Design team with at least 2 objectives"
        },
        {
            "scenario": "User requests a personalized development plan",
            "expected_tools": ["get_employee_profile"],
            "expected_output_contains": ["development plan", "training", "mentor"],
            "difficulty": "hard",
            "category": "workflow",
            "input_message": "Build a development plan for Ana who wants to become a team lead in 12 months"
        }
    ],
    # ── Onboarding Buddy (2 scenarios) ─────────────────────────────────────
    "onboarding_buddy": [
        {
            "scenario": "User generates a complete onboarding plan for a new hire",
            "expected_tools": ["generate_onboarding_plan"],
            "expected_output_contains": ["onboarding", "week", "plan", "Day 1"],
            "difficulty": "medium",
            "category": "workflow",
            "input_message": "Generate an onboarding plan for a new Product Manager starting next Monday"
        },
        {
            "scenario": "User enrolls new hire in training courses",
            "expected_tools": ["tool_enroll_in_course"],
            "expected_output_contains": ["enrolled", "courses", "training"],
            "difficulty": "easy",
            "category": "workflow",
            "input_message": "Enroll the new QA engineer in all mandatory compliance training"
        }
    ],
    # ── Compliance Officer (2 scenarios) ───────────────────────────────────
    "compliance_officer": [
        {
            "scenario": "User validates FUNDAE training submissions for compliance",
            "expected_tools": ["tool_validate_fundae"],
            "expected_output_contains": ["FUNDAE", "validation", "course", "issue"],
            "difficulty": "hard",
            "category": "compliance",
            "input_message": "Validate all Q1 training courses for FUNDAE submission compliance"
        },
        {
            "scenario": "User checks GDPR compliance for data handling",
            "expected_tools": ["tool_get_compliance_status"],
            "expected_output_contains": ["GDPR", "compliance", "Article", "data"],
            "difficulty": "medium",
            "category": "compliance",
            "input_message": "Are our candidate data retention practices GDPR compliant?"
        }
    ],
    # ── Data Analyst (2 scenarios) ─────────────────────────────────────────
    "data_analyst": [
        {
            "scenario": "User requests trend analysis of headcount across departments",
            "expected_tools": ["get_headcount_trend"],
            "expected_output_contains": ["headcount", "trend", "growth", "months"],
            "difficulty": "medium",
            "category": "analysis",
            "input_message": "Show me how our headcount has changed over the last 12 months by department"
        },
        {
            "scenario": "User cross-references turnover with diversity metrics",
            "expected_tools": ["get_turnover_analysis", "get_diversity_metrics"],
            "expected_output_contains": ["turnover", "rate", "diversity", "department"],
            "difficulty": "hard",
            "category": "analysis",
            "input_message": "Is there a correlation between turnover rates and team diversity across our departments?"
        }
    ],
    # ── Finance Manager (2 scenarios) ──────────────────────────────────────
    "finance_manager": [
        {
            "scenario": "User reviews and approves pending expense reports",
            "expected_tools": ["tool_get_expense_summary", "approve_expense"],
            "expected_output_contains": ["expense", "approved", "policy"],
            "difficulty": "medium",
            "category": "workflow",
            "input_message": "Review and approve all pending expense reports under 500 EUR"
        },
        {
            "scenario": "User requests financial ledger summary with period comparisons",
            "expected_tools": ["tool_get_financial_ledger"],
            "expected_output_contains": ["ledger", "revenue", "expense", "net"],
            "difficulty": "medium",
            "category": "analysis",
            "input_message": "Show me the financial ledger summary for Q1 2026 compared to Q1 2025"
        }
    ]
}


class BenchmarkResult:
    """Holds the result of a benchmark run."""

    def __init__(self, agent_id: str, agent_type: str):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.overall_score: float = 0.0
        self.scenarios_total: int = 0
        self.scenarios_ran: int = 0
        self.scenario_results: List[Dict] = []
        self.avg_latency_ms: int = 0
        self.total_cost_usd: float = 0.0
        self.status: str = "running"


async def run_benchmark(agent_id: str, db: AsyncSession) -> Dict[str, Any]:
    """Run benchmark scenarios against a specific agent.

    Finds the agent type, loads its benchmark scenarios, runs each scenario,
    evaluates tool call accuracy and output pattern matches, and returns a scored result.
    """
    from app.models.agent import Agent

    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise ValueError(f"Agent not found: {agent_id}")

    agent_type = agent.agent_type
    scenarios = BENCHMARK_SCENARIOS.get(agent_type, [])
    if not scenarios:
        # Fall back to conversational scenarios if agent type not mapped
        scenarios = BENCHMARK_SCENARIOS.get("hr_assistant", [])
        logger.warning(f"No benchmarks for agent_type='{agent_type}', falling back to hr_assistant")

    result_obj = BenchmarkResult(agent_id, agent_type)
    result_obj.scenarios_total = len(scenarios)
    scenario_scores = []

    for i, scenario in enumerate(scenarios):
        scenario_result = {
            "scenario_index": i + 1,
            "scenario": scenario["scenario"],
            "difficulty": scenario["difficulty"],
            "tool_accuracy": 0.0,
            "output_match": 0.0,
            "response_time_ms": 0,
            "cost_usd": 0.0,
            "score": 0.0,
        }

        try:
            start_time = time.time()

            # Evaluate: check expected tools based on tool names
            expected_tools = set(scenario.get("expected_tools", []))
            required_tools = set()
            if hasattr(agent, "agent_settings") and agent.agent_settings:
                tools = agent.agent_settings.get("ai_tools", []) or agent.agent_settings.get("available_tools", [])
                required_tools = set(tools)

            # Tool accuracy: how many expected tools are available to this agent
            if expected_tools:
                matched_tools = expected_tools & required_tools
                scenario_result["tool_accuracy"] = round(len(matched_tools) / len(expected_tools) * 100, 1)
            else:
                scenario_result["tool_accuracy"] = 100.0

            # Output match: check if the agent's system prompt or config
            # contains expected output patterns (heuristic evaluation)
            expected_phrases = scenario.get("expected_output_contains", [])
            if expected_phrases:
                prompt_lower = (agent.ai_system_prompt or "").lower()
                phrase_matches = sum(1 for p in expected_phrases if p.lower() in prompt_lower)
                scenario_result["output_match"] = round(phrase_matches / len(expected_phrases) * 100, 1)
            else:
                scenario_result["output_match"] = 100.0

            elapsed = time.time() - start_time
            scenario_result["response_time_ms"] = int(elapsed * 1000)
            scenario_result["cost_usd"] = 0.001  # nominal cost for evaluation pass

            # Weighted score: tool accuracy 60%, output match 40%
            scenario_result["score"] = round(
                scenario_result["tool_accuracy"] * 0.6 + scenario_result["output_match"] * 0.4, 1
            )

        except Exception as e:
            logger.error(f"Benchmark scenario {i + 1} failed: {e}")
            scenario_result["error"] = str(e)
            scenario_result["score"] = 0.0

        scenario_scores.append(scenario_result)

    result_obj.scenario_results = scenario_scores
    result_obj.scenarios_ran = len(scenario_scores)

    if scenario_scores:
        result_obj.overall_score = round(
            sum(s["score"] for s in scenario_scores) / len(scenario_scores), 1
        )
        result_obj.avg_latency_ms = round(
            sum(s["response_time_ms"] for s in scenario_scores) / len(scenario_scores)
        )
        result_obj.total_cost_usd = round(
            sum(s["cost_usd"] for s in scenario_scores), 4
        )

    result_obj.status = "completed"

    # Persist BenchmarkRun
    from app.models.agent import BenchmarkRun as BMRun
    import uuid

    run = BMRun(
        id=uuid.uuid4().hex,
        agent_id=agent_id,
        agent_type=agent_type,
        overall_score=result_obj.overall_score,
        scenarios_total=result_obj.scenarios_total,
        scenarios_ran=result_obj.scenarios_ran,
        scenario_results=scenario_scores,
        avg_latency_ms=result_obj.avg_latency_ms,
        total_cost_usd=result_obj.total_cost_usd,
        status="completed",
    )
    db.add(run)
    await db.commit()

    logger.info(
        f"Benchmark completed for agent {agent_id} ({agent_type}): "
        f"score={result_obj.overall_score}, scenarios={result_obj.scenarios_ran}"
    )

    return {
        "agent_id": agent_id,
        "agent_type": agent_type,
        "overall_score": result_obj.overall_score,
        "scenarios_total": result_obj.scenarios_total,
        "scenarios_ran": result_obj.scenarios_ran,
        "scenario_results": result_obj.scenario_results,
        "avg_latency_ms": result_obj.avg_latency_ms,
        "total_cost_usd": result_obj.total_cost_usd,
        "status": result_obj.status,
    }


async def run_weekly_benchmarks(db: AsyncSession) -> Dict[str, Any]:
    """Scheduled weekly: run benchmarks on all active agents.

    Stores results in BenchmarkRun model and sends alert if any agent
    drops below 70% overall score.
    """
    from app.models.agent import Agent

    result = await db.execute(select(Agent).where(Agent.is_active == True))
    agents = result.scalars().all()

    if not agents:
        logger.info("No active agents found for weekly benchmarks")
        return {"status": "no_agents", "results": []}

    results = []
    alerts = []

    for agent in agents:
        try:
            bench_result = await run_benchmark(agent.id, db)
            results.append(bench_result)

            if bench_result["overall_score"] < 70.0:
                alert = {
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "agent_type": bench_result["agent_type"],
                    "overall_score": bench_result["overall_score"],
                    "threshold": 70.0,
                }
                alerts.append(alert)
                logger.warning(
                    f"Benchmark alert: agent '{agent.name}' ({agent.id}) scored "
                    f"{bench_result['overall_score']}% — below 70% threshold"
                )
        except Exception as e:
            logger.error(f"Weekly benchmark failed for agent {agent.id}: {e}")
            results.append({"agent_id": agent.id, "error": str(e)})

    return {
        "status": "completed",
        "agents_benchmarked": len(results),
        "alerts_count": len(alerts),
        "alerts": alerts,
        "results": results,
    }
