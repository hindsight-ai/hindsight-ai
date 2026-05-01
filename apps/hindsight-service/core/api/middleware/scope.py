"""
Middleware: enforce explicit scope metadata on write operations for scoped resources.
"""
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import status


async def enforce_write_scope_metadata(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        try:
            path = request.url.path or ""
        except Exception:
            path = ""
        # Only enforce for scope-managed resources
        if (
            path.startswith("/agents")
            or path.startswith("/keywords")
            or path.startswith("/memory-blocks")
            or path.startswith("/consolidation")
            or path.startswith("/consolidation-suggestions/")
        ):
            h = request.headers
            # When a PAT is supplied (Authorization bearer token or X-API-Key),
            # downstream dependencies already enforce scope/organization semantics
            # based on the token itself. In that case we skip the header guard here
            # so PAT consumers do not have to echo redundant scope metadata.
            pat_present = bool(h.get("Authorization") or h.get("X-API-Key"))
            if not pat_present:
                qp = request.query_params
                scope_val = (h.get("X-Active-Scope") or qp.get("scope") or "").strip().lower()
                if not scope_val:
                    return JSONResponse({"detail": "scope_required"}, status_code=status.HTTP_400_BAD_REQUEST)
                if scope_val == "organization":
                    org_id = (h.get("X-Organization-Id") or qp.get("organization_id") or "").strip()
                    if not org_id:
                        return JSONResponse({"detail": "organization_id_required"}, status_code=status.HTTP_400_BAD_REQUEST)
    return await call_next(request)
