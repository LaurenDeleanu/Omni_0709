import time
import json
import logging
import asyncio
import uuid
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent import Agent, AgentConfig, AgentExecutionRun
from app.services.llm_router import get_llm_client, current_run_id
from app.services.model_fallback import (
    build_full_cascade,
    resolve_provider_client,
    get_provider_health,
)
from app.services.tool_executor import execute_tool
from app.services.pii_sanitizer import sanitize_output
from app.services.moderation_service import moderate_content
from app.services.hallucination_detector import detect_hallucination
from app.services.usage_quotas import record_agent_run
from app.services.ab_deployment import ABDeployment
from app.services.agent_memory import save_conversation_turn
from app.core.retry import async_retry

# Modular helpers
from app.services.agent_context_builder import build_agent_context
from app.services.agent_cost_tracker import calculate_token_cost, apply_reseller_billing, record_budget_consumption

logger = logging.getLogger("successcore.agent_executor")

def _surface_tool_errors(tool_name: str, tool_result: str) -> str:
    if not tool_result:
        return tool_result
    try:
        parsed = json.loads(tool_result)
        if isinstance(parsed, dict) and "error" in parsed:
            error_msg = parsed["error"]
            detail = parsed.get("detail", "")
            validation_errors = parsed.get("validation_errors", [])
            parts = [f"Tool '{tool_name}' returned an error: {error_msg}"]
            if detail:
                parts.append(f"Detail: {detail}")
            if validation_errors:
                parts.append(f"Validation issues: {'; '.join(str(v) for v in validation_errors)}")
            return " | ".join(parts)
    except (json.JSONDecodeError, TypeError):
        pass
    return tool_result


async def _apply_phase5_postprocessing(
    final_text: str,
    user_msg: str,
    agent,
    active_tools: list,
    trace_steps: list,
) -> str:
    agent_settings = agent.agent_settings or {}

    tools_used_names = []
    if active_tools:
        for t in active_tools:
            name = t.get("function", {}).get("name", "")
            if name:
                tools_used_names.append(name)

    # Self-Critique
    if agent_settings.get("use_self_critique", False):
        from app.services.self_critique import run_self_critique_cycle
        try:
            agent_ctx = agent.ai_system_prompt or ""
            critique_data = await run_self_critique_cycle(
                response=final_text,
                original_query=user_msg,
                tools_used=tools_used_names,
                agent_context=agent_ctx,
            )
            final_text = critique_data["final_response"]
            trace_steps.append({
                "step": "self_critique",
                "iterations": critique_data["iterations"],
                "best_score": critique_data["best_score"],
            })
        except Exception as e:
            logger.warning(f"Self-critique failed (non-fatal): {e}")

    # Confidence Scoring
    from app.services.confidence_scorer import score_response_confidence, append_confidence_metadata
    try:
        confidence_result = await score_response_confidence(
            response=final_text,
            tools_used=tools_used_names,
            query_complexity="medium",
        )
        if agent_settings.get("show_confidence", True):
            final_text = await append_confidence_metadata(final_text, confidence_result)
        trace_steps.append({
            "step": "confidence_scoring",
            "score": confidence_result.get("confidence_score", 0),
            "flags": len(confidence_result.get("uncertainty_flags", [])),
        })
    except Exception as e:
        logger.warning(f"Confidence scoring failed (non-fatal): {e}")

    # Explanation Chain
    explanation_style = agent_settings.get("explanation_style", "none")
    if explanation_style == "chain":
        from app.services.explanation_chains import generate_explanation_chain
        try:
            evidence_list = []
            reasoning_list = []
            for ts in trace_steps:
                step_name = ts.get("step", "")
                if "tool" in step_name:
                    evidence_list.append(f"Tool call: {step_name}")
                    reasoning_list.append(f"Retrieved data via {step_name}")
                elif "rag" in step_name:
                    evidence_list.append("Knowledge base retrieval")
                    reasoning_list.append("Relevant documents were consulted")
            if not evidence_list:
                evidence_list = ["Agent reasoning based on internal knowledge"]
                reasoning_list = ["Synthesized from training data and system prompt"]
            explanation = await generate_explanation_chain(
                decision=final_text[:100] + "...",
                evidence=evidence_list,
                reasoning_steps=reasoning_list,
                confidence=0.8,
            )
            final_text = final_text + "\n\n" + explanation
        except Exception as e:
            logger.warning(f"Explanation chain failed (non-fatal): {e}")

    return final_text


async def _make_llm_call(client, model, messages, tools, temperature):
    return await client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        temperature=temperature,
    )


