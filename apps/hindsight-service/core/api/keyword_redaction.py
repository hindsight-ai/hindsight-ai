"""Hide keywords the caller may not read from memory-block responses.

A readable (e.g. public) memory block can be linked to a keyword that is
personal or belongs to another organisation. Serialising the block's
``keywords`` verbatim would disclose that keyword's text. These helpers work on
detached pydantic copies so the ORM rows and their associations are never
mutated.
"""
from __future__ import annotations

from typing import Any, Iterable, List, Optional

from core.db import schemas
from core.db.scope_utils import get_user_organization_ids
from core.utils.scopes import SCOPE_ORGANIZATION, SCOPE_PUBLIC


def keyword_visible_to(keyword: Any, current_user: Optional[Any]) -> bool:
    """Same visibility rule as ``apply_scope_filter`` for a single keyword."""
    scope = getattr(keyword, "visibility_scope", None)
    scope = getattr(scope, "value", scope)
    if scope == SCOPE_PUBLIC:
        return True
    if current_user is None or getattr(current_user, "id", None) is None:
        return False
    if getattr(current_user, "is_superadmin", False):
        return True
    if getattr(keyword, "owner_user_id", None) == current_user.id:
        return True
    org_id = getattr(keyword, "organization_id", None)
    return (
        scope == SCOPE_ORGANIZATION
        and org_id is not None
        and org_id in get_user_organization_ids(current_user)
    )


def visible_keywords(keywords: Iterable[Any], current_user: Optional[Any]) -> List[Any]:
    return [k for k in keywords if keyword_visible_to(k, current_user)]


def redact_block(block: Any, current_user: Optional[Any], schema=schemas.MemoryBlock):
    """Return a detached pydantic copy of ``block`` with unreadable keywords removed."""
    out = block if isinstance(block, schemas.MemoryBlock) else schema.model_validate(block)
    out = out.model_copy(update={"keywords": visible_keywords(out.keywords, current_user)})
    return out


def redact_blocks(blocks: Iterable[Any], current_user: Optional[Any], schema=schemas.MemoryBlock):
    return [redact_block(b, current_user, schema) for b in blocks]
