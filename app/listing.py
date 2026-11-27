"""Building blocks every paged list shares: a page of results, and search."""

from dataclasses import dataclass

from sqlalchemy import ColumnElement
from sqlalchemy.orm import InstrumentedAttribute, Query


@dataclass(frozen=True)
class Page[T]:
    items: list[T]
    # How many rows match, across all pages.
    total: int


def paginate[T](query: Query[T], limit: int, offset: int) -> Page[T]:
    """One query for the page and one for the count, whatever the page size.
    The query must already be ordered, or pages could overlap."""
    return Page(
        items=query.limit(limit).offset(offset).all(),
        total=query.order_by(None).count(),
    )


def contains(column: InstrumentedAttribute[str], search: str) -> ColumnElement[bool]:
    """Case-insensitive substring match; % and _ in the search match literally."""
    escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return column.ilike(f"%{escaped}%", escape="\\")