async def _call_llm_with_cascade(
    agent,
    db,
    messages,
    tools,
    temperature,
    trace_steps,
):
    from app.services.llm_cache import llm_cache_lookup, llm_cache_store
    from app.services.model_router import MultiModelRouter, record_model_performance

    cached = await llm_cache_lookup(agent.ai_model, messages, tools)
    if cached is not None:
        trace_steps.append({"step": "cache_hit", "model": agent.ai_model})
        return cached, 0, agent.ai_model

    from app.services.tool_adapter import supports_tool_calling as _supports_tools
    use_text_tools = tools and not _supports_tools(agent.ai_model)
    if use_text_tools:
        messages = [
            {"role": "user" if m.get("role") == "tool" else m.get("role", "user"),
             "content": str(m.get("content", "")) + (
                 f"\n[Tool: {m.get('name', '')}]\nResult: {m.get('content', '')}\n"
                 if m.get("role") == "tool" else ""
             ),
             **{k: v for k, v in m.items() if k not in ("role", "content")}}
            if isinstance(m, dict) else m
            for m in messages
        ]

    router = MultiModelRouter()
    user_message = messages[-1].get("content", "") if messages else ""
    routed_decision = None
    classification_tier = "standard"
    classification_confidence = 0.5
    try:
        routed_decision = await router.route(user_message, agent, db)
        classification_tier = router._last_tier
        classification_confidence = router._last_confidence
    except Exception as e:
        logger.warning(f"Model routing failed, using agent default: {e}")

    primary_model = agent.ai_model
    if routed_decision and routed_decision.selected_model != agent.ai_model and classification_confidence >= 0.6:
        primary_model = routed_decision.selected_model
        trace_steps.append({
            "step": "model_routed",
            "original": agent.ai_model,
            "routed": primary_model,
            "tier": classification_tier,
            "confidence": classification_confidence,
        })

    cascade = build_full_cascade(primary_model, agent, agent_model=agent.ai_model)
    health = get_provider_health()
    last_error = None
    used_model = None

    for attempt, entry in enumerate(cascade):
        model_name = entry["model"]
        provider = entry["provider"]

        if not await health.is_healthy(provider):
            trace_steps.append({"step": "fallback_skip", "reason": f"Circuit open for {provider}", "model": model_name})
            continue

        try:
            client, _ = await resolve_provider_client(model_name, agent, db)

            model_supports_tools = True
            adapted_tools = tools
            from app.services.tool_adapter import supports_tool_calling, tools_to_text_prompt
            if tools and not supports_tool_calling(model_name):
                model_supports_tools = False
                tool_text = tools_to_text_prompt(tools)
                messages = list(messages)
                if messages:
                    last = dict(messages[-1])
                    last["content"] = str(last.get("content", "")) + tool_text
                    messages[-1] = last
                adapted_tools = None
                trace_steps.append({"step": "tool_adaptation", "reason": f"Model {model_name} does not support native tools"})

            llm_start = time.monotonic()
            _safe_call = async_retry(max_retries=2, base_delay=0.5)(_make_llm_call)
            response = await _safe_call(
                client=client,
                model=model_name,
                messages=messages,
                tools=adapted_tools,
                temperature=temperature,
            )
            llm_latency = int((time.monotonic() - llm_start) * 1000)
            await health.record_success(provider, llm_latency)
            used_model = model_name

            await llm_cache_store(primary_model, messages, tools, response)

            usage = response.usage
            total_tokens = (usage.prompt_tokens + usage.completion_tokens) if usage else 0
            from app.services.agent_cost_tracker import calculate_token_cost
            est_cost = calculate_token_cost(usage.prompt_tokens if usage else 0, usage.completion_tokens if usage else 0)
            await record_model_performance(
                model_name=used_model,
                latency_ms=int(llm_latency),
                tokens_used=total_tokens,
                estimated_cost_usd=est_cost,
                success=True,
            )

            if attempt > 0:
                trace_steps.append({"step": "fallback_used", "original_model": cascade[0]["model"], "used_model": model_name, "attempt": attempt + 1})
            return response, llm_latency, used_model
        except Exception as e:
            await health.record_failure(provider)
            last_error = e
            trace_steps.append({"step": "fallback_fail", "model": model_name, "error": str(e)[:200], "attempt": attempt + 1})

    raise last_error or RuntimeError("All cascade models failed")


async def execute_agent_run(
    db: AsyncSession,
    agent_id: str,
    input_payload: Dict[str, Any],
    trigger_source: str = "manual",
    idempotency_key: str = None,
) -> Dict[str, Any]:
    from app.services.telemetry import tracer, OTEL_AVAILABLE
    from opentelemetry import trace as otel_trace
    from opentelemetry import context as otel_context
    
    telemetry_span = None
    telemetry_token = None
    if OTEL_AVAILABLE and tracer:
        try:
            telemetry_span = tracer.start_span("execute_agent_run", attributes={
                "agent.id": agent_id,
                "trigger_source": trigger_source,
                "tenant_id": str(input_payload.get("tenant_id", "default"))
            })
            context = otel_trace.set_span_in_context(telemetry_span)
            telemetry_token = otel_context.attach(context)
        except Exception as otel_err:
            logger.warning(f"Failed to start telemetry span: {otel_err}")

    try:
        result = await _execute_agent_run_inner(db, agent_id, input_payload, trigger_source, idempotency_key)
        if telemetry_span and isinstance(result, dict) and "status" in result:
            telemetry_span.set_attribute("status", result["status"])
            telemetry_span.set_status(otel_trace.StatusCode.OK)
        return result
    except Exception as e:
        if telemetry_span:
            telemetry_span.record_exception(e)
            telemetry_span.set_status(otel_trace.StatusCode.ERROR, str(e))
        raise
    finally:
        if telemetry_token:
            otel_context.detach(telemetry_token)
        if telemetry_span:
            telemetry_span.end()


