from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select
from sqlalchemy import Row
from typing import Optional, Union, Any
from datetime import datetime


async def paginate_query(
    db: AsyncSession,
    query: Select,
    page: int = 1,
    page_size: int = 20,
    max_page_size: int = 100,
) -> dict:
    page_size = min(page_size, max_page_size)
    page = max(1, page)
    offset = (page - 1) * page_size

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(query.offset(offset).limit(page_size))
    items = list(result.scalars().all())

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


async def paginate_cursor(
    db: AsyncSession,
    query: Select,
    cursor_column,
    cursor: Optional[str] = None,
    size: int = 20,
    max_size: int = 100,
    raw_items: bool = False,
) -> dict:
    size = min(size, max_size)
    if cursor:
        query = query.where(cursor_column > cursor)
    query = query.order_by(cursor_column.asc()).limit(size + 1)

    result = await db.execute(query)
    if raw_items:
        items = list(result.all())
    else:
        items = list(result.scalars().all())

    has_more = len(items) > size
    if has_more:
        items = items[:size]

    next_cursor = None
    if has_more and items:
        last = items[-1]
        if raw_items and isinstance(last, Row):
            last_entity = last[0]
        else:
            last_entity = last
        val = getattr(last_entity, cursor_column.name)
        next_cursor = val.isoformat() if isinstance(val, datetime) else str(val)

    return {
        "items": items,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }
