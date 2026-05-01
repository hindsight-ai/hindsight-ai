"""Sanity tests for the core.api.orgs package — pin the public router shape."""
from fastapi.routing import APIRoute


def test_orgs_router_exposes_unified_router():
    """The package's `router` is an APIRouter with all 17 routes mounted."""
    from core.api.orgs import router

    # All routes carry the /organizations prefix from the parent router
    paths = [r.path for r in router.routes if isinstance(r, APIRoute)]
    assert len(paths) == 17, f"Expected 17 routes, got {len(paths)}: {paths}"
    assert all(p.startswith("/organizations") for p in paths), (
        f"Some routes missing /organizations prefix: {[p for p in paths if not p.startswith('/organizations')]}"
    )


def test_orgs_router_routes_partitioned_by_subdomain():
    """Each of the 3 sub-modules contributes its expected route count."""
    from core.api.orgs import router

    paths = [r.path for r in router.routes if isinstance(r, APIRoute)]
    members_paths = [p for p in paths if "/members" in p]
    invitations_paths = [p for p in paths if "/invitations" in p]
    org_paths = [p for p in paths if p not in members_paths and p not in invitations_paths]

    assert len(org_paths) == 7, f"Expected 7 org-CRUD routes, got {len(org_paths)}"
    assert len(members_paths) == 4, f"Expected 4 member routes, got {len(members_paths)}"
    assert len(invitations_paths) == 6, f"Expected 6 invitation routes, got {len(invitations_paths)}"


def test_orgs_subrouters_importable_individually():
    """Each sub-module's router is independently importable (for future composition)."""
    from core.api.orgs.organizations import router as orgs_crud_router
    from core.api.orgs.members import router as members_router
    from core.api.orgs.invitations import router as invitations_router

    assert len([r for r in orgs_crud_router.routes if isinstance(r, APIRoute)]) == 7
    assert len([r for r in members_router.routes if isinstance(r, APIRoute)]) == 4
    assert len([r for r in invitations_router.routes if isinstance(r, APIRoute)]) == 6