async def _execute_agent_run_inner(
    db: AsyncSession,
    agent_id: str,
    input_payload: Dict[str, Any],
    trigger_source: str = "manual",
    idempotency_key: str = None,
) -> Dict[str, Any]:
    """
    Orchestrates synchronous agent execution:
    Budget Check -> Context Builder -> ReAct/Plan-Execute/Standard loop execution -> Costs tracking.
    """
    start_time = time.monotonic()

    # Idempotency check
    user_id = input_payload.get("user_id", "")
    if idempotency_key and user_id:
        from app.services.idempotency import check_idempotency
        cached = await check_idempotency(agent_id, user_id, idempotency_key, db)
        if cached is not None:
            return cached

    # Budget check
    estimated_cost = 0.05
    from app.services.agent_budget import check_budget, BudgetCheckResult
    budget_result = await check_budget(agent_id, estimated_cost, db)
    if budget_result == BudgetCheckResult.BLOCKED:
        raise ValueError("Agent budget exceeded — execution blocked")
    if budget_result == BudgetCheckResult.WARNING:
        logger.warning(f"Agent {agent_id} approaching budget limit")

    from app.services.agent_pool import AgentPoolManager
    pool = await AgentPoolManager.get_pool(agent_id, db)
    pool_start = time.monotonic()
    pool_agent = await pool.get_agent()
    pool_latency_ms = int((time.monotonic() - pool_start) * 1000)
    pool_stats = await pool.get_pool_stats()

    resolved_agent_id = agent_id
    ab_variant_id = None
    try:
        resolved = await ABDeployment.route_request(agent_id, input_payload, db)
        if resolved != agent_id:
            ab_variant_id = resolved
            resolved_agent_id = resolved
            logger.info(f"AB routing: {agent_id} -> {resolved_agent_id}")
    except Exception as e:
        logger.warning(f"AB routing failed, using base agent: {e}")
    
    # 1. Get Agent
    agent_res = await db.execute(select(Agent).where(Agent.id == resolved_agent_id))
    agent = agent_res.scalar_one_or_none()
    if not agent:
        raise ValueError(f"Agente con ID {resolved_agent_id} no encontrado.")
        
    config_res = await db.execute(select(AgentConfig).where(AgentConfig.agent_id == resolved_agent_id).limit(1))
    config = config_res.scalars().first()
    max_loops = config.max_loops if config else 10
    
    # 2. Init Execution Run Log
    run_log = AgentExecutionRun(
        id=uuid.uuid4().hex,
        agent_id=resolved_agent_id,
        trigger_source=trigger_source,
        status="running",
        input_payload=input_payload,
        loop_count=0,
        token_usage=0,
        cost_usd=0.0,
        latency_ms=0,
        execution_trace="",
        tenant_id=input_payload.get("tenant_id", "unknown")
    )
    db.add(run_log)
    await db.flush()
    current_run_id.set(run_log.id)
    
    from opentelemetry import trace as otel_trace
    try:
        current_span = otel_trace.get_current_span()
        ctx = current_span.get_span_context()
        if ctx.is_valid:
            run_log.trace_id = f"{ctx.trace_id:032x}"
            run_log.span_id = f"{ctx.span_id:016x}"
    except Exception:
        pass
    
    start_type = "warm_start" if pool_stats["warm_starts"] > pool_stats["cold_starts"] else "cold_start"
    trace_steps = [{"step": "agent_pool", "type": start_type, "pool_latency_ms": pool_latency_ms, "available": pool_stats["available_count"], "in_use": pool_stats["in_use_count"]}]

    try:
        # 3. Assemble Context (RAG, Memory, Guardrails, Prompts, active tools)
        from app.services.concurrency_limiter import acquire_run_slot, release_run_slot
        tenant = input_payload.get("tenant_id", "unknown")
        if not await acquire_run_slot(tenant):
            return {"reply": "Demasiadas ejecuciones simultaneas. Intenta de nuevo en unos segundos.", "status": "throttled"}

        messages, active_tools, user_msg, user_id, tenant_id, context_traces = await build_agent_context(
            db=db,
            agent=agent,
            input_payload=input_payload
        )
        trace_steps.extend(context_traces)

        # 4. Workflow specific logic
        if agent.agent_type == "WORKFLOW":
            from app.services.workflow_runtime import execute_workflow_run
            wf_result = await execute_workflow_run(db, agent_id, user_msg)
            run_log.status = "success"
            run_log.output_result = {"reply": json.dumps(wf_result.get("data", {}), default=str), "workflow_status": wf_result.get("status"), "trace": wf_result.get("trace", [])}
            run_log.latency_ms = int((time.monotonic() - start_time) * 1000)
            run_log.cost_usd = 0.0
            run_log.execution_trace = json.dumps(trace_steps, ensure_ascii=False)
            await db.commit()
            release_run_slot(tenant)
            return {"reply": json.dumps(wf_result.get("data", {}), default=str), "workflow_status": wf_result.get("status"), "trace": wf_result.get("trace", [])}

        # 5. Exec Loop Patterns (Plan-Execute or ReAct or Standard loop)
        agent_settings = agent.agent_settings or {}
        
        use_blackboard_orchestrator = agent_settings.get("use_blackboard_orchestrator", False)
        if use_blackboard_orchestrator:
            from app.services.blackboard import BlackboardSession
            session_id = input_payload.get("blackboard_session_id")
            if not session_id:
                session_id = await BlackboardSession.create_session(task_description=user_msg, metadata={"original_agent": agent_id})
                trace_steps.append({"step": "blackboard_session_created", "session_id": session_id})
            
            bb_prompt = f"You are participating in Blackboard Session {session_id}. Provide a well-reasoned hypothesis or validate existing ones."
            messages.append({"role": "system", "content": bb_prompt})
            
            response, llm_latency, used_model = await _call_llm_with_cascade(
                agent=agent, db=db, messages=messages,
                tools=active_tools if active_tools else None,
                temperature=agent.ai_temperature, trace_steps=trace_steps,
            )
            
            final_text = response.choices[0].message.content or ""
            hyp_id = await BlackboardSession.post_hypothesis(session_id, agent_id, final_text)
            trace_steps.append({"step": "blackboard_hypothesis_posted", "hypothesis_id": hyp_id})
            
            safe_text = f"Blackboard Session {session_id} active. Hypothesis {hyp_id} posted. Awaiting peer validation.\n\n{final_text}"
            
            run_log.status = "success"
            run_log.output_result = {"reply": safe_text, "blackboard_session_id": session_id}
            run_log.latency_ms = int((time.monotonic() - start_time) * 1000)
            run_log.execution_trace = json.dumps(trace_steps, ensure_ascii=False)
            
            await apply_reseller_billing(agent, db, run_log.cost_usd, input_payload)
            await db.commit()
            await db.refresh(run_log)
            try:
                release_run_slot(tenant)
            except Exception:
                pass
            return {"reply": safe_text, "blackboard_session_id": session_id}

        use_plan_execute = agent_settings.get("use_plan_execute", False)
        if use_plan_execute:
            from app.services.plan_execute import PlanExecuteLoop
            plan_tools = active_tools if active_tools else None
            plan_loop = PlanExecuteLoop(
                db=db,
                agent=agent,
                user_message=user_msg,
                tools=plan_tools,
                model=agent.ai_model,
                temperature=agent.ai_temperature,
            )
            plan_result = await plan_loop.run(max_iterations=max_loops)
            final_text = plan_result.final_answer

            trace_steps.append({
                "step": "plan_execute",
                "plan": [{"step": s.step_number, "description": s.description, "status": s.status} for s in plan_result.plan],
                "steps_executed": plan_result.steps_executed,
                "total_tool_calls": plan_result.total_tool_calls,
                "replans_made": plan_result.replans_made,
                "confidence": plan_result.confidence,
            })

            # Phase 5: Postprocessing
            final_text = await _apply_phase5_postprocessing(
                final_text=final_text,
                user_msg=user_msg,
                agent=agent,
                active_tools=active_tools,
                trace_steps=trace_steps,
            )

            safe_text = sanitize_output(final_text)
            try:
                client, _ = await get_llm_client(agent.ai_model, agent, db)
                is_safe, mod_result = await moderate_content(safe_text, client)
                if not is_safe:
                    trace_steps.append({"step": "moderation_blocked", "categories": mod_result.get("categories", {})})
                    safe_text = "Lo siento, no puedo generar ese tipo de contenido. Por favor, reformula tu pregunta."
            except Exception as mod_err:
                logger.warning(f"Moderation check skipped: {mod_err}")

            try:
                context_str = "\n".join([m.get("content", "") for m in messages if m.get("role") in ("system", "user")])
                is_hallucination, hall_result = await detect_hallucination(safe_text, agent, db, context=context_str)
                if is_hallucination:
                    trace_steps.append({"step": "hallucination_detected", "confidence": hall_result.get("confidence", 0), "reason": hall_result.get("reason", "")[:200]})
            except Exception:
                pass

            run_log.status = "success"
            run_log.output_result = {"reply": safe_text}

            if user_id:
                try:
                    await save_conversation_turn(db, agent_id, user_id, user_msg, safe_text)
                except Exception as mem_err:
                    logger.warning(f"Failed to save conversation turn: {mem_err}")

            total_tokens = getattr(plan_loop, '_token_count', 0)
            prompt_tok_est = int(total_tokens * 0.6) if total_tokens >= 0 else 0
            comp_tok_est = int(total_tokens * 0.4) if total_tokens >= 0 else 0
            run_log.token_usage = max(0, total_tokens)
            run_log.cost_usd = calculate_token_cost(prompt_tok_est, comp_tok_est)
            run_log.execution_trace = json.dumps(trace_steps, ensure_ascii=False)
            run_log.latency_ms = int((time.monotonic() - start_time) * 1000)

            await apply_reseller_billing(agent, db, run_log.cost_usd, input_payload)
            await db.commit()
            await db.refresh(run_log)
            release_run_slot(tenant)
            return {"reply": safe_text}

        use_react = agent_settings.get("use_react_pattern", False)
        if use_react:
            from app.services.react_loop import ReActLoop
            react_tools = active_tools if active_tools else None
            react_loop = ReActLoop(
                db=db,
                agent=agent,
                user_message=user_msg,
                tools=react_tools,
                model=agent.ai_model,
                temperature=agent.ai_temperature,
            )
            react_result = await react_loop.run(max_iterations=max_loops)
            
            if react_result.status == "paused":
                # Save pause state to the database
                run_log.status = "paused"
                run_log.paused_state = {
                    "conversation": react_loop.conversation,
                    "active_tools": [t.get("function", {}).get("name") for t in active_tools] if active_tools else [],
                    "user_msg": user_msg,
                    "max_loops": max_loops,
                    "last_step": {
                        "action_name": react_result.steps[-1].action_name if react_result.steps else None,
                        "action_args": react_result.steps[-1].action_args if react_result.steps else None,
                        "approval_id": react_result.approval_id
                    }
                }
                run_log.latency_ms = int((time.monotonic() - start_time) * 1000)
                run_log.execution_trace = json.dumps(trace_steps, ensure_ascii=False)
                await db.commit()
                release_run_slot(tenant)
                return {
                    "status": "paused",
                    "run_id": run_log.id,
                    "approval_id": react_result.approval_id,
                    "reply": f"Action requires approval. Approval Request ID: {react_result.approval_id}"
                }

            final_text = react_result.final_answer

            trace_steps.append({
                "step": "react_execution",
                "total_iterations": react_result.total_iterations,
                "total_tool_calls": react_result.total_tool_calls,
                "confidence_score": react_result.confidence_score,
                "execution_summary": react_result.execution_summary,
            })

            # Phase 5: Postprocessing
            final_text = await _apply_phase5_postprocessing(
                final_text=final_text,
                user_msg=user_msg,
                agent=agent,
                active_tools=active_tools,
                trace_steps=trace_steps,
            )

            safe_text = sanitize_output(final_text)
            try:
                client, _ = await get_llm_client(agent.ai_model, agent, db)
                is_safe, mod_result = await moderate_content(safe_text, client)
                if not is_safe:
                    trace_steps.append({"step": "moderation_blocked", "categories": mod_result.get("categories", {})})
                    safe_text = "Lo siento, no puedo generar ese tipo de contenido. Por favor, reformula tu pregunta."
            except Exception as mod_err:
                logger.warning(f"Moderation check skipped: {mod_err}")

            try:
                context_str = "\n".join([m.get("content", "") for m in messages if m.get("role") in ("system", "user")])
                is_hallucination, hall_result = await detect_hallucination(safe_text, agent, db, context=context_str)
                if is_hallucination:
                    trace_steps.append({"step": "hallucination_detected", "confidence": hall_result.get("confidence", 0), "reason": hall_result.get("reason", "")[:200]})
            except Exception:
                pass

            run_log.status = "success"
            run_log.output_result = {"reply": safe_text}

            if user_id:
                try:
                    await save_conversation_turn(db, agent_id, user_id, user_msg, safe_text)
                except Exception as mem_err:
                    logger.warning(f"Failed to save conversation turn: {mem_err}")

            total_tokens = react_result.total_tokens_used
            prompt_tok_est = int(total_tokens * 0.6) if total_tokens >= 0 else 0
            comp_tok_est = int(total_tokens * 0.4) if total_tokens >= 0 else 0
            run_log.token_usage = max(0, total_tokens)
            run_log.cost_usd = calculate_token_cost(prompt_tok_est, comp_tok_est)
            run_log.execution_trace = json.dumps(trace_steps, ensure_ascii=False)
            run_log.latency_ms = int((time.monotonic() - start_time) * 1000)

            await apply_reseller_billing(agent, db, run_log.cost_usd, input_payload)
            await db.commit()
            await db.refresh(run_log)
            release_run_slot(tenant)
            return {"reply": safe_text}

        # 6. Standard re-entrant tool loop (fallback)
        loop_count = 0
        final_text = ""
        total_prompt_tokens = 0
        total_completion_tokens = 0
        
        while loop_count < max_loops:
            loop_count += 1
            run_log.loop_count = loop_count
            
            response, llm_latency, used_model = await _call_llm_with_cascade(
                agent=agent,
                db=db,
                messages=messages,
                tools=active_tools if active_tools else None,
                temperature=agent.ai_temperature,
                trace_steps=trace_steps,
            )
            
            usage = response.usage
            prompt_tok = usage.prompt_tokens if usage else 0
            comp_tok = usage.completion_tokens if usage else 0
            total_prompt_tokens += prompt_tok
            total_completion_tokens += comp_tok
            
            choice = response.choices[0]
            msg = choice.message
            if hasattr(msg, "model_dump"):
                messages.append(msg.model_dump(exclude_none=True))
            elif hasattr(msg, "dict"):
                messages.append(msg.dict(exclude_none=True))
            else:
                messages.append(msg if isinstance(msg, dict) else vars(msg))

            if not msg.tool_calls:
                from app.services.tool_adapter import parse_text_tool_call, make_mock_tool_call
                text_content = msg.content if hasattr(msg, "content") and msg.content else ""
                text_tool = parse_text_tool_call(text_content) if text_content else None
                if text_tool:
                    mock_msg = make_mock_tool_call(text_tool["name"], text_tool["arguments"])
                    messages[-1] = mock_msg
                    msg = mock_msg

            if msg.tool_calls:
                trace_steps.append({
                    "step": f"llm_response_loop_{loop_count}",
                    "latency_ms": llm_latency,
                    "prompt_tokens": prompt_tok,
                    "completion_tokens": comp_tok,
                    "action": "execute_tools",
                    "details": [t.function.name for t in msg.tool_calls]
                })
                
                async def _execute_one(tool):
                    tool_name = tool.function.name
                    tool_args = json.loads(tool.function.arguments or "{}")
                    tool_start = time.monotonic()
                    try:
                        user_payload = {
                            "user_id": input_payload.get("user_id", ""),
                            "role": input_payload.get("role", "employee"),
                            "tenant_id": input_payload.get("tenant_id", "default")
                        }
                        from app.services.tool_acl import enforce_tool_acl
                        acl_result = await enforce_tool_acl(tool_name, user_payload, db)
                        if acl_result.denied:
                            tool_result = json.dumps({"error": acl_result.reason, "message": acl_result.message})
                        else:
                            tool_result = await execute_tool(db, tool_name, tool_args, user_payload=user_payload, agent_id=resolved_agent_id, run_id=run_log.id)
                    except Exception as exc:
                        tool_result = f"Error: {str(exc)}"
                    tool_latency = int((time.monotonic() - tool_start) * 1000)
                    return tool, tool_name, tool_args, str(tool_result), tool_latency

                tool_results = await asyncio.gather(*[_execute_one(t) for t in msg.tool_calls], return_exceptions=False)

                for tool, tool_name, tool_args, tool_result, tool_latency in tool_results:
                    surfaced = _surface_tool_errors(tool_name, tool_result)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool.id,
                        "name": tool_name,
                        "content": surfaced
                    })
                    trace_steps.append({
                        "step": f"tool_execution_{tool_name}",
                        "latency_ms": tool_latency,
                        "arguments": tool_args,
                        "result": surfaced[:500] + "..." if len(surfaced) > 500 else surfaced
                    })
            else:
                final_text = msg.content or ""
                trace_steps.append({
                    "step": f"llm_response_final",
                    "latency_ms": llm_latency,
                    "prompt_tokens": prompt_tok,
                    "completion_tokens": comp_tok,
                    "action": "return_reply",
                    "reply": final_text[:500] + "..." if len(final_text) > 500 else final_text
                })
                break
                
        if loop_count >= max_loops and not final_text:
            raise TimeoutError("El Agente superó el número máximo de ciclos de herramientas (max_loops).")

        # Phase 5: Postprocessing
        final_text = await _apply_phase5_postprocessing(
            final_text=final_text,
            user_msg=user_msg,
            agent=agent,
            active_tools=active_tools,
            trace_steps=trace_steps,
        )

        # 7. Finalization Checks
        safe_text = sanitize_output(final_text)
        try:
            client, _ = await get_llm_client(agent.ai_model, agent, db)
            is_safe, mod_result = await moderate_content(safe_text, client)
            if not is_safe:
                trace_steps.append({"step": "moderation_blocked", "categories": mod_result.get("categories", {})})
                safe_text = "Lo siento, no puedo generar ese tipo de contenido. Por favor, reformula tu pregunta."
        except Exception as mod_err:
            logger.warning(f"Moderation check skipped: {mod_err}")

        try:
            context_str = "\n".join([m.get("content", "") for m in messages if m.get("role") in ("system", "user")])
            is_hallucination, hall_result = await detect_hallucination(safe_text, agent, db, context=context_str)
            if is_hallucination:
                trace_steps.append({"step": "hallucination_detected", "confidence": hall_result.get("confidence", 0), "reason": hall_result.get("reason", "")[:200]})
        except Exception:
            pass

        run_log.status = "success"
        run_log.output_result = {"reply": safe_text}

        if not safe_text or safe_text.strip().lower() in ("completed successfully", "task completed", "done", ""):
            run_log.status = "failed"
            run_log.output_result = {"reply": safe_text, "error": "Agent returned empty or generic completion response"}
            trace_steps.append({"step": "empty_response_detected", "reply": safe_text[:200]})

        if user_id:
            try:
                await save_conversation_turn(db, agent_id, user_id, user_msg, safe_text)
            except Exception as mem_err:
                logger.warning(f"Failed to save conversation turn: {mem_err}")
        
    except Exception as e:
        logger.error(f"Fallo en la ejecución del agente: {e}")
        run_log.status = "failed"
        run_log.output_result = {"error": str(e)}
        trace_steps.append({
            "step": "execution_failed",
            "error": str(e)
        })
        final_text = f"Error en la ejecución: {str(e)}"
        total_prompt_tokens = 0
        total_completion_tokens = 0
        
    # 8. Logging, billing, and budget updates
    duration_ms = int((time.monotonic() - start_time) * 1000)
    run_log.latency_ms = duration_ms
    run_log.token_usage = total_prompt_tokens + total_completion_tokens
    run_log.cost_usd = calculate_token_cost(total_prompt_tokens, total_completion_tokens)
    if ab_variant_id:
        trace_steps.insert(0, {"step": "ab_routed", "original_agent_id": agent_id, "variant_id": ab_variant_id})
    run_log.execution_trace = json.dumps(trace_steps, ensure_ascii=False)

    run_log_id = run_log.id
    run_log_status = run_log.status
    run_log_token_usage = run_log.token_usage
    run_log_cost_usd = run_log.cost_usd
    agent_type = agent.agent_type

    if trigger_source not in ("harness", "harness_ab"):
        record_agent_run(input_payload.get("tenant_id", "unknown"))

    await apply_reseller_billing(agent, db, run_log_cost_usd, input_payload)
        
    await db.commit()

    try:
        release_run_slot(tenant)
    except NameError:
        pass

    try:
        await pool.return_agent(pool_agent)
    except Exception as pool_err:
        logger.warning(f"Pool return failed (non-fatal): {pool_err}")

    try:
        from app.services.agent_reputation import AgentReputation
        await AgentReputation.update_reputation(agent_id, {
            "run_id": run_log_id, "status": run_log_status,
            "reply": final_text, "latency_ms": duration_ms,
            "token_usage": run_log_token_usage, "cost_usd": run_log_cost_usd,
        }, db)
    except Exception as rep_err:
        logger.warning(f"Reputation update failed (non-fatal): {rep_err}")

    await record_budget_consumption(agent_id, run_log_cost_usd, db)

    try:
        from app.services.eu_ai_act import log_ai_transparency
        tools_used = []
        for step in trace_steps:
            if isinstance(step, dict) and "tool" in step.get("step", ""):
                tools_used.append(step.get("step", "").replace("tool_execution_", ""))
        await log_ai_transparency(
            agent_id=agent_id,
            agent_type=agent_type,
            user_input=str(input_payload.get("message", ""))[:2000],
            ai_output=final_text[:5000],
            tools_used=tools_used,
            confidence_score=0.8,
            human_reviewed=run_log_status != "success",
            run_id=run_log_id,
            tenant_id=input_payload.get("tenant_id", "default"),
        )
    except Exception as e:
        logger.debug(f"Transparency logging skipped: {e}")

    try:
        from app.services.agent_analytics_collector import agent_analytics
        tool_calls_count = sum(1 for step in trace_steps if isinstance(step, dict) and step.get("step") == "tool_call")
        await agent_analytics.record_run(
            agent_id=agent_id,
            agent_type=agent_type,
            latency_ms=duration_ms,
            tokens_used=run_log_token_usage,
            cost_usd=run_log_cost_usd,
            status=run_log_status,
            trigger_source=trigger_source,
            tool_calls=tool_calls_count,
        )
    except Exception as e:
        logger.debug(f"Analytics recording skipped: {e}")

    if idempotency_key and user_id:
        try:
            from app.services.idempotency import store_idempotency
            await store_idempotency(
                agent_id, user_id, idempotency_key,
                {"run_id": run_log.id, "status": run_log.status, "reply": final_text,
                 "latency_ms": duration_ms, "token_usage": run_log.token_usage, "cost_usd": run_log.cost_usd, "trace": trace_steps},
                db=db,
            )
        except Exception as e:
            logger.warning(f"Idempotency store failed (non-fatal): {e}")

    try:
        from app.services.runtime_monitor import record_execution
        record_execution({"status": run_log.status, "token_usage": run_log.token_usage, "cost_usd": run_log.cost_usd}, duration_ms)
    except Exception:
        pass

    return {
        "run_id": run_log.id,
        "status": run_log.status,
        "reply": final_text,
        "latency_ms": duration_ms,
        "token_usage": run_log.token_usage,
        "cost_usd": run_log.cost_usd,
        "trace": trace_steps
    }


