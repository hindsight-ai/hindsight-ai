"""Typed per-request context dataclasses.

Extracted from ``core.api.deps`` (#92) — that module had grown to 678 LOC
mixing dataclass definitions, FastAPI ``Depends`` resolvers, dev-mode
PAT provisioning, and PAT-scope narrowing. This module owns only the
type definitions; resolvers stay in ``deps.py``.

Re-exported by ``deps.py`` so the ~50 caller modules continue to do
``from core.api.deps import UserContext, RequestContext`` without
changes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import only for type hints
    from core.db import models
    from core.db.scope_utils import ScopeContext


@dataclass(frozen=True)
class PatContext:
    """Metadata about the PAT used to authenticate this request."""
    id: Any
    token_id: str
    scopes: List[str]
    organization_id: Optional[Any]


@dataclass(frozen=True)
class CurrentUserContext:
    """Per-request user context.

    Replaces the legacy Dict[str, Any] shape. Consumers should access via
    attribute (``ctx.is_superadmin``) instead of dict get
    (``ctx.get('is_superadmin')``). Mistyped attribute access fails
    loudly at the call site instead of silently returning ``None`` — the
    entire reason this type exists.
    """
    id: Any
    email: str
    display_name: Optional[str]
    is_superadmin: bool
    is_beta_access_admin: bool
    memberships: List[Dict[str, Any]]
    memberships_by_org: Dict[str, Dict[str, Any]]
    beta_access_status: Optional[str]
    pat: Optional[PatContext] = None
    dev_mode_pat: Optional[str] = None


@dataclass(frozen=True)
class UserContext:
    """Result of ``get_current_user_context*()`` — pairs the ORM user row with the typed ``CurrentUserContext``."""
    user: "models.User"
    current: CurrentUserContext


@dataclass(frozen=True)
class RequestContext:
    """Result of ``get_scoped_user_and_context()`` — adds ``ScopeContext`` on top of ``UserContext``."""
    user: "models.User"
    current: CurrentUserContext
    scope: "ScopeContext"
