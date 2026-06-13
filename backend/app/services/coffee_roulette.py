import random
import logging
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

logger = logging.getLogger("successcore.roulette")

_past_pairings: List[tuple] = []


async def generate_coffee_pairings(db: AsyncSession) -> dict:
    from app.models.user import User

    users_res = await db.execute(
        select(User).where(User.is_active == True)
    )
    users = list(users_res.scalars().all())

    if len(users) < 2:
        return {"paired": 0, "pairs": [], "message": "Not enough active users"}

    random.shuffle(users)
    pairs = []
    used = set()

    for i in range(0, len(users) - 1, 2):
        a, b = users[i], users[i + 1]
        if a.department == b.department:
            if i + 2 < len(users):
                b, users[i + 2] = users[i + 2], b
        pair_key = tuple(sorted([a.id, b.id]))
        if pair_key in _past_pairings and i + 2 < len(users):
            continue

        pairs.append({
            "person_a": {"id": a.id, "name": a.full_name or a.email, "department": a.department},
            "person_b": {"id": b.id, "name": b.full_name or b.email, "department": b.department},
            "cross_department": a.department != b.department,
        })
        used.add(a.id)
        used.add(b.id)
        _past_pairings.append(pair_key)

    return {
        "week": f"{datetime.now(timezone.utc).isocalendar().week}",
        "paired": len(pairs) * 2,
        "total_employees": len(users),
        "pairs": pairs,
        "suggestion": "Send calendar invites to each pair for a 15-minute virtual coffee chat",
    }