async def resume_agent_run(
    db: AsyncSession,
    run_id: str,
    approved: bool,
    approver_id: str = "admin",
    rejection_reason: Optional[str] = None
) -> Dict[str, Any]:
    """
    Resumes a paused agent execution run using the stored paused_state.
    """
    current_run_id.set(run_id)
    # 1. Fetch paused run log
    stmt = select(AgentExecutionRun).where(AgentExecutionRun.id == run_id)
    res = await db.execute(stmt)
    run_log = res.scalar_one_or_none()
    
    if not run_log:
        raise ValueError("Execution run not found")
    if run_log.status != "paused":
        raise ValueError(f"Execution run is not paused (status: {run_log.status})")
        
    paused_data = run_log.paused_state
    if not paused_data:
        raise ValueError("No paused state found for this execution run")
        
    # 2. Fetch Agent
    agent_res = await db.execute(select(Agent).where(Agent.id == run_log.agent_id))
    agent = agent_res.scalar_one_or_none()
    if not agent:
        raise ValueError("Agent not found")
        
    # 3. Reconstruct tool observation based on approval
    last_step_info = paused_data.get("last_step", {})
    tool_name = last_step_info.get("action_name")
    tool_args = last_step_info.get("action_args")
    
    if approved:
        # Run the tool! The action was approved, so we proceed to call the actual tool implementation
        try:
            user_payload = {
                "user_id": run_log.input_payload.get("user_id", ""),
                "role": run_log.input_payload.get("role", "employee"),
                "tenant_id": run_log.input_payload.get("tenant_id", "default")
            }
            observation = await execute_tool(db, tool_name, tool_args, user_payload=user_payload, agent_id=agent.id, run_id=run_id)
            trace_steps.append({"step": "tool_exec_success", "tool": tool_name})
        except Exception as e:
            observation = f"Error executing approved action: {str(e)}"
    else:
        observation = f"Action rejected by Admin: {rejection_reason or 'No reason provided.'}"
        
    # Append the observation to the conversation history
    conversation = paused_data.get("conversation", [])
    conversation.append({
        "role": "assistant",
        "content": f"[Tool: {tool_name}({json.dumps(tool_args or {})}) returned: {observation}]",
    })
    
    # 4. Resume ReAct loop
    from app.services.react_loop import ReActLoop
    from app.services.tool_executor import AVAILABLE_TOOLS_SCHEMA
    active_tools_names = paused_data.get("active_tools", [])
    active_tools = [t for t in AVAILABLE_TOOLS_SCHEMA if t.get("function", {}).get("name") in active_tools_names]
    
    react_loop = ReActLoop(
        db=db,
        agent=agent,
        user_message=paused_data.get("user_msg", ""),
        tools=active_tools,
        model=agent.ai_model,
        temperature=agent.ai_temperature,
        conversation=conversation
    )
    
    run_log.status = "running"
    await db.commit()
    
    start_time = time.monotonic()
    react_result = await react_loop.run(max_iterations=paused_data.get("max_loops", 10))
    
    # Handle paused state again (if there is another destructive tool)
    if react_result.status == "paused":
        run_log.status = "paused"
        run_log.paused_state = {
            "conversation": react_loop.conversation,
            "active_tools": active_tools_names,
            "user_msg": paused_data.get("user_msg", ""),
            "max_loops": paused_data.get("max_loops", 10),
            "last_step": {
                "action_name": react_result.steps[-1].action_name if react_result.steps else None,
                "action_args": react_result.steps[-1].action_args if react_result.steps else None,
                "approval_id": react_result.approval_id
            }
        }
        run_log.latency_ms += int((time.monotonic() - start_time) * 1000)
        await db.commit()
        return {
            "status": "paused",
            "run_id": run_log.id,
            "approval_id": react_result.approval_id,
            "reply": f"Action requires approval. Approval Request ID: {react_result.approval_id}"
        }
        
    final_text = react_result.final_answer
    
    # Run post-processing
    from app.services.agent_executor import _apply_phase5_postprocessing, sanitize_output, moderate_content, detect_hallucination
    # Parse trace steps
    try:
        trace_steps = json.loads(run_log.execution_trace) if run_log.execution_trace else []
    except Exception:
        trace_steps = []
        
    trace_steps.append({
        "step": "react_resume_execution",
        "total_iterations": react_result.total_iterations,
        "total_tool_calls": react_result.total_tool_calls,
    })
    
    final_text = await _apply_phase5_postprocessing(
        final_text=final_text,
        user_msg=paused_data.get("user_msg", ""),
        agent=agent,
        active_tools=active_tools,
        trace_steps=trace_steps
    )
    
    safe_text = sanitize_output(final_text)
    
    run_log.status = "success"
    run_log.output_result = {"reply": safe_text}
    run_log.latency_ms += int((time.monotonic() - start_time) * 1000)
    run_log.token_usage += react_result.total_tokens_used
    run_log.execution_trace = json.dumps(trace_steps, ensure_ascii=False)
    
    # Save conversation turn
    user_id = run_log.input_payload.get("user_id", "")
    if user_id:
        try:
            from app.services.copilot_session import save_conversation_turn
            await save_conversation_turn(db, run_log.agent_id, user_id, paused_data.get("user_msg", ""), safe_text)
        except Exception:
            pass
            
    await db.commit()
    await db.refresh(run_log)
    return {
        "run_id": run_log.id,
        "status": run_log.status,
        "reply": safe_text,
        "latency_ms": run_log.latency_ms,
        "token_usage": run_log.token_usage,
        "cost_usd": run_log.cost_usd,
        "trace": trace_steps
    }


