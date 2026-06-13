import json
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
import uuid

from app.models.agent import Agent, AgentExecutionRun
from app.core.redis import get_redis

logger = logging.getLogger("successcore.agent_reputation")

REPUTATION_REDIS_PREFIX = "reputation:"
REPUTATION_WINDOW_DAYS = 30
REPUTATION_BASELINE_WINDOW_RUNS = 500
REPUTATION_RECENT_WINDOW_RUNS = 50
REPUTATION_DRIFT_THRESHOLD = 0.20

SCORE_WEIGHTS = {
    "user_ratings": 0.40,
    "task_completion": 0.30,
    "response_quality": 0.20,
    "cost_efficiency": 0.10,
}


class AgentReputation:
    @staticmethod
    async def calculate_reputation(agent_id: str, db: AsyncSession) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(days=REPUTATION_WINDOW_DAYS)

        user_rating_score = await _calculate_user_rating_score(agent_id, window_start, db)
        completion_score = await _calculate_completion_score(agent_id, window_start, db)
        quality_score = await _calculate_quality_score(agent_id, window_start, db)
        cost_score = await _calculate_cost_efficiency_score(agent_id, window_start, db)

        overall = (
            user_rating_score * SCORE_WEIGHTS["user_ratings"]
            + completion_score * SCORE_WEIGHTS["task_completion"]
            + quality_score * SCORE_WEIGHTS["response_quality"]
            + cost_score * SCORE_WEIGHTS["cost_efficiency"]
        )

        run_count_result = await db.execute(
            select(func.count(AgentExecutionRun.id)).where(
                AgentExecutionRun.agent_id == agent_id,
                AgentExecutionRun.created_at >= window_start,
            )
        )
        total_runs = int(run_count_result.scalar_one() or 0)

        trend = await _calculate_trend(agent_id, db)

        reputation_data = {
            "agent_id": agent_id,
            "overall_score": round(overall, 2),
            "user_rating_score": round(user_rating_score, 2),
            "completion_score": round(completion_score, 2),
            "quality_score": round(quality_score, 2),
            "cost_efficiency_score": round(cost_score, 2),
            "total_runs_evaluated": total_runs,
            "trend": trend,
            "calculated_at": now.isoformat(),
        }

        await _store_reputation_cache(agent_id, reputation_data)

        return reputation_data

    @staticmethod
    async def update_reputation(agent_id: str, run_result: dict, db: AsyncSession):
        try:
            score = await AgentReputation.calculate_reputation(agent_id, db)

            from app.models.agent import AgentReputationScore

            existing = await db.execute(
                select(AgentReputationScore)
                .where(AgentReputationScore.agent_id == agent_id)
                .order_by(AgentReputationScore.calculated_at.desc())
                .limit(1)
            )
            latest = existing.scalar_one_or_none()

            new_score = AgentReputationScore(
                id=uuid.uuid4().hex,
                agent_id=agent_id,
                overall_score=score["overall_score"],
                user_rating_score=score["user_rating_score"],
                completion_score=score["completion_score"],
                quality_score=score["quality_score"],
                cost_efficiency_score=score["cost_efficiency_score"],
                total_runs_evaluated=score["total_runs_evaluated"],
                trend=score.get("trend", "stable"),
            )
            db.add(new_score)

            await db.commit()
            logger.debug(f"Updated reputation for agent {agent_id}: overall={score['overall_score']:.1f}")

        except Exception as e:
            logger.warning(f"Failed to update reputation for agent {agent_id}: {e}")

    @staticmethod
    async def get_leaderboard(limit: int = 10, category: str = "overall", db: AsyncSession = None) -> list:
        from app.models.agent import AgentReputationScore, Agent

        if db is None:
            return []

        sub = (
            select(
                AgentReputationScore.agent_id,
                func.max(AgentReputationScore.calculated_at).label("max_at"),
            )
            .group_by(AgentReputationScore.agent_id)
            .subquery()
        )

        stmt = (
            select(AgentReputationScore, Agent.name, Agent.agent_type)
            .join(Agent, Agent.id == AgentReputationScore.agent_id)
            .join(
                sub,
                (AgentReputationScore.agent_id == sub.c.agent_id)
                & (AgentReputationScore.calculated_at == sub.c.max_at),
            )
            .order_by(AgentReputationScore.overall_score.desc())
            .limit(limit)
        )

        result = await db.execute(stmt)
        rows = result.all()

        leaderboard = []
        for score, name, agent_type in rows:
            entry = {
                "agent_id": score.agent_id,
                "name": name,
                "agent_type": agent_type,
                "rank": 0,
                "scores": {
                    "overall": round(score.overall_score, 2),
                    "user_rating": round(score.user_rating_score, 2),
                    "completion": round(score.completion_score, 2),
                    "quality": round(score.quality_score, 2),
                    "cost_efficiency": round(score.cost_efficiency_score, 2),
                },
                "trend": score.trend,
                "total_runs": score.total_runs_evaluated,
            }

            if category == "cost_efficiency":
                entry["rank_score"] = score.cost_efficiency_score
            elif category == "user_satisfaction":
                entry["rank_score"] = score.user_rating_score
            elif category == "task_completion":
                entry["rank_score"] = score.completion_score
            else:
                entry["rank_score"] = score.overall_score

            leaderboard.append(entry)

        sorted_board = sorted(leaderboard, key=lambda x: x["rank_score"], reverse=True)
        for i, entry in enumerate(sorted_board):
            entry["rank"] = i + 1

        return sorted_board

    @staticmethod
    async def detect_drift(agent_id: str, db: AsyncSession) -> dict:
        now = datetime.now(timezone.utc)
        baseline_start = now - timedelta(days=90)
        recent_start = now - timedelta(days=7)

        recent_result = await db.execute(
            select(
                func.count(AgentExecutionRun.id).label("total"),
                func.sum(case((AgentExecutionRun.status == "success", 1), else_=0)).label("successes"),
                func.avg(AgentExecutionRun.latency_ms).label("avg_latency"),
                func.avg(AgentExecutionRun.cost_usd).label("avg_cost"),
            ).where(
                AgentExecutionRun.agent_id == agent_id,
                AgentExecutionRun.created_at >= recent_start,
            )
        )
        recent = recent_result.one_or_none()
        recent_total = int(recent.total or 0)
        recent_successes = int(recent.successes or 0)
        recent_success_rate = recent_successes / recent_total if recent_total else 0
        recent_avg_latency = float(recent.avg_latency or 0)
        recent_avg_cost = float(recent.avg_cost or 0)

        base_result = await db.execute(
            select(
                func.count(AgentExecutionRun.id).label("total"),
                func.sum(case((AgentExecutionRun.status == "success", 1), else_=0)).label("successes"),
                func.avg(AgentExecutionRun.latency_ms).label("avg_latency"),
                func.avg(AgentExecutionRun.cost_usd).label("avg_cost"),
            ).where(
                AgentExecutionRun.agent_id == agent_id,
                AgentExecutionRun.created_at >= baseline_start,
                AgentExecutionRun.created_at < recent_start,
            )
        )
        base = base_result.one_or_none()
        base_total = int(base.total or 0)
        base_successes = int(base.successes or 0)
        base_success_rate = base_successes / base_total if base_total else 0
        base_avg_latency = float(base.avg_latency or 0)
        base_avg_cost = float(base.avg_cost or 0)

        drifts = {}
        alerts = []

        if base_success_rate > 0 and recent_success_rate > 0:
            success_drop = (base_success_rate - recent_success_rate) / base_success_rate
            drifts["success_rate_change"] = round(success_drop, 4)
            if success_drop > REPUTATION_DRIFT_THRESHOLD:
                alerts.append(f"Success rate dropped {success_drop * 100:.1f}% — from {base_success_rate:.2%} to {recent_success_rate:.2%}")

        if base_avg_latency > 0 and recent_avg_latency > 0:
            latency_increase = (recent_avg_latency - base_avg_latency) / base_avg_latency
            drifts["latency_change"] = round(latency_increase, 4)
            if latency_increase > REPUTATION_DRIFT_THRESHOLD:
                alerts.append(f"Latency increased {latency_increase * 100:.1f}% — from {base_avg_latency:.0f}ms to {recent_avg_latency:.0f}ms")

        if base_avg_cost > 0 and recent_avg_cost > 0:
            cost_increase = (recent_avg_cost - base_avg_cost) / base_avg_cost
            drifts["cost_change"] = round(cost_increase, 4)
            if cost_increase > REPUTATION_DRIFT_THRESHOLD:
                alerts.append(f"Cost increased {cost_increase * 100:.1f}% — from ${base_avg_cost:.4f} to ${recent_avg_cost:.4f}")

        is_drifting = len(alerts) > 0

        if is_drifting:
            logger.warning(f"Agent {agent_id} is drifting: {'; '.join(alerts)}")

        return {
            "agent_id": agent_id,
            "is_drifting": is_drifting,
            "alerts": alerts,
            "recent": {
                "total_runs": recent_total,
                "success_rate": round(recent_success_rate, 4),
                "avg_latency_ms": round(recent_avg_latency, 2),
                "avg_cost_usd": round(recent_avg_cost, 4),
                "window": "7 days",
            },
            "baseline": {
                "total_runs": base_total,
                "success_rate": round(base_success_rate, 4),
                "avg_latency_ms": round(base_avg_latency, 2),
                "avg_cost_usd": round(base_avg_cost, 4),
                "window": "83 days",
            },
            "drifts": drifts,
        }


