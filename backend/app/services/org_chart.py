import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.core.cache import cache_get, cache_set, cache_invalidate_namespace

logger = logging.getLogger("successcore.orgchart")

CACHE_NAMESPACE = "orgchart"
CACHE_TTL = 60


def _build_tree(users) -> Dict[str, Any]:
    user_map: Dict[str, dict] = {}
    for u in users:
        user_map[u.id] = {
            "id": u.id,
            "name": u.full_name or u.email,
            "email": u.email,
            "department": u.department,
            "role": u.role,
            "title": u.role,
            "manager_id": u.manager_id,
            "children": [],
        }

    roots: List[dict] = []
    for uid, node in user_map.items():
        manager_id = node["manager_id"]
        if manager_id and manager_id in user_map:
            user_map[manager_id]["children"].append(node)
        else:
            roots.append(node)

    return {"org_name": "Organization", "total_employees": len(users), "roots": roots}


async def build_org_chart(db: AsyncSession) -> Dict[str, Any]:
    result = await db.execute(select(User).where(User.is_active == True).order_by(User.full_name.asc()))
    users = result.scalars().all()
    return _build_tree(users)


async def get_cached_org_chart(db: AsyncSession, tenant_id: str) -> Dict[str, Any]:
    cache_key = f"tree:{tenant_id}"
    cached = await cache_get(CACHE_NAMESPACE, cache_key)
    if cached:
        return cached
    chart = await build_org_chart(db)
    await cache_set(CACHE_NAMESPACE, cache_key, chart, ttl=CACHE_TTL)
    return chart


async def get_org_chart_preview(db: AsyncSession, tenant_id: str, max_depth: int = 2) -> Dict[str, Any]:
    result = await db.execute(select(User).where(User.is_active == True).order_by(User.full_name.asc()))
    users = result.scalars().all()
    tree = _build_tree(users)
    _prune_depth(tree["roots"], max_depth)
    return tree


def _prune_depth(nodes: list, max_depth: int, current_depth: int = 0):
    if current_depth >= max_depth:
        for node in nodes:
            node["children"] = []
        return
    for node in nodes:
        _prune_depth(node["children"], max_depth, current_depth + 1)


def _count_descendants(node: dict) -> int:
    count = len(node["children"])
    for child in node["children"]:
        count += _count_descendants(child)
    return count


async def _invalidate_org_chart_cache(tenant_id: str = "", payload: dict = None) -> None:
    await cache_invalidate_namespace(CACHE_NAMESPACE)
    logger.debug(f"Org chart cache invalidated for tenant {tenant_id}")


def bind_org_chart_cache_invalidation():
    from app.services.event_bus import get_event_bus
    from app.services.event_catalog import EMPLOYEE_CREATED, EMPLOYEE_UPDATED, EMPLOYEE_ARCHIVED, EMPLOYEE_DELETED

    bus = get_event_bus()
    for event_type in [EMPLOYEE_CREATED, EMPLOYEE_UPDATED, EMPLOYEE_ARCHIVED, EMPLOYEE_DELETED]:
        bus.subscribe(
            event_type,
            lambda tenant_id="", payload=None, et=event_type: _invalidate_org_chart_cache(tenant_id, payload)
        )
