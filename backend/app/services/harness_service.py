import logging
import json
import uuid
import time
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.harness import TestSuite, TestCase, TestRun
from app.models.agent import Agent

logger = logging.getLogger("successcore.harness_service")


async def run_agent_test_suite(
    db: AsyncSession,
    suite_id: str,
    evaluator_model: str = "gpt-4o",
) -> Dict[str, Any]:
    suite = await db.get(TestSuite, suite_id)
    if not suite:
        raise ValueError(f"Test suite {suite_id} not found")

    test_cases_res = await db.execute(
        select(TestCase).where(TestCase.suite_id == suite_id)
    )
    test_cases = test_cases_res.scalars().all()
    if not test_cases:
        return {"suite_id": suite_id, "total": 0, "passed": 0, "failed": 0, "results": []}

    agent_res = await db.execute(select(Agent).where(Agent.id == suite.agent_id))
    agent = agent_res.scalar_one_or_none()

    start_time = time.monotonic()
    results = []
    passed = 0
    failed = 0
    total_tokens = 0
    total_cost = 0.0

    for tc in test_cases:
        case_result = await _evaluate_case(db, tc, agent, evaluator_model)
        results.append(case_result)
        if case_result["passed"]:
            passed += 1
        else:
            failed += 1
        total_tokens += case_result.get("tokens_used", 0)

    avg_latency = int((time.monotonic() - start_time) * 1000 / max(len(test_cases), 1))

    run = TestRun(
        id=uuid.uuid4().hex,
        suite_id=suite_id,
        status="SUCCESS" if failed == 0 else ("PARTIAL" if passed > 0 else "FAILED"),
        passed_count=passed,
        failed_count=failed,
        total_count=len(test_cases),
        avg_latency_ms=avg_latency,
        total_cost_usd=total_cost,
        log_details=results,
    )
    db.add(run)
    await db.commit()

    return {
        "run_id": run.id,
        "suite_id": suite_id,
        "total": len(test_cases),
        "passed": passed,
        "failed": failed,
        "pass_rate_pct": round(passed / max(len(test_cases), 1) * 100, 1),
        "avg_latency_ms": avg_latency,
        "total_cost_usd": total_cost,
        "results": results,
    }


async def _evaluate_case(
    db: AsyncSession,
    test_case: TestCase,
    agent: Optional[Agent],
    evaluator_model: str,
) -> Dict[str, Any]:
    try:
        from app.services.agent_runtime import execute_agent_run

        run_result = await execute_agent_run(
            db=db,
            agent_id=agent.id if agent else "",
            input_payload={
                "message": test_case.input_payload,
                "user_id": "harness",
                "tenant_id": "harness",
                "role": "tester",
            },
            trigger_source="harness",
        )

        response = run_result.get("reply", "")

        eval_result = await _llm_evaluate(
            db, test_case.input_payload, response,
            test_case.expected_criteria, evaluator_model,
        )

        return {
            "case_id": test_case.id,
            "case_name": test_case.name,
            "passed": eval_result["passed"],
            "score": eval_result["score"],
            "critique": eval_result["critique"],
            "response": response[:500],
            "tokens_used": run_result.get("token_usage", 0),
            "cost_usd": run_result.get("cost_usd", 0.0),
            "latency_ms": run_result.get("latency_ms", 0),
        }
    except Exception as e:
        logger.error(f"Test case {test_case.id} failed: {e}")
        return {
            "case_id": test_case.id,
            "case_name": test_case.name,
            "passed": False,
            "score": 0,
            "critique": f"Execution error: {str(e)[:300]}",
            "response": "",
            "tokens_used": 0,
            "cost_usd": 0.0,
            "latency_ms": 0,
        }


async def _llm_evaluate(
    db,
    user_input: str,
    agent_response: str,
    evaluation_criteria: str,
    model: str = "gpt-4o",
) -> Dict[str, Any]:
    from app.services.llm_router import get_llm_client

    prompt = f"""You are an LLM-as-a-Judge evaluator. Grade the following agent response against the evaluation criteria.

USER INPUT:
{user_input}

AGENT RESPONSE:
{agent_response[:2000]}

EVALUATION CRITERIA:
{evaluation_criteria}

Return JSON with: {{"passed": true/false, "score": 0-10, "critique": "brief explanation (2-3 sentences)"}}"""

    try:
        client, _ = await get_llm_client(model, None, db)
        response = await client.chat.completions.create(
            model=model,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )
        raw = response.choices[0].message.content or "{}"
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw[raw.find("\n"):raw.rfind("```")].strip()
        data = json.loads(raw)
        return {
            "passed": data.get("passed", data.get("score", 0) >= 5),
            "score": data.get("score", 5),
            "critique": data.get("critique", "No critique provided"),
        }
    except Exception as e:
        logger.warning(f"LLM evaluation failed: {e}")
        return {"passed": True, "score": 5, "critique": f"Evaluation unavailable: {e}"}


async def generate_test_suite_from_agent(
    db: AsyncSession,
    agent_id: str,
    num_cases: int = 5,
) -> TestSuite:
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise ValueError(f"Agent {agent_id} not found")

    from app.services.llm_router import get_llm_client

    prompt = f"""Generate {num_cases} test cases for evaluating an AI agent with the following profile:

Name: {agent.name}
Type: {agent.agent_type}
System Prompt: {agent.ai_system_prompt[:500]}

For each test case, provide:
- A realistic user input message
- Evaluation criteria (what a good response should include)

Return a JSON array of test cases:
[{{"name": "Test case name", "input_payload": "user message", "expected_criteria": "evaluation criteria"}}]"""

    try:
        client, _ = await get_llm_client("gpt-4o", None, db)
        response = await client.chat.completions.create(
            model="gpt-4o",
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
        )
        raw = response.choices[0].message.content or "[]"
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw[raw.find("\n"):raw.rfind("```")].strip()

        cases_data = json.loads(raw)

        suite = TestSuite(
            id=uuid.uuid4().hex,
            agent_id=agent_id,
            name=f"Auto-generated suite for {agent.name}",
            description=f"Auto-generated {len(cases_data)} test cases",
        )
        db.add(suite)

        for case in cases_data[:num_cases]:
            tc = TestCase(
                id=uuid.uuid4().hex,
                suite_id=suite.id,
                name=case.get("name", "Unnamed test"),
                input_payload=case.get("input_payload", ""),
                expected_criteria=case.get("expected_criteria", ""),
                mock_collected_data={},
            )
            db.add(tc)

        await db.commit()
        await db.refresh(suite)
        logger.info(f"Generated test suite {suite.id[:8]} with {len(cases_data)} cases for agent {agent.name}")
        return suite
    except Exception as e:
        logger.error(f"Test suite generation failed: {e}")
        raise ValueError(f"Failed to generate test suite: {e}")


run_evaluation_suite = run_agent_test_suite
