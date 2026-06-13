import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.agent import Agent, AgentConfig, AgentExecutionRun, AgentReputationScore
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

AB_TTL_SECONDS = 30 * 24 * 3600


class ABDeployment:

    @staticmethod
    async def create_variant(
        base_agent_id: str,
        variant_settings: dict,
        traffic_split: float,
        db: AsyncSession,
    ) -> dict:
        agent_res = await db.execute(select(Agent).where(Agent.id == base_agent_id))
        base_agent = agent_res.scalar_one_or_none()
        if not base_agent:
            raise ValueError(f"Agent {base_agent_id} not found")

        variant_id = uuid.uuid4().hex
        variant_name = variant_settings.get("name", f"{base_agent.name} (Variant)")

        variant_agent = Agent(
            id=variant_id,
            name=variant_name,
            agent_type=base_agent.agent_type,
            ai_model=variant_settings.get("ai_model", base_agent.ai_model),
            ai_system_prompt=variant_settings.get("ai_system_prompt", base_agent.ai_system_prompt),
            ai_temperature=variant_settings.get("ai_temperature", base_agent.ai_temperature),
            ai_tone=variant_settings.get("ai_tone", base_agent.ai_tone),
            ai_guardrails=variant_settings.get("ai_guardrails", base_agent.ai_guardrails),
            agent_settings=variant_settings.get("agent_settings", base_agent.agent_settings),
            is_active=True,
        )
        db.add(variant_agent)

        cfg_res = await db.execute(
            select(AgentConfig).where(AgentConfig.agent_id == base_agent_id)
        )
        base_cfg = cfg_res.scalar_one_or_none()
        if base_cfg:
            variant_config = AgentConfig(
                id=uuid.uuid4().hex,
                agent_id=variant_id,
                max_loops=base_cfg.max_loops,
                max_tokens_per_run=base_cfg.max_tokens_per_run,
                input_schema=base_cfg.input_schema,
                output_schema=base_cfg.output_schema,
            )
            db.add(variant_config)

        await db.commit()

        r = await get_redis()
        key = f"ab:{base_agent_id}:{variant_id}:split"
        await r.set(key, str(traffic_split), ex=AB_TTL_SECONDS)

        total_key = f"ab:{base_agent_id}:total_split"
        current_total = float(await r.get(total_key) or 0)
        await r.set(total_key, str(current_total + traffic_split), ex=AB_TTL_SECONDS)

        base_remainder = round(1.0 - (current_total + traffic_split), 4)
        logger.info(
            f"AB variant created: {variant_id} for base {base_agent_id}, "
            f"split={traffic_split}, base_remainder={base_remainder}"
        )

        return {
            "variant_id": variant_id,
            "variant_name": variant_name,
            "traffic_split": traffic_split,
            "base_agent_id": base_agent_id,
            "base_remainder": base_remainder,
        }

    @staticmethod
    async def route_request(
        agent_id: str,
        user_context: dict,
        db: AsyncSession,
    ) -> str:
        r = await get_redis()
        pattern = f"ab:{agent_id}:*:split"
        keys = []
        try:
            keys = await r.keys(pattern)
        except Exception as e:
            logger.warning(f"Redis scan failed for AB routing: {e}")
            return agent_id

        if not keys:
            return agent_id

        user_id = user_context.get("user_id", user_context.get("sub", "unknown"))
        hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
        bucket = (hash_val % 10000) / 10000.0

        cumulative = 0.0
        for key in keys:
            split = float(await r.get(key) or 0)
            cumulative += split
            if bucket < cumulative:
                variant_id = key.decode("utf-8") if isinstance(key, bytes) else key
                variant_id = variant_id.replace("ab:", "").replace(":split", "")
                variant_id = variant_id.replace(agent_id + ":", "")
                logger.debug(
                    f"AB routed user {user_id} (bucket={bucket:.4f}) to variant {variant_id}"
                )
                return variant_id

        return agent_id

    @staticmethod
    async def compare_variants(
        agent_id: str,
        db: AsyncSession,
        period_days: int = 7,
    ) -> dict:
        cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)

        r = await get_redis()
        pattern = f"ab:{agent_id}:*:split"
        keys = []
        try:
            keys = await r.keys(pattern)
        except Exception:
            keys = []

        variant_ids = set()
        for key in keys:
            key_str = key.decode("utf-8") if isinstance(key, bytes) else key
            parts = key_str.replace("ab:", "").replace(":split", "").split(":")
            if len(parts) >= 2:
                variant_ids.add(parts[1])

        all_agent_ids = list(variant_ids) + [agent_id]
        comparison = {}

        for aid in all_agent_ids:
            runs_query = select(
                func.count(AgentExecutionRun.id).label("total"),
                func.avg(AgentExecutionRun.latency_ms).label("avg_latency"),
                func.avg(AgentExecutionRun.cost_usd).label("avg_cost"),
                func.sum(
                    func.case(
                        (AgentExecutionRun.status == "success", 1),
                        else_=0,
                    )
                ).label("successes"),
            ).where(
                and_(
                    AgentExecutionRun.agent_id == aid,
                    AgentExecutionRun.created_at >= cutoff,
                )
            )
            runs_result = await db.execute(runs_query)
            row = runs_result.one_or_none()
            if not row or row.total == 0:
                comparison[aid] = {
                    "total_runs": 0,
                    "success_rate": None,
                    "avg_latency_ms": None,
                    "avg_cost_usd": None,
                    "user_ratings_avg": None,
                    "task_completion_rate": None,
                }
                continue

            total = row.total
            successes = row.successes or 0
            success_rate = successes / total if total > 0 else 0

            rep_result = await db.execute(
                select(AgentReputationScore).where(
                    AgentReputationScore.agent_id == aid
                ).limit(1)
            )
            rep = rep_result.scalars().first()

            comparison[aid] = {
                "total_runs": total,
                "success_rate": round(success_rate, 4),
                "avg_latency_ms": round(row.avg_latency or 0, 1),
                "avg_cost_usd": round(row.avg_cost or 0, 6),
                "user_ratings_avg": round(rep.user_rating_score if rep else 50.0, 1),
                "task_completion_rate": round(rep.completion_score if rep else 50.0, 1),
            }

        base_stats = comparison.get(agent_id, {})
        variants_summary = []
        winner = None
        best_score = -1

        for vid in variant_ids:
            vstats = comparison.get(vid, {})
            if not vstats or not vstats.get("total_runs"):
                continue

            highlights = []
            if base_stats and base_stats.get("user_ratings_avg") is not None:
                diff = vstats.get("user_ratings_avg", 0) - base_stats.get("user_ratings_avg", 0)
                if diff > 0:
                    highlights.append(f"User satisfaction higher (+{diff:.0f}%)")
                elif diff < 0:
                    highlights.append(f"User satisfaction lower ({diff:.0f}%)")

            if base_stats and base_stats.get("success_rate") is not None:
                diff = (vstats.get("success_rate", 0) - base_stats.get("success_rate", 0)) * 100
                if diff > 1:
                    highlights.append(f"Success rate higher (+{diff:.1f}%)")
                elif diff < -1:
                    highlights.append(f"Success rate lower ({diff:.1f}%)")

            if base_stats and base_stats.get("avg_cost_usd") is not None and base_stats["avg_cost_usd"] > 0:
                diff = (vstats.get("avg_cost_usd", 0) - base_stats.get("avg_cost_usd", 0)) / base_stats["avg_cost_usd"] * 100
                if diff > 0:
                    highlights.append(f"Cost {diff:.0f}% higher")
                else:
                    highlights.append(f"Cost {abs(diff):.0f}% lower")

            if base_stats and base_stats.get("task_completion_rate") is not None:
                diff = vstats.get("task_completion_rate", 0) - base_stats.get("task_completion_rate", 0)
                if diff > 0:
                    highlights.append(f"Task completion higher (+{diff:.0f}%)")
                elif diff < 0:
                    highlights.append(f"Task completion lower ({diff:.0f}%)")

            score = 0
            if base_stats and base_stats.get("user_ratings_avg") is not None:
                score += max(0, vstats.get("user_ratings_avg", 0) - base_stats.get("user_ratings_avg", 0))
            if base_stats and base_stats.get("success_rate") is not None:
                score += max(0, (vstats.get("success_rate", 0) - base_stats.get("success_rate", 0)) * 100)
            if base_stats and base_stats.get("task_completion_rate") is not None:
                score += max(0, vstats.get("task_completion_rate", 0) - base_stats.get("task_completion_rate", 0))
            if base_stats and base_stats.get("avg_cost_usd") is not None and base_stats["avg_cost_usd"] > 0:
                score += max(0, 1 - vstats.get("avg_cost_usd", 0) / base_stats["avg_cost_usd"])

            variant_summary = {
                "variant_id": vid,
                **vstats,
                "highlights": highlights,
                "score": round(score, 2),
            }
            variants_summary.append(variant_summary)

            if score > best_score:
                best_score = score
                winner = vid

        recommendation = ""
        if winner and variants_summary:
            win_summary = variants_summary[-1] if variants_summary else {}
            hl_text = "; ".join(win_summary.get("highlights", []))
            if hl_text:
                recommendation = f"Variant {winner[:8]} outperforms baseline: {hl_text}."
            else:
                recommendation = f"No clear winner detected for agent {agent_id}."

        return {
            "agent_id": agent_id,
            "period_days": period_days,
            "baseline": base_stats,
            "variants": variants_summary,
            "winner_variant_id": winner,
            "recommendation": recommendation,
        }

    @staticmethod
    async def promote_variant(variant_id: str, db: AsyncSession) -> dict:
        variant_res = await db.execute(
            select(Agent).where(Agent.id == variant_id)
        )
        variant = variant_res.scalar_one_or_none()
        if not variant:
            raise ValueError(f"Variant agent {variant_id} not found")

        r = await get_redis()
        pattern = f"ab:*:{variant_id}:split"
        keys = []
        try:
            keys = await r.keys(pattern)
        except Exception:
            keys = []

        base_agent_id = None
        for key in keys:
            key_str = key.decode("utf-8") if isinstance(key, bytes) else key
            parts = key_str.replace("ab:", "").replace(":split", "").split(":")
            if len(parts) >= 2:
                candidate_base = parts[0]
                base_agent_id = candidate_base
                break

        if not base_agent_id:
            base_agent_id = variant.agent_settings.get("ab_base_agent_id") if variant.agent_settings else None

        if not base_agent_id:
            raise ValueError("Could not determine base agent for this variant")

        base_res = await db.execute(
            select(Agent).where(Agent.id == base_agent_id)
        )
        base_agent = base_res.scalar_one_or_none()
        if not base_agent:
            raise ValueError(f"Base agent {base_agent_id} not found")

        base_agent.ai_model = variant.ai_model
        base_agent.ai_system_prompt = variant.ai_system_prompt
        base_agent.ai_temperature = variant.ai_temperature
        base_agent.ai_tone = variant.ai_tone
        base_agent.ai_guardrails = variant.ai_guardrails
        base_agent.agent_settings = variant.agent_settings or {}
        base_agent.agent_settings.pop("ab_base_agent_id", None)
        base_agent.updated_at = datetime.now(timezone.utc)

        variant.is_active = False

        for key in keys:
            await r.delete(key)

        total_key = f"ab:{base_agent_id}:total_split"
        await r.delete(total_key)

        await db.commit()

        logger.info(
            f"AB variant {variant_id} promoted to baseline for agent {base_agent_id}"
        )
        return {
            "status": "promoted",
            "variant_id": variant_id,
            "base_agent_id": base_agent_id,
            "message": f"Variant {variant.name} is now the new baseline",
        }

    @staticmethod
    async def auto_rollback(agent_id: str, db: AsyncSession) -> dict:
        cutoff = datetime.now(timezone.utc) - timedelta(days=1)

        base_query = select(
            func.count(AgentExecutionRun.id).label("total"),
            func.sum(
                func.case(
                    (AgentExecutionRun.status == "failed", 1),
                    else_=0,
                )
            ).label("failures"),
        ).where(
            and_(
                AgentExecutionRun.agent_id == agent_id,
                AgentExecutionRun.created_at >= cutoff,
            )
        )
        base_result = await db.execute(base_query)
        base_row = base_result.one_or_none()
        base_total = base_row.total if base_row else 0
        base_failures = base_row.failures if base_row else 0
        base_error_rate = base_failures / base_total if base_total > 0 else 0

        r = await get_redis()
        pattern = f"ab:{agent_id}:*:split"
        keys = []
        try:
            keys = await r.keys(pattern)
        except Exception:
            keys = []

        rolled_back = []

        for key in keys:
            key_str = key.decode("utf-8") if isinstance(key, bytes) else key
            parts = key_str.replace("ab:", "").replace(":split", "").split(":")
            if len(parts) < 2:
                continue
            variant_id = parts[1]

            var_query = select(
                func.count(AgentExecutionRun.id).label("total"),
                func.sum(
                    func.case(
                        (AgentExecutionRun.status == "failed", 1),
                        else_=0,
                    )
                ).label("failures"),
            ).where(
                and_(
                    AgentExecutionRun.agent_id == variant_id,
                    AgentExecutionRun.created_at >= cutoff,
                )
            )
            var_result = await db.execute(var_query)
            var_row = var_result.one_or_none()
            var_total = var_row.total if var_row else 0
            var_failures = var_row.failures if var_row else 0
            var_error_rate = var_failures / var_total if var_total > 0 else 0

            if var_error_rate > (base_error_rate * 2) and var_total >= 5:
                await r.delete(key)
                total_key = f"ab:{agent_id}:total_split"
                old_total = float(await r.get(total_key) or 0)
                split_val = float(await r.get(key_str) or 0)
                await r.set(total_key, str(max(0, old_total - split_val)), ex=AB_TTL_SECONDS)

                rolled_back.append({
                    "variant_id": variant_id,
                    "error_rate": round(var_error_rate, 4),
                    "baseline_error_rate": round(base_error_rate, 4),
                })
                logger.warning(
                    f"Auto-rollback: Variant {variant_id} error rate "
                    f"({var_error_rate:.4f}) exceeds 2x baseline ({base_error_rate:.4f})"
                )

        if rolled_back:
            return {
                "status": "rolled_back",
                "agent_id": agent_id,
                "rolled_back_variants": rolled_back,
                "message": f"{len(rolled_back)} variant(s) auto-rolled back",
            }

        return {
            "status": "healthy",
            "agent_id": agent_id,
            "baseline_error_rate": round(base_error_rate, 4),
            "message": "No variants exceeded error threshold",
        }

    @staticmethod
    async def get_active_deployment(agent_id: str) -> Optional[dict]:
        r = await get_redis()
        pattern = f"ab:{agent_id}:*:split"
        keys = []
        try:
            keys = await r.keys(pattern)
        except Exception:
            return None

        if not keys:
            return None

        variants = []
        total_split = 0.0

        for key in keys:
            key_str = key.decode("utf-8") if isinstance(key, bytes) else key
            parts = key_str.replace("ab:", "").replace(":split", "").split(":")
            if len(parts) >= 2:
                vid = parts[1]
                split_val = float(await r.get(key_str) or 0)
                total_split += split_val
                variants.append({"variant_id": vid, "split": split_val})

        return {
            "agent_id": agent_id,
            "variants": variants,
            "total_split": round(total_split, 4),
            "base_split": round(1.0 - total_split, 4),
        }