async def _calculate_user_rating_score(agent_id: str, window_start, db: AsyncSession) -> float:
    try:
        result = await db.execute(
            select(func.count(AgentExecutionRun.id)).where(
                AgentExecutionRun.agent_id == agent_id,
                AgentExecutionRun.created_at >= window_start,
            )
        )
        total = int(result.scalar_one() or 0)
        if total == 0:
            return 50.0
        return 70.0
    except Exception:
        return 50.0


async def _calculate_completion_score(agent_id: str, window_start, db: AsyncSession) -> float:
    result = await db.execute(
        select(
            func.count(AgentExecutionRun.id).label("total"),
            func.sum(case((AgentExecutionRun.status == "success", 1), else_=0)).label("successes"),
        ).where(
            AgentExecutionRun.agent_id == agent_id,
            AgentExecutionRun.created_at >= window_start,
        )
    )
    row = result.one_or_none()
    total = int(row.total or 0)
    if total == 0:
        return 50.0
    successes = int(row.successes or 0)
    return round((successes / total) * 100, 2)


async def _calculate_quality_score(agent_id: str, window_start, db: AsyncSession) -> float:
    return 70.0


async def _calculate_cost_efficiency_score(agent_id: str, window_start, db: AsyncSession) -> float:
    result = await db.execute(
        select(
            func.count(AgentExecutionRun.id).label("total"),
            func.avg(AgentExecutionRun.cost_usd).label("avg_cost"),
            func.avg(AgentExecutionRun.token_usage).label("avg_tokens"),
        ).where(
            AgentExecutionRun.agent_id == agent_id,
            AgentExecutionRun.created_at >= window_start,
        )
    )
    row = result.one_or_none()
    total = int(row.total or 0)
    if total == 0:
        return 50.0
    avg_cost = float(row.avg_cost or 0)
    if avg_cost == 0:
        return 100.0
    normalized = max(0, min(100, (1.0 - avg_cost / 0.50) * 100))
    return round(normalized, 2)