async def _call_llm_cascade(
    messages: List[Dict[str, Any]],
    model: str = "gpt-4o-mini",
    temperature: float = 0.2,
    max_tokens: Optional[int] = None,
    db: Optional[AsyncSession] = None,
) -> str:
    """
    Simplified direct LLM caller that runs the model cascade and returns the text response.
    Used by domain services like candidate_screener.py that don't need a full agent session.
    """
    cascade = build_full_cascade(model, None, agent_model=model)
    health = get_provider_health()
    last_error = None

    for attempt, entry in enumerate(cascade):
        model_name = entry["model"]
        provider = entry["provider"]

        if not await health.is_healthy(provider):
            continue

        try:
            client, _ = await resolve_provider_client(model_name, None, db)
            
            # Prepare kwargs for the chat completions create call
            kwargs = {
                "model": model_name,
                "messages": messages,
                "temperature": temperature,
            }
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens

            llm_start = time.monotonic()
            _safe_call = async_retry(max_retries=2, base_delay=0.5)(_make_llm_call_direct)
            response = await _safe_call(client, kwargs)
            llm_latency = int((time.monotonic() - llm_start) * 1000)
            await health.record_success(provider, llm_latency)

            choice = response.choices[0]
            return choice.message.content or ""
        except Exception as e:
            await health.record_failure(provider)
            last_error = e
            logger.warning(f"Direct LLM cascade fallback attempt {attempt + 1} failed for {model_name}: {e}")

    raise last_error or RuntimeError("All cascade models failed in direct call")


async def _make_llm_call_direct(client, kwargs):
    return await client.chat.completions.create(**kwargs)


