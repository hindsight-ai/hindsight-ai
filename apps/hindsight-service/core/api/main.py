"""
FastAPI app assembly: middleware and router wiring.
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# Configure logging
LOG_LEVEL_NAME = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_NAME, logging.INFO)
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
logger.info("app_startup: log_level=%s", LOG_LEVEL_NAME)


from core.api.auth import IdentityMismatchError
from core.api.middleware.scope import enforce_write_scope_metadata

# Resource routers (existing)
from core.api.orgs import router as orgs_router
from core.api.agents import router as agents_router
from core.api.keywords import router as keywords_router
from core.api.memory_blocks import router as memory_blocks_router
from core.api.audits import router as audits_router
from core.api.bulk_operations import router as bulk_operations_router
from core.api.notifications import router as notifications_router
from core.api.consolidation import router as consolidation_router
from core.api.support import router as support_router
from core.api.users import router as users_router
from core.api.beta_access import router as beta_access_router

# New routers extracted from main.py
from core.api.user_info import router as user_info_router
from core.api.pruning import router as pruning_router
from core.api.compression import router as compression_router
from core.api.search import router as search_router
from core.api.memory_blocks_bulk import router as memory_blocks_bulk_router

# Database schema is managed by Alembic migrations.


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Startup / shutdown hooks.

    On startup: reconcile bulk operations stuck in `running` state across
    a process restart (#88). The check runs synchronously before the app
    accepts traffic; failure to reconcile is logged but does not block
    startup (better to serve traffic than to crash on a transient DB
    glitch).
    """
    try:
        from core.async_bulk_operations import reconcile_stuck_bulk_operations
        reconciled = reconcile_stuck_bulk_operations(min_age_seconds=60)
        if reconciled:
            logger.info("startup: reconciled %d stuck bulk operations to 'failed'", reconciled)
    except Exception as exc:  # pragma: no cover — defensive logging
        logger.warning("startup: bulk-operation reconciliation failed: %s", exc)
    yield


app = FastAPI(
    title="Intelligent AI Agent Memory Service",
    description="API for managing AI agent memories, including creation, retrieval, and feedback.",
    version="1.0.0",
    lifespan=lifespan,
)

# Avoid implicit trailing-slash redirects for predictable URLs
try:
    app.router.redirect_slashes = False
except Exception:
    pass

origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8000",
    "https://app.hindsight-ai.com",
    "https://app-staging.hindsight-ai.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Translate IdentityMismatchError (raised by core.api.auth.get_or_create_user
# when a request's external_subject does not match the existing User row's
# bound subject) into a clean 401, regardless of which handler was running.
# Without this, the exception escaped through ~5 call sites as a 500 with the
# mismatch detail in the response body.
@app.exception_handler(IdentityMismatchError)
async def _identity_mismatch_handler(_request: Request, _exc: IdentityMismatchError):
    return JSONResponse(
        {"authenticated": False, "detail": "Authentication denied."},
        status_code=status.HTTP_401_UNAUTHORIZED,
    )

# Middleware: enforce read-only for unauthenticated requests
@app.middleware("http")
async def enforce_readonly_for_guests(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        # In dev mode, allow; authentication is handled by route dependencies
        import os
        is_dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"

        if not is_dev_mode:
            try:
                path = request.url.path or ""
            except Exception:
                path = ""
            if path.startswith("/beta-access/review/") and path.endswith("/token"):
                return await call_next(request)
            h = request.headers
            user_present = (
                h.get("x-auth-request-user")
                or h.get("x-auth-request-email")
                or h.get("x-forwarded-user")
                or h.get("x-forwarded-email")
            )
            # Allow Personal Access Tokens to pass; route dependencies validate
            pat_present = h.get("authorization") or h.get("x-api-key")
            if not user_present and not pat_present:
                return JSONResponse(
                    {"detail": "Guest mode is read-only. Sign in to perform changes."},
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )
    return await call_next(request)

# Middleware: require explicit scope metadata on write operations for scoped resources
app.middleware("http")(enforce_write_scope_metadata)

# ---------------------------------------------------------------------------
# Router registration
# ---------------------------------------------------------------------------

app.include_router(users_router)
app.include_router(user_info_router)
app.include_router(orgs_router)
app.include_router(agents_router)
app.include_router(keywords_router)
app.include_router(memory_blocks_router)
app.include_router(audits_router)
app.include_router(bulk_operations_router)
app.include_router(notifications_router)
app.include_router(consolidation_router)
app.include_router(support_router)
app.include_router(beta_access_router)
app.include_router(pruning_router)
app.include_router(compression_router)
app.include_router(search_router)
app.include_router(memory_blocks_bulk_router)

# Test-fixtures router — ONLY mounted when E2E_TEST_HOOKS=true.
# These endpoints seed DB state for the Playwright E2E suite and bypass
# LLM-gated paths (e.g. consolidation suggestion creation). MUST NOT be
# enabled in production. See `core/api/test_fixtures.py` for the security
# model. The conditional import means the routes literally do not exist in
# prod bytecode when the flag is unset.
if os.getenv("E2E_TEST_HOOKS", "false").lower() == "true":
    from core.api.test_fixtures import router as test_fixtures_router  # noqa: E402
    app.include_router(test_fixtures_router)
    logger.warning("E2E_TEST_HOOKS=true — test-fixtures endpoints mounted. NEVER enable in production.")

# Include memory optimization router
try:
    from core.api.memory_optimization import router as memory_optimization_router
    app.include_router(memory_optimization_router, prefix="/memory-optimization", tags=["memory-optimization"])
    logger.info("Memory optimization endpoints loaded successfully")
except ImportError as e:
    logger.warning(f"Could not load memory optimization endpoints: {e}")

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "hindsight-service"}


# /conversations/count lives at the top level (no resource prefix). It does
# not fit cleanly under /memory-blocks/ even though it queries memory blocks.
# Kept here to preserve the URL.
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from core.db.database import get_db
from core.db.repositories.memory_blocks import get_unique_conversation_count
from core.api.deps import get_scoped_user_and_context, ensure_pat_allows_read


@app.get("/conversations/count")
def get_conversations_count_endpoint(
    db: Session = Depends(get_db),
    scoped = Depends(get_scoped_user_and_context),
):
    """Get the count of unique conversations from memory blocks."""
    try:
        user = scoped.user
        current_user = scoped.current
        scope_ctx = scoped.scope
        ensure_pat_allows_read(current_user, scope_ctx.organization_id)
        count = get_unique_conversation_count(db, current_user=current_user, scope_ctx=scope_ctx)
        return {"count": count or 0}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversations count: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting conversations count: {str(e)}")