async def _calculate_trend(agent_id: str, db: AsyncSession) -> str:
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=7)
    prev_start = now - timedelta(days=14)

    recent_result = await db.execute(
        select(
            func.count(AgentExecutionRun.id).label("total"),
            func.sum(case((AgentExecutionRun.status == "success", 1), else_=0)).label("successes"),
        ).where(
            AgentExecutionRun.agent_id == agent_id,
            AgentExecutionRun.created_at >= week_start,
        )
    )
    recent = recent_result.one_or_none()
    recent_total = int(recent.total or 0)
    recent_rate = (int(recent.successes or 0)) / recent_total if recent_total else 0

    prev_result = await db.execute(
        select(
            func.count(AgentExecutionRun.id).label("total"),
            func.sum(case((AgentExecutionRun.status == "success", 1), else_=0)).label("successes"),
        ).where(
            AgentExecutionRun.agent_id == agent_id,
            AgentExecutionRun.created_at >= prev_start,
            AgentExecutionRun.created_at < week_start,
        )
    )
    prev = prev_result.one_or_none()
    prev_total = int(prev.total or 0)
    prev_rate = (int(prev.successes or 0)) / prev_total if prev_total else 0

    if prev_rate == 0:
        return "stable"
    change = (recent_rate - prev_rate) / prev_rate
    if change > 0.05:
        return "improving"
    elif change < -0.05:
        return "declining"
    return "stable"


async def _store_reputation_cache(agent_id: str, data: dict):
    try:
        r = await get_redis()
        key = f"{REPUTATION_REDIS_PREFIX}{agent_id}"
        await r.set(key, json.dumps(data))
        await r.expire(key, 600)
    except Exception as e:
        logger.debug(f"Failed to cache reputation: {e}")


async def get_cached_reputation(agent_id: str) -> Optional[dict]:
    try:
        r = await get_redis()
        key = f"{REPUTATION_REDIS_PREFIX}{agent_id}"
        data = await r.get(key)
        if data:
            return json.loads(data)
    except Exception:
        pass
    return None
