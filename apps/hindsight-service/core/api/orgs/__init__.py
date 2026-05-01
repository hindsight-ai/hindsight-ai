"""
Organizations API package.

Exposes a unified `router` under the `/organizations` prefix by composing
three sub-routers: org CRUD, membership management, and invitations.
"""
from fastapi import APIRouter
from core.api.orgs.organizations import router as _orgs_router
from core.api.orgs.members import router as _members_router
from core.api.orgs.invitations import router as _invitations_router

router = APIRouter(prefix="/organizations", tags=["organizations"])
router.include_router(_orgs_router)
router.include_router(_members_router)
router.include_router(_invitations_router)
