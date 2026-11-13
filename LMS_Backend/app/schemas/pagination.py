"""Cursor-paginated list responses."""

from pydantic import BaseModel, Field


class Page[T](BaseModel):
    items: list[T]
    next_cursor: str | None = Field(
        default=None, description="Pass as `cursor` to fetch the next page; null on the last page."
    )
