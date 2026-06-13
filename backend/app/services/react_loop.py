import time
import json
import logging
import asyncio
from typing import Any, Optional
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.tool_executor import execute_tool, AVAILABLE_TOOLS_SCHEMA
from app.services.llm_router import get_llm_client
from app.services.agent_cost_tracker import calculate_token_cost
from app.services.agent_budget import check_running_budget

logger = logging.getLogger(__name__)

# --- LLM calling helpers ---

async def _call_llm(client, model: str, messages: list, temperature: float, response_format: Optional[dict] = None):
    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format:
        kwargs["response_format"] = response_format
    return await client.chat.completions.create(**kwargs)

async def _call_llm_with_tools(client, model: str, messages: list, tools: list, temperature: float):
    return await client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        temperature=temperature,
    )


# --- Data classes ---

@dataclass
class ReActStep:
    step_number: int
    thought: str = ""
    action_name: Optional[str] = None
    action_args: Optional[dict] = None
    observation: Optional[str] = None
    reflection: str = ""
    decision: str = ""  # "CONTINUE" or "ANSWER"


@dataclass
class ReActResult:
    steps: list[ReActStep] = field(default_factory=list)
    final_answer: str = ""
    total_iterations: int = 0
    total_tool_calls: int = 0
    total_tokens_used: int = 0
    confidence_score: float = 0.0
    execution_summary: str = ""
    status: str = "success"  # success, paused, failed
    approval_id: Optional[str] = None


# --- Main ReAct Loop class ---

