import json
import logging
import time
from typing import Any, Optional
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.tool_executor import execute_tool
from app.services.llm_router import get_llm_client

logger = logging.getLogger(__name__)


@dataclass
class ToolCallSpec:
    tool: str
    args: dict
    expected_outcome: str = ""


@dataclass
class PlanStep:
    step_number: int
    description: str
    tool_calls: list = field(default_factory=list)
    expected_outcome: str = ""
    status: str = "pending"
    result: Optional[str] = None
    evaluation: Optional[dict] = None


@dataclass
class PlanExecuteResult:
    plan: list = field(default_factory=list)
    steps_executed: int = 0
    final_answer: str = ""
    replans_made: int = 0
    total_tool_calls: int = 0
    confidence: float = 0.0
    results_per_step: list = field(default_factory=list)


async def _call_llm(client, model: str, messages: list, temperature: float, response_format: Optional[dict] = None):
    kwargs = dict(model=model, messages=messages, temperature=temperature)
    if response_format:
        kwargs["response_format"] = response_format
    return await client.chat.completions.create(**kwargs)


class PlanExecuteLoop:

    def __init__(
        self,
        db: AsyncSession,
        agent,
        user_message: str,
        tools: list,
        model: str,
        temperature: float = 0.3,
    ):
        self.db = db
        self.agent = agent
        self.user_message = user_message
        self.tools = tools or []
        self.model = model
        self.temperature = temperature
        self._token_count = 0
        self._client = None

    async def _get_client(self):
        if self._client is None:
            self._client, _ = await get_llm_client(self.model, self.agent, self.db)
        return self._client

    def _accumulate_tokens(self, response):
        usage = response.usage
        if usage:
            self._token_count += usage.prompt_tokens or 0
            self._token_count += usage.completion_tokens or 0

    async def run(self, max_iterations: int = 15) -> PlanExecuteResult:
        result = PlanExecuteResult()
        client = await self._get_client()

        conversation = []
        system_prompt = self._build_system_prompt()
        conversation.append({"role": "system", "content": system_prompt})

        plan = await self._generate_plan(self.user_message, conversation, client)
        result.plan = plan

        step_index = 0
        while step_index < len(plan) and result.steps_executed < max_iterations:
            current_step = plan[step_index]
            step_number = current_step.step_number
            current_step.status = "running"

            summary = await self._execute_step(current_step, client)
            result.steps_executed += 1
            result.total_tool_calls += len(current_step.tool_calls)

            evaluation = await self._evaluate_step(step_number, summary, current_step, client)
            current_step.evaluation = evaluation
            current_step.result = summary

            result.results_per_step.append({
                "step_number": step_number,
                "description": current_step.description,
                "result": summary,
                "evaluation": evaluation,
                "tool_calls": [t.tool for t in current_step.tool_calls] if isinstance(current_step.tool_calls, list) and current_step.tool_calls and hasattr(current_step.tool_calls[0], 'tool') else [],
            })

            if evaluation.get("should_replan") and step_index >= 2:
                result.replans_made += 1
                remaining = plan[step_index + 1:]
                plan = await self._replan(self.user_message, plan, current_step, evaluation, conversation, client)
                step_index = len(plan) - len(remaining)
            else:
                current_step.status = "completed"
                step_index += 1

            conversation.append({
                "role": "assistant",
                "content": f"Step {step_number} completed: {summary[:300]}"
            })

        result.final_answer = await self._synthesize(plan, conversation, client)
        result.confidence = await self._estimate_confidence(client, result)

        return result

    async def run_stream(self, max_iterations: int = 15):
        client = await self._get_client()

        conversation = []
        system_prompt = self._build_system_prompt()
        conversation.append({"role": "system", "content": system_prompt})

        plan = await self._generate_plan(self.user_message, conversation, client)
        yield {
            "event": "plan_created",
            "data": [{"step": s.step_number, "description": s.description} for s in plan]
        }

        steps_executed = 0
        step_index = 0
        while step_index < len(plan) and steps_executed < max_iterations:
            current_step = plan[step_index]
            step_number = current_step.step_number
            current_step.status = "running"

            yield {
                "event": "step_start",
                "data": {"step_number": step_number, "description": current_step.description}
            }

            summary = await self._execute_step(current_step, client)
            steps_executed += 1

            evaluation = await self._evaluate_step(step_number, summary, current_step, client)
            current_step.evaluation = evaluation
            current_step.result = summary

            yield {
                "event": "step_complete",
                "data": {"step_number": step_number, "result": summary}
            }

            if evaluation.get("should_replan") and step_index >= 2:
                plan = await self._replan(self.user_message, plan, current_step, evaluation, conversation, client)
                yield {
                    "event": "plan_updated",
                    "data": [{"step": s.step_number, "description": s.description} for s in plan]
                }
                # Recalculate step_index
                remaining = plan[step_index + 1:]
                step_index = len(plan) - len(remaining)
            else:
                current_step.status = "completed"
                step_index += 1

            conversation.append({
                "role": "assistant",
                "content": f"Step {step_number} completed: {summary[:300]}"
            })

        # --- SYNTHESIZE ANSWER (STREAMED) ---
        yield {"event": "status", "data": "synthesizing"}
        
        steps_summary = ""
        for s in plan:
            steps_summary += f"\nStep {s.step_number}: {s.description} -> Result: {s.result or 'N/A'}"
            if s.evaluation:
                steps_summary += f" (Success: {s.evaluation.get('success', 'unknown')})"

        synth_messages = conversation + [{
            "role": "user",
            "content": (
                f"User request: {self.user_message}\n\n"
                f"Plan execution summary:\n{steps_summary}\n\n"
                "Synthesize a comprehensive final answer based on all the steps above. "
                "Be thorough and structured. Include key findings and conclusions."
            ),
        }]

        try:
            resp_stream = await client.chat.completions.create(
                model=self.model,
                messages=synth_messages,
                temperature=max(self.temperature, 0.5),
                stream=True
            )
            async for chunk in resp_stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    yield {"event": "token", "data": token}
        except Exception as e:
            logger.error(f"Error streaming plan synthesis: {e}")
            yield {"event": "token", "data": f"Error during synthesis: {e}"}

        yield {"event": "done", "data": ""}


    def _build_system_prompt(self) -> str:
        tool_names = [t.get("function", {}).get("name", "") for t in self.tools]
        return (
            f"{self.agent.ai_system_prompt}\n\n"
            "You are operating in Plan-and-Execute mode.\n"
            "Break down the user's request into sequential steps. Execute each step, "
            "evaluate results, and decide whether to continue or adjust the plan.\n"
            f"Available tools: {', '.join(tool_names) if tool_names else 'None'}.\n"
        )

    async def _generate_plan(self, user_message: str, history: list, client) -> list:
        supports_json_schema = self.model.startswith("gpt-") or self.model.startswith("o1") or self.model.startswith("o3")
        
        user_msg = (
            "Given the user's request, create a step-by-step plan to accomplish it. "
            "For each step, specify what tool(s) you'll use and what you expect to learn.\n\n"
            f"User request: {user_message}\n\n"
        )
        
        response_format = None
        if supports_json_schema:
            user_msg += "Respond with a JSON object containing a 'steps' array."
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "plan_schema",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "steps": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "step_number": {"type": "integer"},
                                        "description": {"type": "string"},
                                        "tool_calls": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "tool": {"type": "string"},
                                                    "args": {"type": "object"},
                                                    "expected_outcome": {"type": "string"}
                                                },
                                                "required": ["tool", "args", "expected_outcome"],
                                                "additionalProperties": False
                                            }
                                        },
                                        "expected_outcome": {"type": "string"}
                                    },
                                    "required": ["step_number", "description", "tool_calls", "expected_outcome"],
                                    "additionalProperties": False
                                }
                            }
                        },
                        "required": ["steps"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            }
        else:
            user_msg += (
                "Respond with a JSON object containing a 'steps' array. Each step must have: "
                "step_number (int), description (string), tool_calls (array of {tool: string, args: object, expected_outcome: string}), "
                "expected_outcome (string).\n"
                'Example: {"steps": [{"step_number": 1, "description": "...", "tool_calls": [{"tool": "search", "args": {"query": "..."}, "expected_outcome": "..."}], "expected_outcome": "..."}]}'
            )

        plan_messages = history + [{"role": "user", "content": user_msg}]

        resp = await _call_llm(client, self.model, plan_messages, self.temperature, response_format=response_format)
        self._accumulate_tokens(resp)
        content = resp.choices[0].message.content or "{}"

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                try:
                    data = json.loads(match.group(0))
                except json.JSONDecodeError:
                    return []
            else:
                return []

        steps_data = data.get("steps", [])
        if not isinstance(steps_data, list):
            steps_data = []

        plan_steps = []
        for s in steps_data:
            tool_calls = []
            for tc in s.get("tool_calls", []):
                tool_calls.append(ToolCallSpec(
                    tool=tc.get("tool", ""),
                    args=tc.get("args", {}),
                    expected_outcome=tc.get("expected_outcome", ""),
                ))
            plan_steps.append(PlanStep(
                step_number=s.get("step_number", len(plan_steps) + 1),
                description=s.get("description", ""),
                tool_calls=tool_calls,
                expected_outcome=s.get("expected_outcome", ""),
            ))

        return plan_steps

    async def _execute_step(self, step: PlanStep, client) -> str:
        results = []
        for tc_spec in step.tool_calls:
            try:
                outcome = await execute_tool(self.db, tc_spec.tool, tc_spec.args)
                results.append(f"[{tc_spec.tool}]: {str(outcome)}")
            except Exception as exc:
                results.append(f"[{tc_spec.tool}]: Error: {str(exc)}")
        return "\n".join(results) if results else f"No tool calls executed for step {step.step_number}"

    async def _evaluate_step(self, step_number: int, step_result: str, step: PlanStep, client) -> dict:
        supports_json_schema = self.model.startswith("gpt-") or self.model.startswith("o1") or self.model.startswith("o3")
        
        user_msg = (
            f"Step {step_number} description: {step.description}\n"
            f"Expected outcome: {step.expected_outcome}\n"
            f"Actual result: {step_result}\n\n"
            "Evaluate this step. "
        )
        
        response_format = None
        if supports_json_schema:
            user_msg += "Respond with a JSON object."
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "eval_schema",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean"},
                            "actual_learning": {"type": "string"},
                            "should_replan": {"type": "boolean"}
                        },
                        "required": ["success", "actual_learning", "should_replan"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            }
        else:
            user_msg += (
                "Respond with JSON:\n"
                '{"success": true/false, "actual_learning": "what was learned", "should_replan": false}'
            )

        eval_messages = [
            {"role": "system", "content": "You are an evaluation engine. Review the outcome of an executed step and determine if it was successful."},
            {"role": "user", "content": user_msg},
        ]

        resp = await _call_llm(client, self.model, eval_messages, 0.2, response_format=response_format)
        self._accumulate_tokens(resp)
        content = resp.choices[0].message.content or "{}"

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
            return {"success": True, "actual_learning": "Unknown", "should_replan": False}

    async def _replan(self, user_message: str, plan: list, current_step: PlanStep, evaluation: dict, history: list, client) -> list:
        supports_json_schema = self.model.startswith("gpt-") or self.model.startswith("o1") or self.model.startswith("o3")
        
        remaining = []
        for s in plan:
            if s.step_number > current_step.step_number:
                remaining.append(s)

        user_msg = (
            f"User request: {user_message}\n\n"
            f"Step {current_step.step_number} result: {current_step.result}\n"
            f"Evaluation: {json.dumps(evaluation)}\n\n"
            "Given what you've learned so far, does the remaining plan still make sense? "
        )

        response_format = None
        if supports_json_schema:
            user_msg += "Provide an adjusted plan (only the remaining steps) as a JSON object with a 'steps' array. If no changes are needed, return the same steps."
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "plan_schema",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "steps": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "step_number": {"type": "integer"},
                                        "description": {"type": "string"},
                                        "tool_calls": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "tool": {"type": "string"},
                                                    "args": {"type": "object"},
                                                    "expected_outcome": {"type": "string"}
                                                },
                                                "required": ["tool", "args", "expected_outcome"],
                                                "additionalProperties": False
                                            }
                                        },
                                        "expected_outcome": {"type": "string"}
                                    },
                                    "required": ["step_number", "description", "tool_calls", "expected_outcome"],
                                    "additionalProperties": False
                                }
                            }
                        },
                        "required": ["steps"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            }
        else:
            user_msg += (
                "Provide an adjusted plan (only the remaining steps) as JSON with a 'steps' array. "
                "If no changes are needed, return the same steps."
            )

        replan_messages = history + [{"role": "user", "content": user_msg}]

        resp = await _call_llm(client, self.model, replan_messages, self.temperature, response_format=response_format)
        self._accumulate_tokens(resp)
        content = resp.choices[0].message.content or "{}"

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                try:
                    data = json.loads(match.group(0))
                except json.JSONDecodeError:
                    return remaining
            else:
                return remaining

        new_steps = data.get("steps", [])
        if not new_steps:
            return remaining

        replanned = []
        for i, s in enumerate(new_steps):
            tool_calls = []
            for tc in s.get("tool_calls", []):
                tool_calls.append(ToolCallSpec(
                    tool=tc.get("tool", ""),
                    args=tc.get("args", {}),
                    expected_outcome=tc.get("expected_outcome", ""),
                ))
            replanned.append(PlanStep(
                step_number=s.get("step_number", current_step.step_number + 1 + i),
                description=s.get("description", ""),
                tool_calls=tool_calls,
                expected_outcome=s.get("expected_outcome", ""),
            ))

        return plan[:current_step.step_number] + replanned

    async def _synthesize(self, plan: list, history: list, client) -> str:
        steps_summary = ""
        for s in plan:
            steps_summary += f"\nStep {s.step_number}: {s.description} -> Result: {s.result or 'N/A'}"
            if s.evaluation:
                steps_summary += f" (Success: {s.evaluation.get('success', 'unknown')})"

        synth_messages = history + [{
            "role": "user",
            "content": (
                f"User request: {self.user_message}\n\n"
                f"Plan execution summary:\n{steps_summary}\n\n"
                "Synthesize a comprehensive final answer based on all the steps above. "
                "Be thorough and structured. Include key findings and conclusions."
            ),
        }]

        resp = await _call_llm(client, self.model, synth_messages, max(self.temperature, 0.5))
        self._accumulate_tokens(resp)
        return resp.choices[0].message.content or ""

    async def _estimate_confidence(self, client, result: PlanExecuteResult) -> float:
        if not result.results_per_step:
            return 0.0
        conf_messages = [
            {"role": "system", "content": "Rate confidence in the plan execution outcome on a scale of 0.0 to 1.0. Reply with just a number."},
            {"role": "user", "content": (
                f"Query: {self.user_message}\n"
                f"Steps executed: {result.steps_executed}\n"
                f"Tool calls: {result.total_tool_calls}\n"
                f"Replans: {result.replans_made}\n"
                "Confidence score (0.0-1.0):"
            )},
        ]
        resp = await _call_llm(client, self.model, conf_messages, 0.1)
        self._accumulate_tokens(resp)
        text = resp.choices[0].message.content or "0.5"
        try:
            return float(text.strip())
        except ValueError:
            return 0.5
