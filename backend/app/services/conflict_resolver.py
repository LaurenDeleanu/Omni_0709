import json
import logging
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.services.llm_router import get_llm_client

logger = logging.getLogger(__name__)

CONFLICT_DETECTION_PROMPT = """You are a conflict detection engine. Analyze the outputs of multiple agents that addressed the same task independently.

Below are the results from {num_agents} agents:
{agent_results_text}

Identify disagreements between agents. There are three conflict types:
1. **factual_disagreement**: Same data interpreted differently — agents cite the same facts but draw opposite conclusions
2. **value_conflict**: Different priorities or values — agents disagree on what matters most
3. **methodological_difference**: Different approaches to the same problem — agents use incompatible methods

For each conflict found, return:
- The type of conflict
- Which agent holds which view
- A divergence score (0.0 = identical views, 1.0 = completely opposite)
- The specific data points in dispute

Return JSON:
{{
  "conflicts": [
    {{
      "type": "factual_disagreement|value_conflict|methodological_difference",
      "agent_a_view": "Agent A's position",
      "agent_b_view": "Agent B's position",
      "agent_a_id": "agent identifier",
      "agent_b_id": "agent identifier",
      "divergence_score": 0.75,
      "data_cited": ["specific data point 1", "specific data point 2"],
      "description": "Brief description of the conflict"
    }}
  ]
}}

Only report genuine conflicts. Ignore minor word choice differences or formatting variations. If agents fundamentally agree, return an empty conflicts array."""


VOTING_RESOLUTION_PROMPT = """You are resolving a factual dispute identified between multiple agents.

Conflict: {conflict_description}

Agent votes on this point:
{agent_votes}

As a fair vote-counter, determine:
1. The majority position
2. Whether the majority is convincing (supermajority > 60%)
3. The resolved answer

Return JSON:
{{
  "resolved": true/false,
  "resolution": "The resolved answer",
  "majority_count": N,
  "total_agents": N,
  "confidence": 0.85,
  "method": "voting"
}}"""


MEDIATOR_RESOLUTION_PROMPT = """You are a neutral mediator resolving a value conflict between AI agents.

Conflict description: {conflict_description}

Agent A ({agent_a}) position: {agent_a_view}
Agent B ({agent_b}) position: {agent_b_view}

As a neutral arbitrator, analyze both positions and decide:
1. Which position (or compromise) is most justified
2. Your reasoning
3. A resolution that acknowledges both perspectives

Return JSON:
{{
  "resolved": true/false,
  "resolution": "The mediated resolution",
  "reasoning": "Your reasoning for this decision",
  "confidence": 0.80,
  "method": "mediator",
  "compromise_points": ["point 1"]
}}"""


CONSENSUS_BUILDING_PROMPT = """You are facilitating consensus on a methodological difference between AI agents.

Conflict description: {conflict_description}

Agent A ({agent_a}) approach: {agent_a_view}
Agent B ({agent_b}) approach: {agent_b_view}

Find common methodological ground:
1. What aspects of each approach are complementary rather than contradictory?
2. Can the approaches be combined, sequenced, or conditionally applied?
3. What hybrid methodology would satisfy both agents?

Return JSON:
{{
  "resolved": true/false,
  "resolution": "The consensus methodology",
  "complementary_aspects": ["aspect 1"],
  "hybrid_approach": "Description of combined approach",
  "confidence": 0.80,
  "method": "consensus"
}}"""


REPORT_PROMPT = """Generate a human-readable conflict resolution report based on the following data.

Conflicts detected: {num_conflicts}
Resolutions: {num_resolved} resolved, {num_unresolved} unresolved

Details:
{details_text}

Write a concise, professional summary paragraph in plain English (no markdown) that:
1. States how many conflicts were detected between the agents
2. For each conflict, describes the nature, the resolution method used, and the outcome
3. Clearly flags any items that require human review

Report:"""