class ReActLoop:
    """
    Implements the full ReAct (Reasoning + Acting) pattern:
      THOUGHT -> ACTION (tool_call) -> OBSERVATION -> REFLECTION -> ... -> ANSWER
    """

    def __init__(
        self,
        db: AsyncSession,
        agent,
        user_message: str,
        tools: list,
        model: str,
        temperature: float = 0.3,
        conversation: Optional[list] = None,
        user_payload: Optional[dict] = None,
    ):
        self.db = db
        self.agent = agent
        self.user_message = user_message
        self.tools = tools or []
        self.model = model
        self.temperature = temperature
        self._token_count = 0
        self.conversation = conversation
        self.user_payload = user_payload or {}

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    async def run(self, max_iterations: int = 10) -> ReActResult:
        result = ReActResult()

        if self.conversation is None:
            self.conversation = []
            system_msg = self._build_system_prompt()
            self.conversation.append({"role": "system", "content": system_msg})
            self.conversation.append({"role": "user", "content": self.user_message})

        client, _ = await get_llm_client(self.model, self.agent, self.db)

        for iteration in range(1, max_iterations + 1):
            step = ReActStep(step_number=iteration)

            # --- THOUGHT ---
            step.thought = await self._generate_thought(client, self.conversation)

            # --- ACTION ---
            tool_response = await self._decide_and_execute_action(client, self.conversation, step)
            result.total_tool_calls += 1 if step.action_name else 0

            # --- CHECK FOR APPROVAL SUSPENSION ---
            if step.action_name is not None and step.observation:
                try:
                    obs_json = json.loads(step.observation)
                    if isinstance(obs_json, dict) and obs_json.get("status") == "pending_approval":
                        result.status = "paused"
                        result.approval_id = obs_json.get("approval_id")
                        # Preserve the thought and the planned tool call in history
                        self.conversation.append({
                            "role": "assistant",
                            "content": f"Thought: {step.thought}\nAction: call {step.action_name} with args {json.dumps(step.action_args)}"
                        })
                        result.steps.append(step)
                        return result
                except Exception:
                    pass

            # --- OBSERVATION & REFLECTION ---
            if step.action_name is not None:
                self.conversation.append({
                    "role": "assistant",
                    "content": f"[Tool: {step.action_name}({json.dumps(step.action_args or {})}) returned: {step.observation}]",
                })
                step.reflection, step.decision = await self._reflect_on_observation(
                    client, step.observation or "", step.thought
                )
            else:
                step.decision = "ANSWER"
                step.reflection = "Ready to synthesize final answer."

            result.steps.append(step)

            if step.decision == "ANSWER":
                break

            # --- BUDGET CHECK ---
            prompt_tok = int(self._token_count * 0.6)
            comp_tok = int(self._token_count * 0.4)
            running_cost = calculate_token_cost(self.model, prompt_tok, comp_tok)
            should_abort = await check_running_budget(self.agent.id, running_cost, self.db)
            if should_abort:
                logger.warning(f"Aborting ReAct loop for agent {self.agent.id} due to budget limits.")
                step.decision = "ANSWER"
                step.reflection = "Budget limit reached. Synthesizing partial answer."
                break

        # --- SYNTHESIZE ANSWER ---
        result.final_answer = await self._synthesize_answer(client, result.steps)
        result.total_iterations = len(result.steps)
        result.total_tokens_used = self._token_count
        result.confidence_score = await self._estimate_confidence(client, result.steps)
        result.execution_summary = self._build_summary(result)
        result.status = "success"

        return result

    async def run_stream(self, max_iterations: int = 10):
        if self.conversation is None:
            self.conversation = []
            system_msg = self._build_system_prompt()
            self.conversation.append({"role": "system", "content": system_msg})
            self.conversation.append({"role": "user", "content": self.user_message})

        client, _ = await get_llm_client(self.model, self.agent, self.db)

        steps = []
        for iteration in range(1, max_iterations + 1):
            step = ReActStep(step_number=iteration)

            # --- THOUGHT ---
            step.thought = await self._generate_thought(client, self.conversation)
            yield {"event": "react_thought", "data": step.thought}

            # --- ACTION ---
            tool_response = await self._decide_and_execute_action(client, self.conversation, step)
            if step.action_name:
                yield {"event": "react_action", "data": {"name": step.action_name, "args": step.action_args}}

            # --- CHECK FOR APPROVAL SUSPENSION ---
            if step.action_name is not None and step.observation:
                try:
                    obs_json = json.loads(step.observation)
                    if isinstance(obs_json, dict) and obs_json.get("status") == "pending_approval":
                        self.conversation.append({
                            "role": "assistant",
                            "content": f"Thought: {step.thought}\nAction: call {step.action_name} with args {json.dumps(step.action_args)}"
                        })
                        yield {"event": "status", "data": "paused"}
                        yield {"event": "paused", "data": {"approval_id": obs_json.get("approval_id")}}
                        return
                except Exception:
                    pass

            # --- OBSERVATION & REFLECTION ---
            if step.action_name is not None:
                yield {"event": "react_observation", "data": step.observation}
                self.conversation.append({
                    "role": "assistant",
                    "content": f"[Tool: {step.action_name}({json.dumps(step.action_args or {})}) returned: {step.observation}]",
                })
                step.reflection, step.decision = await self._reflect_on_observation(
                    client, step.observation or "", step.thought
                )
            else:
                step.decision = "ANSWER"
                step.reflection = "Ready to synthesize final answer."

            steps.append(step)

            if step.decision == "ANSWER":
                break

            # --- BUDGET CHECK ---
            prompt_tok = int(self._token_count * 0.6)
            comp_tok = int(self._token_count * 0.4)
            running_cost = calculate_token_cost(self.model, prompt_tok, comp_tok)
            should_abort = await check_running_budget(self.agent.id, running_cost, self.db)
            if should_abort:
                logger.warning(f"Aborting ReAct loop for agent {self.agent.id} due to budget limits.")
                step.decision = "ANSWER"
                step.reflection = "Budget limit reached. Synthesizing partial answer."
                yield {"event": "status", "data": "budget_exceeded_aborting"}
                break

        # --- SYNTHESIZE ANSWER (STREAMED) ---
        yield {"event": "status", "data": "synthesizing"}
        
        if not steps:
            yield {"event": "token", "data": "No steps were taken."}
            yield {"event": "done", "data": ""}
            return

        last_step = steps[-1]
        if last_step.action_name is None and last_step.observation:
            final_text = last_step.observation
            for token in final_text.split(" "):
                yield {"event": "token", "data": token + " "}
                await asyncio.sleep(0.01)
            yield {"event": "done", "data": ""}
            return

        trace_text = ""
        for s in steps:
            trace_text += f"\nStep {s.step_number}: Thought={s.thought[:200]}"
            if s.action_name:
                trace_text += f", Action={s.action_name}, Observation={s.observation[:200]}"
            trace_text += f", Reflection={s.reflection[:200]}"

        synth_messages = [
            {"role": "system", "content": (
                "You are a synthesis engine. Combine all reasoning steps into a coherent, helpful final answer "
                "for the user. Be thorough but concise. Format your reply as markdown if appropriate.\n"
                "CRITICAL: If your answer relies on documents or knowledge chunks retrieved via tools, "
                "you MUST ground your output by citing the specific chunk or document ID using the format [Source: <id>]. "
                "Place these citations inline exactly where the information is used."
            )},
            {"role": "user", "content": (
                f"User query: {self.user_message}\n\n"
                f"Reasoning trace:\n{trace_text}\n\n"
                "Provide the final answer to the user now."
            )},
        ]
        
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
            logger.error(f"Error streaming synthesis: {e}")
            yield {"event": "token", "data": f"Error during synthesis: {e}"}

        yield {"event": "done", "data": ""}


    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        tool_names = [t.get("function", {}).get("name", "") for t in self.tools]
        return (
            f"{self.agent.ai_system_prompt}\n\n"
            "You are operating in ReAct (Reasoning + Acting) mode.\n"
            "Before taking any action, think step-by-step about what the user needs and what information you require.\n"
            f"Available tools: {', '.join(tool_names) if tool_names else 'None'}.\n"
            "For each iteration, state your thought, then decide to call a tool or provide a final answer."
        )

    async def _generate_thought(self, client, messages: list) -> str:
        thought_messages = messages + [{
            "role": "user",
            "content": (
                "Based on the conversation so far and your available tools, "
                "what should you do next? Think step by step. "
                "Consider what information you already have, what you need, "
                "and whether a tool call is necessary."
            ),
        }]
        resp = await _call_llm(client, self.model, thought_messages, self.temperature)
        self._accumulate_tokens(resp)
        return resp.choices[0].message.content or ""

    async def _decide_and_execute_action(self, client, messages: list, step: ReActStep) -> Any:
        action_messages = messages + [{
            "role": "user",
            "content": (
                "Based on your thought process, decide whether to call a tool or give a final answer. "
                "If a tool is needed, call it. If you can answer now, respond with text only."
            ),
        }]

        if self.tools:
            resp = await _call_llm_with_tools(client, self.model, action_messages, self.tools, self.temperature)
        else:
            resp = await _call_llm(client, self.model, action_messages, self.temperature)

        self._accumulate_tokens(resp)
        choice = resp.choices[0]
        msg = choice.message

        if msg.tool_calls:
            if len(msg.tool_calls) == 1:
                tool = msg.tool_calls[0]
                step.action_name = tool.function.name
                step.action_args = json.loads(tool.function.arguments or "{}")
                try:
                    step.observation = await execute_tool(self.db, step.action_name, step.action_args, user_payload=self.user_payload)
                except Exception as exc:
                    step.observation = f"Error: {str(exc)}"
            else:
                tool_names = []
                tool_args = []
                tasks = []
                for tool in msg.tool_calls:
                    name = tool.function.name
                    args = json.loads(tool.function.arguments or "{}")
                    tool_names.append(name)
                    tool_args.append(args)
                    tasks.append(execute_tool(self.db, name, args, user_payload=self.user_payload))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                obs_list = []
                pending_approval_obs = None
                for name, res in zip(tool_names, results):
                    if isinstance(res, Exception):
                        obs_list.append(f"[{name}] Error: {str(res)}")
                    else:
                        obs_list.append(f"[{name}] Result: {res}")
                        try:
                            # Check if any tool triggered pending_approval
                            res_json = json.loads(res)
                            if isinstance(res_json, dict) and res_json.get("status") == "pending_approval":
                                pending_approval_obs = res
                        except Exception:
                            pass
                
                step.action_name = "Parallel Execution: " + ", ".join(tool_names)
                step.action_args = {"parallel_calls": tool_args}
                # If any tool requires approval, we yield its pending state so the loop pauses
                if pending_approval_obs:
                    step.observation = pending_approval_obs
                else:
                    step.observation = "\n".join(obs_list)
            return resp
        else:
            step.action_name = None
            step.action_args = None
            step.observation = msg.content or ""
            return resp

    async def _reflect_on_observation(self, client, observation: str, previous_thought: str) -> tuple:
        supports_json_schema = self.model.startswith("gpt-") or self.model.startswith("o1") or self.model.startswith("o3")
        
        system_msg = "You are a reflective reasoning engine. Analyse the results of executed actions."
        user_msg = (
            f"Previous thought: {previous_thought}\n\n"
            f"Tool result / observation: {observation}\n\n"
            "What did you learn from this observation? "
            "Do you need to take another action (reply CONTINUE) or are you ready to answer (reply ANSWER)?"
        )
        
        response_format = None
        if supports_json_schema:
            user_msg += "\nRespond with a JSON object containing 'decision' (CONTINUE or ANSWER) and 'reflection' (string)."
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "reflection_schema",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "decision": {"type": "string", "enum": ["CONTINUE", "ANSWER"]},
                            "reflection": {"type": "string"}
                        },
                        "required": ["decision", "reflection"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            }
        else:
            user_msg += "\nRespond with:\nDECISION: CONTINUE|ANSWER\nREFLECTION: <your reasoning>"

        reflect_messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]
        
        resp = await _call_llm(client, self.model, reflect_messages, self.temperature, response_format=response_format)
        self._accumulate_tokens(resp)
        text = resp.choices[0].message.content or ""
        
        decision = "ANSWER"
        reflection = text
        
        if supports_json_schema:
            try:
                data = json.loads(text)
                decision = data.get("decision", "ANSWER").upper()
                reflection = data.get("reflection", text)
            except Exception:
                pass
        else:
            for line in text.split("\n"):
                stripped = line.strip()
                if stripped.upper().startswith("DECISION:"):
                    decision_str = stripped.split(":", 1)[1].strip().upper()
                    if decision_str in ("CONTINUE", "ANSWER"):
                        decision = decision_str
                elif stripped.upper().startswith("REFLECTION:"):
                    reflection = stripped.split(":", 1)[1].strip()
                    
        return reflection, decision

    async def _synthesize_answer(self, client, steps: list) -> str:
        if not steps:
            return "No steps were taken."

        last_step = steps[-1]
        if last_step.action_name is None and last_step.observation:
            return last_step.observation

        trace_text = ""
        for s in steps:
            trace_text += f"\nStep {s.step_number}: Thought={s.thought[:200]}"
            if s.action_name:
                trace_text += f", Action={s.action_name}, Observation={s.observation[:200]}"
            trace_text += f", Reflection={s.reflection[:200]}"

        synth_messages = [
            {"role": "system", "content": (
                "You are a synthesis engine. Combine all reasoning steps into a coherent, helpful final answer "
                "for the user. Be thorough but concise. Format your reply as markdown if appropriate.\n"
                "CRITICAL: If your answer relies on documents or knowledge chunks retrieved via tools, "
                "you MUST ground your output by citing the specific chunk or document ID using the format [Source: <id>]. "
                "Place these citations inline exactly where the information is used."
            )},
            {"role": "user", "content": (
                f"User query: {self.user_message}\n\n"
                f"Reasoning trace:\n{trace_text}\n\n"
                "Provide the final answer to the user now."
            )},
        ]
        resp = await _call_llm(client, self.model, synth_messages, max(self.temperature, 0.5))
        self._accumulate_tokens(resp)
        return resp.choices[0].message.content or ""

    async def _estimate_confidence(self, client, steps: list) -> float:
        if not steps:
            return 0.0
        conf_messages = [
            {"role": "system", "content": "Rate confidence in your answer on a scale of 0.0 to 1.0. Reply with just a number."},
            {"role": "user", "content": (
                f"User query: {self.user_message}\n"
                f"Steps taken: {len(steps)}\n"
                f"Tools used: {sum(1 for s in steps if s.action_name)}\n"
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

    def _build_summary(self, result: ReActResult) -> str:
        return (
            f"ReAct execution completed in {result.total_iterations} iteration(s) "
            f"with {result.total_tool_calls} tool call(s). "
            f"Confidence: {result.confidence_score:.2f}."
        )

    def _accumulate_tokens(self, response) -> None:
        usage = response.usage
        if usage:
            self._token_count += usage.prompt_tokens or 0
            self._token_count += usage.completion_tokens or 0
