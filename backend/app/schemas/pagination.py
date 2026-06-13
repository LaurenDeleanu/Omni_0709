from pydantic import BaseModel
from typing import Generic, TypeVar, List, Optional

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class CursorPaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    next_cursor: Optional[str] = None
    has_more: bool = False
