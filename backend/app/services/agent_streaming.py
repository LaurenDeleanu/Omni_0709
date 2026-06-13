import time
import json
import logging
import asyncio
import uuid
from typing import Dict, Any, Optional, List, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent import Agent, AgentConfig, AgentExecutionRun
from app.services.llm_router import get_llm_client
from app.services.model_fallback import (
    build_full_cascade,
    resolve_provider_client,
    get_provider_health,
)
from app.services.tool_executor import execute_tool
from app.services.pii_sanitizer import sanitize_output
from app.services.moderation_service import moderate_content
from app.services.hallucination_detector import detect_hallucination
from app.services.ab_deployment import ABDeployment
from app.services.agent_memory import save_conversation_turn
from app.core.retry import async_retry

# Modular helpers
from app.services.agent_context_builder import build_agent_context
from app.services.agent_cost_tracker import calculate_token_cost, apply_reseller_billing, record_budget_consumption

logger = logging.getLogger("successcore.agent_streaming")

async def _make_llm_call_streaming(client, model, messages, tools, temperature):
    return await client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        temperature=temperature,
        stream=True,
    )


async def _call_llm_with_cascade_streaming(
    agent,
    db,
    messages,
    tools,
    temperature,
):
    from app.services.model_router import MultiModelRouter
    router = MultiModelRouter()
    user_message = messages[-1].get("content", "") if messages else ""
    primary_model = agent.ai_model
    try:
        decision = await router.route(user_message, agent, db)
        if decision and decision.selected_model:
            primary_model = decision.selected_model
    except Exception as e:
        logger.warning(f"Model routing failed for streaming, using agent default: {e}")

    cascade = build_full_cascade(primary_model, agent, agent_model=agent.ai_model)
    health = get_provider_health()
    last_error = None

    for attempt, entry in enumerate(cascade):
        model_name = entry["model"]
        provider = entry["provider"]

        if not await health.is_healthy(provider):
            if attempt == len(cascade) - 1:
                raise RuntimeError(f"All models in cascade unavailable. Circuit open for {provider}")
            continue

        try:
            client, _ = await resolve_provider_client(model_name, agent, db)
            _safe_call = async_retry(max_retries=2, base_delay=0.5)(_make_llm_call_streaming)
            response = await _safe_call(
                client=client,
                model=model_name,
                messages=messages,
                tools=tools,
                temperature=temperature,
            )
            await health.record_success(provider)
            return response, model_name
        except Exception as e:
            await health.record_failure(provider)
            last_error = e

    raise last_error or RuntimeError("All cascade models failed")


async def execute_agent_run_streaming(
    db: AsyncSession,
    agent_id: str,
    input_payload: Dict[str, Any],
    trigger_source: str = "manual",
    idempotency_key: str = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Orchestrates real-time SSE streaming agent execution.
    """
    from app.services.telemetry import tracer, OTEL_AVAILABLE
    from opentelemetry import trace as otel_trace
    from opentelemetry import context as otel_context

    from app.services.runtime_monitor import heartbeat_tracker as _hb

    telemetry_span = None
    telemetry_token = None
    if OTEL_AVAILABLE and tracer:
        try:
            telemetry_span = tracer.start_span("execute_agent_run_streaming", attributes={
                "agent.id": agent_id,
                "trigger_source": trigger_source,
                "tenant_id": str(input_payload.get("tenant_id", "default"))
            })
            context = otel_trace.set_span_in_context(telemetry_span)
            telemetry_token = otel_context.attach(context)
        except Exception as otel_err:
            logger.warning(f"Failed to start telemetry span in stream: {otel_err}")

    start_time = time.monotonic()
    user_id = input_payload.get("user_id", "")
    tenant = input_payload.get("tenant_id", "unknown")
    run_log = None

    try:
        if idempotency_key and user_id:
            from app.services.idempotency import check_idempotency
            cached = await check_idempotency(agent_id, user_id, idempotency_key, db)
            if cached is not None:
                yield {"event": "done", "data": cached}
                return

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

        agent_res = await db.execute(select(Agent).where(Agent.id == resolved_agent_id))
        agent = agent_res.scalar_one_or_none()
        if not agent:
            yield {"event": "error", "data": {"error": f"Agente con ID {resolved_agent_id} no encontrado."}}
            return

        config_res = await db.execute(select(AgentConfig).where(AgentConfig.agent_id == resolved_agent_id).limit(1))
        config = config_res.scalars().first()
        max_loops = config.max_loops if config else 10

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
            execution_trace=""
        )
        db.add(run_log)
        await db.flush()

        try:
            current_span = otel_trace.get_current_span()
            ctx = current_span.get_span_context()
            if ctx.is_valid:
                run_log.trace_id = f"{ctx.trace_id:032x}"
                run_log.span_id = f"{ctx.span_id:016x}"
        except Exception:
            pass

        trace_steps = []
        messages = []
        final_text = ""
        total_prompt_tokens = 0
        total_completion_tokens = 0

        from app.services.concurrency_limiter import acquire_run_slot, release_run_slot
        if not await acquire_run_slot(tenant):
            yield {"event": "error", "data": {"error": "Demasiadas ejecuciones simultaneas. Intenta de nuevo."}}
            return

        messages, active_tools, user_msg, user_id, tenant_id, context_traces = await build_agent_context(
            db=db,
            agent=agent,
            input_payload=input_payload
        )
        trace_steps.extend(context_traces)

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
            yield {"event": "done", "data": {"reply": json.dumps(wf_result.get("data", {}), default=str), "workflow_status": wf_result.get("status"), "trace": wf_result.get("trace", [])}}
            return

        # Exec ReAct or Plan-Execute or Standard loop with streaming
        agent_settings = agent.agent_settings or {}
        use_plan_execute = agent_settings.get("use_plan_execute", False)
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
                conversation=messages if messages else None
            )

            react_steps_trace = []
            current_step_info = None

            async for event in react_loop.run_stream(max_iterations=max_loops):
                ev_name = event.get("event")
                ev_data = event.get("data")

                if ev_name == "react_thought":
                    current_step_info = {"thought": ev_data, "action": None, "observation": None}
                    react_steps_trace.append(current_step_info)
                elif ev_name == "react_action":
                    if current_step_info:
                        current_step_info["action"] = ev_data
                elif ev_name == "react_observation":
                    if current_step_info:
                        current_step_info["observation"] = ev_data
                elif ev_name == "token":
                    final_text += ev_data

                if ev_name == "paused":
                    # Save pause state to the database
                    run_log.status = "paused"
                    run_log.paused_state = {
                        "conversation": react_loop.conversation,
                        "active_tools": [t.get("function", {}).get("name") for t in active_tools] if active_tools else [],
                        "user_msg": user_msg,
                        "max_loops": max_loops,
                        "last_step": {
                            "action_name": current_step_info.get("action", {}).get("name") if current_step_info else None,
                            "action_args": current_step_info.get("action", {}).get("args") if current_step_info else None,
                            "approval_id": ev_data.get("approval_id")
                        }
                    }
                    yield event
                    break
                elif ev_name == "done":
                    continue
                else:
                    if ev_name == "token" and isinstance(ev_data, str):
                        yield {"event": "token", "data": {"text": ev_data}}
                    else:
                        yield event

            if run_log.status == "paused":
                # Finalize paused run log
                duration_ms = int((time.monotonic() - start_time) * 1000)
                run_log.latency_ms = duration_ms
                if ab_variant_id:
                    trace_steps.insert(0, {"step": "ab_routed", "original_agent_id": agent_id, "variant_id": ab_variant_id})
                trace_steps.append({
                    "step": "react_execution_paused",
                    "steps": react_steps_trace
                })
                run_log.execution_trace = json.dumps(trace_steps, ensure_ascii=False)
                await db.commit()
                release_run_slot(tenant)
                return

            trace_steps.append({
                "step": "react_execution",
                "steps": react_steps_trace
            })

            total_tokens = getattr(react_loop, '_token_count', 0)
            total_prompt_tokens = int(total_tokens * 0.6)
            total_completion_tokens = int(total_tokens * 0.4)

        elif use_plan_execute:
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

            plan_steps_trace = []
            async for event in plan_loop.run_stream(max_iterations=max_loops):
                ev_name = event.get("event")
                ev_data = event.get("data")

                if ev_name == "plan_created":
                    plan_steps_trace = ev_data
                elif ev_name == "plan_updated":
                    plan_steps_trace = ev_data
                elif ev_name == "token":
                    final_text += ev_data
                
                if ev_name == "done":
                    continue
                else:
                    if ev_name == "token" and isinstance(ev_data, str):
                        yield {"event": "token", "data": {"text": ev_data}}
                    else:
                        yield event

            trace_steps.append({
                "step": "plan_execute",
                "plan": plan_steps_trace
            })

            total_tokens = getattr(plan_loop, '_token_count', 0)
            total_prompt_tokens = int(total_tokens * 0.6)
            total_completion_tokens = int(total_tokens * 0.4)

        else:
            # Standard re-entrant streaming loop
            loop_count = 0
            full_content_buffer = ""

            while loop_count < max_loops:
                loop_count += 1
                run_log.loop_count = loop_count

                yield {"event": "status", "data": {"status": "thinking", "loop": loop_count}}
                await _hb.beat(run_log.id)

                llm_start = time.monotonic()
                response, used_model = await _call_llm_with_cascade_streaming(
                    agent=agent,
                    db=db,
                    messages=messages,
                    tools=active_tools if active_tools else None,
                    temperature=agent.ai_temperature,
                )
                llm_latency = int((time.monotonic() - llm_start) * 1000)

                accumulated = {"content": "", "tool_calls": []}

                async for chunk in response:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if not delta:
                        continue

                    if delta.content:
                        safe_token = sanitize_output(delta.content)
                        accumulated["content"] += delta.content
                        yield {"event": "token", "data": {"text": safe_token}}

                    if delta.tool_calls:
                        for tc_delta in delta.tool_calls:
                            idx = tc_delta.index
                            while len(accumulated["tool_calls"]) <= idx:
                                accumulated["tool_calls"].append({"id": "", "name": "", "arguments": ""})
                            if tc_delta.id:
                                accumulated["tool_calls"][idx]["id"] = tc_delta.id
                            if tc_delta.function:
                                if tc_delta.function.name:
                                    accumulated["tool_calls"][idx]["name"] = tc_delta.function.name
                                if tc_delta.function.arguments:
                                    accumulated["tool_calls"][idx]["arguments"] += tc_delta.function.arguments

                comp_tok = len(accumulated["content"]) // 3
                total_completion_tokens += comp_tok

                full_content_buffer += accumulated["content"]

                assistant_msg = {"role": "assistant", "content": accumulated["content"] or None}
                if accumulated["tool_calls"]:
                    tool_call_objects = []
                    for tc in accumulated["tool_calls"]:
                        tool_call_objects.append({
                            "id": tc["id"] or "call_unknown",
                            "type": "function",
                            "function": {"name": tc["name"], "arguments": tc["arguments"]}
                        })
                    assistant_msg["tool_calls"] = tool_call_objects
                    assistant_msg["content"] = accumulated["content"] or ""

                messages.append(assistant_msg)

                # Handle tool calls
                has_tool_calls = bool(accumulated["tool_calls"])
                if has_tool_calls:
                    tasks = []
                    for tc in accumulated["tool_calls"]:
                        tool_name = tc["name"]
                        try:
                            tool_args = json.loads(tc["arguments"] or "{}")
                        except json.JSONDecodeError:
                            tool_args = {}

                        yield {"event": "tool_call", "data": {"tool_name": tool_name, "arguments": tool_args}}

                        user_payload = {
                            "user_id": input_payload.get("user_id", ""),
                            "role": input_payload.get("role", "employee"),
                            "tenant_id": input_payload.get("tenant_id", "default")
                        }
                        
                        # Create task but don't await yet
                        tasks.append(execute_tool(db, tool_name, tool_args, user_payload=user_payload, agent_id=resolved_agent_id, run_id=run_log.id))

                    # Wait for all tools to finish concurrently
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    from app.services.agent_executor import _surface_tool_errors
                    for tc, tool_result_raw in zip(accumulated["tool_calls"], results):
                        tool_name = tc["name"]
                        if isinstance(tool_result_raw, Exception):
                            tool_result = f"Error: {str(tool_result_raw)}"
                        else:
                            tool_result = _surface_tool_errors(tool_name, str(tool_result_raw))

                        yield {"event": "tool_result", "data": {"tool_name": tool_name, "output": str(tool_result)[:500]}}

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"] or "call_unknown",
                            "name": tool_name,
                            "content": str(tool_result)
                        })
                    accumulated["content"] = ""
                    accumulated["tool_calls"] = []
                else:
                    final_text = accumulated["content"]
                    break

            if loop_count >= max_loops and not final_text:
                raise TimeoutError("El Agente supero el numero maximo de ciclos de herramientas (max_loops).")

        run_log.status = "success"
        safe_text = sanitize_output(final_text)

        try:
            client, _ = await get_llm_client(agent.ai_model, agent, db)
            is_safe, mod_result = await moderate_content(safe_text, client)
            if not is_safe:
                safe_text = "Lo siento, no puedo generar ese tipo de contenido."
        except Exception:
            pass

        run_log.output_result = {"reply": safe_text}

        if user_id:
            try:
                await save_conversation_turn(db, agent_id, user_id, user_msg, safe_text)
            except Exception as mem_err:
                logger.warning(f"Failed to save conversation turn (stream): {mem_err}")

    except asyncio.CancelledError:
        logger.info(f"Agent run streaming cancelled for agent {agent_id}")
        if run_log is not None:
            run_log.status = "cancelled"
            run_log.output_result = {"error": "Client disconnected"}
            try:
                await _hb.remove(run_log.id)
            except Exception:
                pass
        final_text = ""
        yield {"event": "cancelled", "data": {"message": "Request cancelled by client"}}
        total_prompt_tokens = 0
        total_completion_tokens = 0
    except Exception as e:
        logger.error(f"Fallo en la ejecucion del agente (stream): {e}")
        if run_log is not None:
            run_log.status = "failed"
            run_log.output_result = {"error": str(e)}
        final_text = f"Error en la ejecucion: {str(e)}"
        yield {"event": "error", "data": {"error": str(e)}}
        total_prompt_tokens = 0
        total_completion_tokens = 0
    finally:
        if telemetry_token:
            try:
                otel_context.detach(telemetry_token)
            except Exception:
                pass
        if telemetry_span:
            try:
                telemetry_span.end()
            except Exception:
                pass

    duration_ms = int((time.monotonic() - start_time) * 1000)
    if run_log is not None:
        try:
            run_log.latency_ms = duration_ms
            run_log.token_usage = total_prompt_tokens + total_completion_tokens
            run_log.cost_usd = calculate_token_cost(total_prompt_tokens, total_completion_tokens)

            if ab_variant_id:
                trace_steps.insert(0, {"step": "ab_routed", "original_agent_id": agent_id, "variant_id": ab_variant_id})
            run_log.execution_trace = json.dumps(trace_steps, ensure_ascii=False)

            await apply_reseller_billing(agent, db, run_log.cost_usd, input_payload)
            await db.commit()
            await db.refresh(run_log)
        except Exception as log_err:
            logger.warning(f"Failed to persist run log (non-fatal): {log_err}")
            try:
                await db.rollback()
            except Exception:
                pass

    try:
        release_run_slot(tenant)
    except NameError:
        pass

    final_data = {
        "run_id": run_log.id if run_log is not None else "",
        "status": run_log.status if run_log is not None else "failed",
        "reply": final_text,
        "latency_ms": duration_ms,
        "token_usage": run_log.token_usage if run_log is not None else 0,
        "cost_usd": run_log.cost_usd if run_log is not None else 0.0,
    }

    if idempotency_key and user_id:
        try:
            from app.services.idempotency import store_idempotency
            await store_idempotency(agent_id, user_id, idempotency_key, final_data, db=db)
        except Exception as e:
            logger.warning(f"Idempotency store failed (non-fatal stream): {e}")

    yield {
        "event": "done",
        "data": final_data,
    }
