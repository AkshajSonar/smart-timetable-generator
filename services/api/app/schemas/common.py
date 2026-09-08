"""Common schemas: paginated response, error envelope per §29."""

from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """§29.5: all list endpoints return {items, next_cursor}."""
    items: list[T]
    next_cursor: Optional[str] = None


class ErrorDetail(BaseModel):
    code: str  # VALIDATION_ERROR | NOT_FOUND | FORBIDDEN | CONFLICT | INFEASIBLE_CONFIGURATION
    message: str
    details: dict[str, Any] = {}


class ErrorResponse(BaseModel):
    """§29.3: standard error envelope."""
    error: ErrorDetail