@dataclass
class ConflictPoint:
    type: str
    agent_a_view: str
    agent_b_view: str
    agent_a_id: str = ""
    agent_b_id: str = ""
    divergence_score: float = 0.0
    data_cited: list = field(default_factory=list)
    description: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ResolutionResult:
    resolved: list = field(default_factory=list)
    unresolved: list = field(default_factory=list)
    resolution_methods: dict = field(default_factory=dict)
    human_review_needed: bool = False
    confidence: float = 0.0
    details: list = field(default_factory=list)


class ConflictResolver:

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model

    async def detect_conflicts(self, agent_results: list[dict]) -> list[ConflictPoint]:
        if len(agent_results) < 2:
            return []

        agent_results_text = ""
        for i, r in enumerate(agent_results):
            agent_name = r.get("agent_type", r.get("agent_id", f"Agent {i + 1}"))
            result_text = r.get("result", r.get("output", ""))
            agent_results_text += f"\n--- Agent: {agent_name} ---\n{result_text}\n"

        prompt = CONFLICT_DETECTION_PROMPT.format(
            num_agents=len(agent_results),
            agent_results_text=agent_results_text,
        )

        try:
            from app.services.llm_router import get_llm_client
            dummy_agent = Agent(
                id="conflict_detector",
                name="ConflictDetector",
                agent_type="analyst",
                ai_model=self.model,
                ai_system_prompt="Detect factual, value, and methodological conflicts between agent outputs.",
                ai_temperature=0.1,
            )
            client, _ = await get_llm_client(self.model, dummy_agent, None)

            response = await client.chat.completions.create(
                model=self.model,
                temperature=0.1,
                messages=[
                    {"role": "system", "content": "You are a conflict detection engine. Only report genuine, meaningful disagreements."},
                    {"role": "user", "content": prompt},
                ],
            )

            raw = response.choices[0].message.content or "{}"
            data = _parse_json(raw)
            conflicts_raw = data.get("conflicts", [])

            conflicts = []
            for c in conflicts_raw:
                conflicts.append(ConflictPoint(
                    type=c.get("type", "factual_disagreement"),
                    agent_a_view=str(c.get("agent_a_view", "")),
                    agent_b_view=str(c.get("agent_b_view", "")),
                    agent_a_id=str(c.get("agent_a_id", "")),
                    agent_b_id=str(c.get("agent_b_id", "")),
                    divergence_score=float(c.get("divergence_score", 0.5)),
                    data_cited=c.get("data_cited", []),
                    description=str(c.get("description", "")),
                ))

            logger.info(f"Detected {len(conflicts)} conflicts among {len(agent_results)} agents")
            return conflicts

        except Exception as e:
            logger.error(f"Conflict detection failed: {e}")

            fallback = []
            if len(agent_results) >= 2:
                texts = []
                for r in agent_results:
                    t = r.get("result", r.get("output", ""))
                    if t:
                        texts.append(t)

                if len(texts) >= 2:
                    sim_score = _compute_jaccard_similarity(texts[0], texts[1])
                    if sim_score < 0.4:
                        fallback.append(ConflictPoint(
                            type="methodological_difference",
                            agent_a_view=texts[0][:200],
                            agent_b_view=texts[1][:200],
                            divergence_score=round(1.0 - sim_score, 2),
                            description="Low text similarity detected between agent outputs",
                        ))

            return fallback

    async def resolve_conflicts(
        self,
        conflict_points: list[ConflictPoint],
        resolution_strategy: str = "auto",
        db: AsyncSession | None = None,
    ) -> ResolutionResult:
        if not conflict_points:
            return ResolutionResult(
                resolved=[],
                unresolved=[],
                resolution_methods={},
                human_review_needed=False,
                confidence=1.0,
            )

        if resolution_strategy == "auto":
            return await self.auto_resolve(conflict_points, db)
        elif resolution_strategy == "voting":
            return await self._resolve_voting(conflict_points, db)
        elif resolution_strategy == "mediator":
            return await self._resolve_mediator(conflict_points, db)
        elif resolution_strategy == "escalate":
            unresolved = [
                {
                    "type": c.type,
                    "description": c.description,
                    "agent_a_view": c.agent_a_view,
                    "agent_b_view": c.agent_b_view,
                    "divergence_score": c.divergence_score,
                }
                for c in conflict_points
            ]
            return ResolutionResult(
                resolved=[],
                unresolved=unresolved,
                resolution_methods={"all": "escalated_to_human"},
                human_review_needed=True,
                confidence=0.0,
            )
        else:
            return await self.auto_resolve(conflict_points, db)

    async def auto_resolve(
        self,
        conflict_points: list[ConflictPoint],
        db: AsyncSession | None = None,
    ) -> ResolutionResult:
        resolved = []
        unresolved = []
        resolution_methods = {}
        all_details = []

        factual_conflicts = [c for c in conflict_points if c.type == "factual_disagreement"]
        value_conflicts = [c for c in conflict_points if c.type == "value_conflict"]
        method_conflicts = [c for c in conflict_points if c.type == "methodological_difference"]
        other_conflicts = [c for c in conflict_points if c.type not in ("factual_disagreement", "value_conflict", "methodological_difference")]

        if factual_conflicts:
            try:
                voting_result = await self._resolve_voting(factual_conflicts, db)
                resolved.extend(voting_result.resolved)
                unresolved.extend(voting_result.unresolved)
                resolution_methods.update(voting_result.resolution_methods)
                all_details.extend(voting_result.details)
            except Exception as e:
                logger.error(f"Voting resolution failed for factual conflicts: {e}")
                for c in factual_conflicts:
                    unresolved.append({
                        "type": c.type,
                        "description": c.description,
                        "agent_a_view": c.agent_a_view,
                        "agent_b_view": c.agent_b_view,
                        "divergence_score": c.divergence_score,
                        "error": str(e),
                    })

        if value_conflicts:
            try:
                mediator_result = await self._resolve_mediator(value_conflicts, db)
                resolved.extend(mediator_result.resolved)
                unresolved.extend(mediator_result.unresolved)
                resolution_methods.update(mediator_result.resolution_methods)
                all_details.extend(mediator_result.details)
            except Exception as e:
                logger.error(f"Mediator resolution failed for value conflicts: {e}")
                for c in value_conflicts:
                    unresolved.append({
                        "type": c.type,
                        "description": c.description,
                        "agent_a_view": c.agent_a_view,
                        "agent_b_view": c.agent_b_view,
                        "divergence_score": c.divergence_score,
                        "error": str(e),
                    })

        if method_conflicts:
            try:
                consensus_result = await self._resolve_consensus(method_conflicts, db)
                resolved.extend(consensus_result.resolved)
                unresolved.extend(consensus_result.unresolved)
                resolution_methods.update(consensus_result.resolution_methods)
                all_details.extend(consensus_result.details)
            except Exception as e:
                logger.error(f"Consensus resolution failed for methodological conflicts: {e}")
                for c in method_conflicts:
                    unresolved.append({
                        "type": c.type,
                        "description": c.description,
                        "agent_a_view": c.agent_a_view,
                        "agent_b_view": c.agent_b_view,
                        "divergence_score": c.divergence_score,
                        "error": str(e),
                    })

        for c in other_conflicts:
            unresolved.append({
                "type": c.type,
                "description": c.description,
                "agent_a_view": c.agent_a_view,
                "agent_b_view": c.agent_b_view,
                "divergence_score": c.divergence_score,
            })
            resolution_methods.setdefault(c.type, "escalated_to_human")

        confidence = 0.0
        total = len(conflict_points)
        if total > 0:
            resolved_confidence = sum(r.get("confidence", 0.5) for r in resolved)
            confidence = resolved_confidence / total if resolved else 0.0

        human_review_needed = len(unresolved) > 0 or any(
            r.get("confidence", 0) < 0.7 for r in resolved
        )

        if human_review_needed and not unresolved:
            for r in resolved:
                if r.get("confidence", 0) < 0.7:
                    unresolved.append(r)

        return ResolutionResult(
            resolved=resolved,
            unresolved=unresolved,
            resolution_methods=resolution_methods,
            human_review_needed=human_review_needed,
            confidence=round(confidence, 3),
            details=all_details,
        )

    async def _resolve_voting(
        self,
        conflict_points: list[ConflictPoint],
        db: AsyncSession | None = None,
    ) -> ResolutionResult:
        resolved = []
        unresolved = []
        methods = {}
        details = []

        for cp in conflict_points:
            try:
                client = None
                if db is not None:
                    dummy_agent = Agent(
                        id="voting_resolver",
                        name="VotingResolver",
                        agent_type="analyst",
                        ai_model=self.model,
                        ai_system_prompt="Resolve factual disputes via voting.",
                        ai_temperature=0.1,
                    )
                    client, _ = await get_llm_client(self.model, dummy_agent, db)
                else:
                    from app.services.llm_router import get_llm_client
                    client, _ = await get_llm_client(self.model)

                votes_text = f"Agent A ({cp.agent_a_id or 'A'}): {cp.agent_a_view}\nAgent B ({cp.agent_b_id or 'B'}): {cp.agent_b_view}"

                prompt = VOTING_RESOLUTION_PROMPT.format(
                    conflict_description=cp.description or f"{cp.agent_a_view[:100]} vs {cp.agent_b_view[:100]}",
                    agent_votes=votes_text,
                )

                response = await client.chat.completions.create(
                    model=self.model,
                    temperature=0.1,
                    messages=[
                        {"role": "system", "content": "Resolve factual disputes by counting agent votes and determining the majority position."},
                        {"role": "user", "content": prompt},
                    ],
                )

                raw = response.choices[0].message.content or "{}"
                result = _parse_json(raw)

                resolution_entry = {
                    "type": cp.type,
                    "description": cp.description,
                    "resolution": result.get("resolution", "No resolution"),
                    "method": "voting",
                    "confidence": float(result.get("confidence", 0.5)),
                }

                if result.get("resolved", True) and result.get("confidence", 0) >= 0.7:
                    resolved.append(resolution_entry)
                else:
                    unresolved.append(resolution_entry)

                methods[cp.type] = "voting"
                details.append(resolution_entry)

            except Exception as e:
                logger.error(f"Voting resolution failed for conflict: {e}")
                unresolved.append({
                    "type": cp.type,
                    "description": cp.description,
                    "resolution": f"Voting resolution error: {str(e)}",
                    "method": "voting",
                    "confidence": 0.0,
                })

        return ResolutionResult(
            resolved=resolved,
            unresolved=unresolved,
            resolution_methods=methods,
            human_review_needed=len(unresolved) > 0,
            confidence=_avg_confidence(resolved),
            details=details,
        )

    async def _resolve_mediator(
        self,
        conflict_points: list[ConflictPoint],
        db: AsyncSession | None = None,
    ) -> ResolutionResult:
        resolved = []
        unresolved = []
        methods = {}
        details = []

        for cp in conflict_points:
            try:
                client = None
                if db is not None:
                    dummy_agent = Agent(
                        id="mediator",
                        name="NeutralMediator",
                        agent_type="mediator",
                        ai_model=self.model,
                        ai_system_prompt="Mediate value conflicts between agents neutrally.",
                        ai_temperature=0.3,
                    )
                    client, _ = await get_llm_client(self.model, dummy_agent, db)
                else:
                    from app.services.llm_router import get_llm_client
                    client, _ = await get_llm_client(self.model)

                prompt = MEDIATOR_RESOLUTION_PROMPT.format(
                    conflict_description=cp.description or "Value conflict between agents",
                    agent_a=cp.agent_a_id or "Agent A",
                    agent_a_view=cp.agent_a_view,
                    agent_b=cp.agent_b_id or "Agent B",
                    agent_b_view=cp.agent_b_view,
                )

                response = await client.chat.completions.create(
                    model=self.model,
                    temperature=0.3,
                    messages=[
                        {"role": "system", "content": "You are a neutral arbitrator for multi-agent conflicts. Weigh both sides fairly and produce a justified resolution."},
                        {"role": "user", "content": prompt},
                    ],
                )

                raw = response.choices[0].message.content or "{}"
                result = _parse_json(raw)

                resolution_entry = {
                    "type": cp.type,
                    "description": cp.description,
                    "resolution": result.get("resolution", "No resolution"),
                    "reasoning": result.get("reasoning", ""),
                    "compromise_points": result.get("compromise_points", []),
                    "method": "mediator",
                    "confidence": float(result.get("confidence", 0.5)),
                }

                if result.get("resolved", True) and result.get("confidence", 0) >= 0.7:
                    resolved.append(resolution_entry)
                else:
                    unresolved.append(resolution_entry)

                methods[cp.type] = "mediator"
                details.append(resolution_entry)

            except Exception as e:
                logger.error(f"Mediator resolution failed for conflict: {e}")
                unresolved.append({
                    "type": cp.type,
                    "description": cp.description,
                    "resolution": f"Mediator error: {str(e)}",
                    "method": "mediator",
                    "confidence": 0.0,
                })

        return ResolutionResult(
            resolved=resolved,
            unresolved=unresolved,
            resolution_methods=methods,
            human_review_needed=len(unresolved) > 0,
            confidence=_avg_confidence(resolved),
            details=details,
        )

    async def _resolve_consensus(
        self,
        conflict_points: list[ConflictPoint],
        db: AsyncSession | None = None,
    ) -> ResolutionResult:
        resolved = []
        unresolved = []
        methods = {}
        details = []

        for cp in conflict_points:
            try:
                client = None
                if db is not None:
                    dummy_agent = Agent(
                        id="consensus_builder",
                        name="ConsensusBuilder",
                        agent_type="facilitator",
                        ai_model=self.model,
                        ai_system_prompt="Build consensus on methodological differences between agents.",
                        ai_temperature=0.3,
                    )
                    client, _ = await get_llm_client(self.model, dummy_agent, db)
                else:
                    from app.services.llm_router import get_llm_client
                    client, _ = await get_llm_client(self.model)

                prompt = CONSENSUS_BUILDING_PROMPT.format(
                    conflict_description=cp.description or "Methodological difference",
                    agent_a=cp.agent_a_id or "Agent A",
                    agent_a_view=cp.agent_a_view,
                    agent_b=cp.agent_b_id or "Agent B",
                    agent_b_view=cp.agent_b_view,
                )

                response = await client.chat.completions.create(
                    model=self.model,
                    temperature=0.3,
                    messages=[
                        {"role": "system", "content": "Find common ground between different methodological approaches. Build consensus by identifying complementarity."},
                        {"role": "user", "content": prompt},
                    ],
                )

                raw = response.choices[0].message.content or "{}"
                result = _parse_json(raw)

                resolution_entry = {
                    "type": cp.type,
                    "description": cp.description,
                    "resolution": result.get("resolution", "No resolution"),
                    "hybrid_approach": result.get("hybrid_approach", ""),
                    "complementary_aspects": result.get("complementary_aspects", []),
                    "method": "consensus",
                    "confidence": float(result.get("confidence", 0.5)),
                }

                if result.get("resolved", True) and result.get("confidence", 0) >= 0.7:
                    resolved.append(resolution_entry)
                else:
                    unresolved.append(resolution_entry)

                methods[cp.type] = "consensus"
                details.append(resolution_entry)

            except Exception as e:
                logger.error(f"Consensus resolution failed for conflict: {e}")
                unresolved.append({
                    "type": cp.type,
                    "description": cp.description,
                    "resolution": f"Consensus error: {str(e)}",
                    "method": "consensus",
                    "confidence": 0.0,
                })

        return ResolutionResult(
            resolved=resolved,
            unresolved=unresolved,
            resolution_methods=methods,
            human_review_needed=len(unresolved) > 0,
            confidence=_avg_confidence(resolved),
            details=details,
        )

    async def generate_resolution_report(
        self,
        conflict_points: list[ConflictPoint],
        resolutions: list[dict],
        db: AsyncSession | None = None,
    ) -> str:
        if not conflict_points:
            return "No conflicts detected between agents."

        details_lines = []
        resolved_count = 0
        unresolved_count = 0

        for i, cp in enumerate(conflict_points):
            res = resolutions[i] if i < len(resolutions) else None
            if res and res.get("resolution"):
                resolved_count += 1
                method = res.get("method", "unknown")
                resolution_text = res.get("resolution", "No resolution")
                details_lines.append(
                    f"Conflict #{i + 1} [{cp.type}]: {cp.description}\n"
                    f"  Agent A: {cp.agent_a_view[:150]}\n"
                    f"  Agent B: {cp.agent_b_view[:150]}\n"
                    f"  Resolution: {resolution_text}\n"
                    f"  Method: {method}\n"
                )
            else:
                unresolved_count += 1
                details_lines.append(
                    f"Conflict #{i + 1} [{cp.type}]: {cp.description}\n"
                    f"  Agent A: {cp.agent_a_view[:150]}\n"
                    f"  Agent B: {cp.agent_b_view[:150]}\n"
                    f"  Status: UNRESOLVED — requires human review\n"
                )

        details_text = "\n".join(details_lines)

        prompt = REPORT_PROMPT.format(
            num_conflicts=len(conflict_points),
            num_resolved=resolved_count,
            num_unresolved=unresolved_count,
            details_text=details_text,
        )

        try:
            client = None
            if db is not None:
                dummy_agent = Agent(
                    id="report_generator",
                    name="ReportGenerator",
                    agent_type="analyst",
                    ai_model=self.model,
                    ai_system_prompt="Generate clear conflict resolution reports.",
                    ai_temperature=0.2,
                )
                client, _ = await get_llm_client(self.model, dummy_agent, db)
            else:
                from app.services.llm_router import get_llm_client
                client, _ = await get_llm_client(self.model)

            response = await client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": "You generate clear, concise conflict resolution reports."},
                    {"role": "user", "content": prompt},
                ],
            )

            return response.choices[0].message.content or self._fallback_report(
                conflict_points, resolved_count, unresolved_count
            )

        except Exception as e:
            logger.error(f"Failed to generate resolution report: {e}")
            return self._fallback_report(conflict_points, resolved_count, unresolved_count)

    def _fallback_report(
        self,
        conflict_points: list[ConflictPoint],
        resolved_count: int,
        unresolved_count: int,
    ) -> str:
        parts = [f"I detected {len(conflict_points)} conflicts between your agents. "]
        if resolved_count:
            parts.append(f"{resolved_count} were resolved successfully. ")
        if unresolved_count:
            parts.append(f"{unresolved_count} require human review. ")

        for i, cp in enumerate(conflict_points):
            parts.append(
                f"Conflict #{i + 1}: {cp.type} about {cp.description}. "
                f"Agent views differ on: {cp.agent_a_view[:80]} vs {cp.agent_b_view[:80]}. "
            )

        return "".join(parts)


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


def _avg_confidence(resolved_items: list) -> float:
    if not resolved_items:
        return 0.0
    confidences = [r.get("confidence", 0.0) for r in resolved_items]
    return round(sum(confidences) / len(confidences), 3)


def _compute_jaccard_similarity(text_a: str, text_b: str) -> float:
    try:
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)
    except Exception:
        return 0.0
