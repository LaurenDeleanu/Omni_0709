import json
import time
import logging
import asyncio
from typing import Any, Optional
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.services.llm_router import get_llm_client

logger = logging.getLogger(__name__)

NEGOTIATION_SCENARIOS = {
    "SCHEDULING": "Schedule a meeting for 4 executives with conflicting calendars. Each executive has their own scheduling agent representing their availability and preferences.",
    "BUDGET_ALLOCATION": "Allocate Q3 budget across Engineering, Sales, and Marketing departments. Each department has an agent advocating for their resource needs and priorities.",
    "POLICY_DRAFTING": "Draft a new remote work policy for the organization. HR, Legal, and Operations agents negotiate the terms including hybrid schedules, compliance requirements, and operational feasibility.",
    "CONTRACT_NEGOTIATION": "Negotiate vendor contract terms for a major software procurement. The Procurement agent negotiates with the Vendor agent on pricing, SLAs, data privacy, and termination clauses.",
}

ROUND_PROMPTS = {
    1: """You are an AI agent serving as a {agent_role} in a multi-agent negotiation on the topic:
"{topic}"

This is Round 1: Position Statements.

State your agent's **position** clearly. Include:
1. Your desired outcome
2. Your constraints (what you cannot compromise on)
3. Your red lines (deal-breakers)
4. Any initial concessions you are willing to make

Respond in the following JSON format exactly:
{{
  "agent_role": "{agent_role}",
  "round": 1,
  "position": "Your primary position and goals",
  "desired_outcome": "What you ideally want to achieve",
  "constraints": ["constraint 1", "constraint 2"],
  "red_lines": ["red line 1", "red line 2"],
  "concessions_offered": ["concession 1"],
  "counter_proposal": null
}}""",

    2: """You are an AI agent serving as a {agent_role} in a multi-agent negotiation on the topic:
"{topic}"

This is Round 2: Counter-Proposals.

Previous round positions from other agents:
{previous_rounds_context}

Based on the other agents' positions, respond with:
1. Your counter-proposal (what you accept, what you reject, and what you propose instead)
2. New or adjusted concessions you are willing to make
3. Any adjustments to your red lines based on what you've heard

Respond in the following JSON format exactly:
{{
  "agent_role": "{agent_role}",
  "round": 2,
  "position": "Your updated primary position",
  "desired_outcome": "Your refined desired outcome",
  "constraints": ["constraint 1"],
  "red_lines": ["red line 1"],
  "concessions_offered": ["concession 1", "concession 2"],
  "counter_proposal": "Your specific counter-proposal addressing other agents' positions"
}}""",

    3: """You are an AI agent serving as a {agent_role} in a multi-agent negotiation on the topic:
"{topic}"

This is Round 3: Refinement.

All positions so far:
{previous_rounds_context}

Seek common ground. Refine your position to:
1. Identify areas where you can agree with other agents
2. Propose a compromise position that addresses the key concerns of all parties
3. Specify any remaining non-negotiable points with justification

Respond in the following JSON format exactly:
{{
  "agent_role": "{agent_role}",
  "round": 3,
  "position": "Your refined position seeking common ground",
  "desired_outcome": "Your compromise-oriented desired outcome",
  "constraints": ["remaining constraint"],
  "red_lines": ["remaining red line with justification"],
  "concessions_offered": ["compromise concession 1", "compromise concession 2"],
  "counter_proposal": "Your compromise proposal bridging agent positions"
}}""",

    4: """You are an AI agent serving as a {agent_role} in a multi-agent negotiation on the topic:
"{topic}"

This is Round 4: Consensus Check.

All positions across all rounds:
{previous_rounds_context}

Cast your final vote on the negotiation:
- ACCEPT: If you agree with the emerging consensus
- REJECT: If you cannot accept the current terms
- CONDITIONAL: If you would accept with specific modifications

Provide your vote and reasoning.

Respond in the following JSON format exactly:
{{
  "agent_role": "{agent_role}",
  "round": 4,
  "position": "Your final position",
  "desired_outcome": "Your final desired outcome",
  "constraints": [],
  "red_lines": [],
  "concessions_offered": [],
  "counter_proposal": null,
  "vote": "ACCEPT|REJECT|CONDITIONAL",
  "vote_reasoning": "Detailed reasoning for your vote",
  "conditions": ["condition 1"] 
}}""",
}


@dataclass
class NegotiationResult:
    final_agreement: dict = field(default_factory=dict)
    consensus_reached: bool = False
    rounds_run: int = 0
    agent_positions: list = field(default_factory=list)
    deadlock_points: list = field(default_factory=list)
    suggested_mediator: str = ""
    total_cost_usd: float = 0.0
    total_tokens: int = 0


class AgentNegotiationProtocol:

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self._total_tokens = 0
        self._total_cost = 0.0

    async def negotiate(
        self,
        topic: str,
        agent_configs: list[dict],
        user_id: str,
        db: AsyncSession,
        max_rounds: int = 5,
        timeout_seconds: int = 120,
    ) -> NegotiationResult:
        if len(agent_configs) < 2:
            return NegotiationResult(
                consensus_reached=False,
                rounds_run=0,
                deadlock_points=["Negotiation requires at least 2 agents"],
                suggested_mediator="human",
            )

        all_positions: list[dict] = []
        consensus_reached = False
        deadlock_points: list[str] = []
        suggested_mediator = ""

        try:
            async with asyncio.timeout(timeout_seconds):
                for round_num in range(1, max_rounds + 1):
                    logger.info(f"Negotiation round {round_num}/{max_rounds} for topic: {topic}")

                    round_positions = await asyncio.gather(
                        *[
                            self._generate_position(
                                agent_id=cfg.get("id", cfg.get("name", f"agent_{i}")),
                                agent_role=cfg.get("role", cfg.get("agent_type", "negotiator")),
                                topic=topic,
                                round_number=round_num,
                                previous_rounds=all_positions,
                                db=db,
                            )
                            for i, cfg in enumerate(agent_configs)
                        ],
                        return_exceptions=True,
                    )

                    valid_positions = []
                    for i, pos in enumerate(round_positions):
                        if isinstance(pos, Exception):
                            logger.error(f"Agent {i} failed in round {round_num}: {pos}")
                            valid_positions.append({
                                "agent_role": agent_configs[i].get("role", "unknown"),
                                "round": round_num,
                                "error": str(pos),
                                "position": "Error generating position",
                                "desired_outcome": "",
                                "constraints": [],
                                "red_lines": [],
                                "concessions_offered": [],
                                "counter_proposal": None,
                            })
                        else:
                            valid_positions.append(pos)

                    all_positions.append({"round": round_num, "positions": valid_positions})

                    if round_num == 4:
                        consensus_eval = await self._evaluate_consensus(valid_positions, db)
                        consensus_reached = consensus_eval.get("consensus_reached", False)
                        if not consensus_reached:
                            deadlock_points = consensus_eval.get("deadlock_points", [])
                            suggested_mediator = consensus_eval.get("suggested_mediator_type", "human")

                    if round_num >= 4:
                        break

                if consensus_reached or all_positions:
                    final_agreement = await self._synthesize_agreement(
                        all_positions,
                        [] if consensus_reached else deadlock_points,
                        db,
                    )
                else:
                    final_agreement = {"error": "No positions generated"}

        except asyncio.TimeoutError:
            logger.warning(f"Negotiation timed out after {timeout_seconds}s")
            final_agreement = {
                "preamble": "Negotiation timed out before reaching consensus.",
                "agreed_points": [],
                "unresolved_items": ["All items"],
                "next_steps": ["Re-initiate negotiation with extended timeout"],
            }
            deadlock_points = ["Negotiation timed out"]
            suggested_mediator = "human"
            consensus_reached = False

        return NegotiationResult(
            final_agreement=final_agreement,
            consensus_reached=consensus_reached,
            rounds_run=len(all_positions),
            agent_positions=all_positions,
            deadlock_points=deadlock_points,
            suggested_mediator=suggested_mediator,
            total_cost_usd=round(self._total_cost, 6),
            total_tokens=self._total_tokens,
        )

    async def _generate_position(
        self,
        agent_id: str,
        agent_role: str,
        topic: str,
        round_number: int,
        previous_rounds: list,
        db: AsyncSession,
    ) -> dict:
        prompt_template = ROUND_PROMPTS.get(round_number, ROUND_PROMPTS[1])

        previous_context = ""
        if previous_rounds and round_number > 1:
            for pr in previous_rounds:
                r = pr.get("round", "?")
                positions = pr.get("positions", [])
                previous_context += f"\n--- Round {r} ---\n"
                for p in positions:
                    agent_r = p.get("agent_role", "unknown")
                    pos = p.get("position", "")
                    desired = p.get("desired_outcome", "")
                    constraints = p.get("constraints", [])
                    red_lines = p.get("red_lines", [])
                    concessions = p.get("concessions_offered", [])
                    counter = p.get("counter_proposal", "")
                    previous_context += f"\n[{agent_r}]:\n"
                    previous_context += f"  Position: {pos}\n"
                    previous_context += f"  Desired: {desired}\n"
                    if constraints:
                        previous_context += f"  Constraints: {', '.join(constraints)}\n"
                    if red_lines:
                        previous_context += f"  Red lines: {', '.join(red_lines)}\n"
                    if concessions:
                        previous_context += f"  Concessions: {', '.join(concessions)}\n"
                    if counter:
                        previous_context += f"  Counter-proposal: {counter}\n"

        prompt = prompt_template.format(
            agent_role=agent_role,
            topic=topic,
            previous_rounds_context=previous_context if previous_context else "No previous rounds — this is the first round.",
        )

        try:
            dummy_agent = Agent(
                id=agent_id,
                name=f"Negotiator-{agent_role}",
                agent_type="negotiator",
                ai_model=self.model,
                ai_system_prompt=f"You are a negotiation agent representing {agent_role}.",
                ai_temperature=0.4,
            )
            client, _ = await get_llm_client(self.model, dummy_agent, db)

            response = await client.chat.completions.create(
                model=self.model,
                temperature=0.4,
                messages=[
                    {"role": "system", "content": f"You are a professional negotiation agent representing {agent_role}. Be honest about your constraints and red lines. Seek mutually beneficial outcomes when possible. Always respond with valid JSON."},
                    {"role": "user", "content": prompt},
                ],
            )

            raw = response.choices[0].message.content or "{}"
            usage = response.usage
            if usage:
                self._total_tokens += usage.total_tokens
                self._total_cost += (usage.prompt_tokens * 0.00015 + usage.completion_tokens * 0.0006) / 1000

            result = _parse_json(raw)
            result.setdefault("agent_role", agent_role)
            result.setdefault("round", round_number)
            result.setdefault("position", "No position generated")
            result.setdefault("desired_outcome", "")
            result.setdefault("constraints", [])
            result.setdefault("red_lines", [])
            result.setdefault("concessions_offered", [])
            result.setdefault("counter_proposal", None)
            return result

        except Exception as e:
            logger.error(f"Failed to generate position for {agent_role} in round {round_number}: {e}")
            return {
                "agent_role": agent_role,
                "round": round_number,
                "position": f"Error: {str(e)}",
                "desired_outcome": "",
                "constraints": [],
                "red_lines": [],
                "concessions_offered": [],
                "counter_proposal": None,
                "error": str(e),
            }

    async def _evaluate_consensus(self, positions: list, db: AsyncSession) -> dict:
        positions_text = ""
        for p in positions:
            vote = p.get("vote", "N/A")
            vote_reasoning = p.get("vote_reasoning", "")
            conditions = p.get("conditions", [])
            positions_text += f"\n[{p.get('agent_role', 'unknown')}] Vote: {vote}\n"
            positions_text += f"  Reasoning: {vote_reasoning}\n"
            if conditions:
                positions_text += f"  Conditions: {', '.join(conditions)}\n"

        prompt = f"""Evaluate whether the following negotiation positions have reached consensus.

Agent votes and positions:
{positions_text}

Determine:
1. Has consensus been reached? (all ACCEPT or CONDITIONAL with compatible conditions)
2. What are the areas of agreement?
3. What are the deadlock points (if any)?
4. If no consensus, what type of mediator would be most appropriate?

Respond in JSON:
{{
  "consensus_reached": true/false,
  "areas_of_agreement": ["point 1", "point 2"],
  "deadlock_points": ["deadlock 1"],
  "suggested_mediator_type": "agent_type or human"
}}"""

        try:
            dummy_agent = Agent(
                id="consensus_eval",
                name="ConsensusEvaluator",
                agent_type="evaluator",
                ai_model=self.model,
                ai_system_prompt="Evaluate multi-agent consensus objectively.",
                ai_temperature=0.2,
            )
            client, _ = await get_llm_client(self.model, dummy_agent, db)

            response = await client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": "You are a neutral consensus evaluator. Determine whether agents have reached agreement."},
                    {"role": "user", "content": prompt},
                ],
            )

            raw = response.choices[0].message.content or "{}"
            usage = response.usage
            if usage:
                self._total_tokens += usage.total_tokens
                self._total_cost += (usage.prompt_tokens * 0.00015 + usage.completion_tokens * 0.0006) / 1000

            result = _parse_json(raw)
            result.setdefault("consensus_reached", False)
            result.setdefault("areas_of_agreement", [])
            result.setdefault("deadlock_points", [])
            result.setdefault("suggested_mediator_type", "human")
            return result

        except Exception as e:
            logger.error(f"Failed to evaluate consensus: {e}")
            accept_count = sum(1 for p in positions if p.get("vote") == "ACCEPT")
            reject_count = sum(1 for p in positions if p.get("vote") == "REJECT")
            total = len(positions)
            return {
                "consensus_reached": accept_count >= total * 0.6,
                "areas_of_agreement": [],
                "deadlock_points": [f"Could not evaluate: {str(e)}"],
                "suggested_mediator_type": "human",
            }

    async def _synthesize_agreement(
        self,
        all_positions: list,
        areas_of_agreement: list,
        db: AsyncSession,
    ) -> dict:
        positions_text = ""
        for round_data in all_positions:
            r = round_data.get("round", "?")
            positions_text += f"\n--- Round {r} ---\n"
            for p in round_data.get("positions", []):
                positions_text += f"\n[{p.get('agent_role', 'unknown')}]: {p.get('position', '')}"
                concessions = p.get("concessions_offered", [])
                if concessions:
                    positions_text += f"\n  Concessions: {', '.join(concessions)}"

        areas_text = "\n".join(f"- {a}" for a in areas_of_agreement) if areas_of_agreement else "(no areas of explicit agreement identified)"

        prompt = f"""Synthesize the following multi-agent negotiation into a structured final agreement document.

All negotiation positions across rounds:
{positions_text}

Areas of agreement identified:
{areas_text}

Produce a structured agreement document in JSON format:
{{
  "preamble": "Summary of the agreement reached",
  "agreed_points": [
    {{
      "point": "Specific agreed point",
      "responsible_parties": ["party 1", "party 2"],
      "timeline": "implementation timeline"
    }}
  ],
  "unresolved_items": ["item not resolved"],
  "next_steps": ["step 1", "step 2"]
}}"""

        try:
            dummy_agent = Agent(
                id="agreement_synth",
                name="AgreementSynthesizer",
                agent_type="synthesizer",
                ai_model=self.model,
                ai_system_prompt="Synthesize multi-agent negotiations into structured agreements.",
                ai_temperature=0.3,
            )
            client, _ = await get_llm_client(self.model, dummy_agent, db)

            response = await client.chat.completions.create(
                model=self.model,
                temperature=0.3,
                messages=[
                    {"role": "system", "content": "You are a neutral agreement synthesizer. Produce a structured, fair agreement document from negotiation positions."},
                    {"role": "user", "content": prompt},
                ],
            )

            raw = response.choices[0].message.content or "{}"
            usage = response.usage
            if usage:
                self._total_tokens += usage.total_tokens
                self._total_cost += (usage.prompt_tokens * 0.00015 + usage.completion_tokens * 0.0006) / 1000

            result = _parse_json(raw)
            result.setdefault("preamble", "Agreement synthesized from multi-agent negotiation.")
            result.setdefault("agreed_points", [])
            result.setdefault("unresolved_items", [])
            result.setdefault("next_steps", ["Review agreement with all stakeholders"])
            return result

        except Exception as e:
            logger.error(f"Failed to synthesize agreement: {e}")
            return {
                "preamble": f"Agreement synthesis failed: {str(e)}",
                "agreed_points": [],
                "unresolved_items": ["All items — synthesis error"],
                "next_steps": ["Re-run synthesis or escalate to human review"],
            }


def _parse_json(raw: str) -> dict:
    for _ in range(3):
        try:
            clean = raw[raw.find("{"):raw.rfind("}") + 1]
            return json.loads(clean)
        except (json.JSONDecodeError, ValueError):
            raw = raw.replace("\r\n", "\n")
            lines = raw.split("\n")
            for line in reversed(lines):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    try:
                        return json.loads(line)
                    except Exception:
                        continue
    return {}


async def run_negotiation(
    topic: str,
    agent_configs: list[dict],
    user_id: str,
    db: AsyncSession,
    scenario: str = "",
    max_rounds: int = 5,
    timeout_seconds: int = 120,
) -> NegotiationResult:
    if scenario and scenario in NEGOTIATION_SCENARIOS:
        full_topic = f"{topic}\n\nScenario: {NEGOTIATION_SCENARIOS[scenario]}"
    else:
        full_topic = topic

    protocol = AgentNegotiationProtocol()
    return await protocol.negotiate(
        topic=full_topic,
        agent_configs=agent_configs,
        user_id=user_id,
        db=db,
        max_rounds=max_rounds,
        timeout_seconds=timeout_seconds,
    )
