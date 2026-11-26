#!/usr/bin/env python3
"""Contract check: the edge proxy must drop every identity header the backend trusts.

Why this exists
---------------
The backend (apps/hindsight-service/core/api/deps.py) authenticates a request
from identity headers such as ``X-Auth-Request-Email`` / ``X-Forwarded-Email``.
Those headers are only trustworthy when oauth2-proxy set them. Traefik routes
``api.<domain>`` straight to the backend (no oauth2-proxy in front), so a
client-supplied identity header would be taken at face value and let anyone
act as any user, including a superadmin.

The fix is an entry-point middleware in Traefik (``strip-identity-headers``)
that blanks those headers on every incoming request *before* any router or
oauth2-proxy runs. oauth2-proxy then sets the real values on its own hop.

This script fails (exit 1) when:
  * the ``websecure`` entry point does not apply ``strip-identity-headers@file``;
  * the middleware does not blank a header that the backend reads as identity
    (it parses the ``Header(...)`` parameters in deps.py, so adding a new
    identity header to the backend without stripping it at the edge fails CI).

Usage: python3 scripts/check_edge_identity_headers.py [repo_root]
Requires PyYAML.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

MIDDLEWARE = "strip-identity-headers"
# Header parameters in deps.py that are NOT identity assertions: PAT credentials
# are verified cryptographically, scope headers only narrow what a verified
# identity may see.
NON_IDENTITY_PARAMS = {"authorization", "x_api_key", "x_active_scope", "x_organization_id"}
# Headers oauth2-proxy can emit; strip them all even if the backend does not read them yet.
OAUTH2_PROXY_HEADERS = {
    "x-auth-request-user",
    "x-auth-request-email",
    "x-auth-request-access-token",
    "x-auth-request-preferred-username",
    "x-auth-request-groups",
    "x-forwarded-user",
    "x-forwarded-email",
    "x-forwarded-preferred-username",
    "x-forwarded-groups",
    "x-forwarded-access-token",
}


def backend_identity_headers(deps_source: str) -> set[str]:
    params = set(re.findall(r"\b(x_[a-z_]+)\s*:\s*Optional\[str\]\s*=\s*Header\(", deps_source))
    return {p.replace("_", "-") for p in params if p not in NON_IDENTITY_PARAMS}


def main(root: Path) -> int:
    errors: list[str] = []
    static = yaml.safe_load((root / "config" / "traefik.yml").read_text())
    dynamic = yaml.safe_load((root / "config" / "dynamic.yml").read_text())
    deps = (root / "apps" / "hindsight-service" / "core" / "api" / "deps.py").read_text()

    ep_mws = (((static.get("entryPoints") or {}).get("websecure") or {}).get("http") or {}).get("middlewares") or []
    if f"{MIDDLEWARE}@file" not in ep_mws:
        errors.append(f"entryPoints.websecure.http.middlewares must include '{MIDDLEWARE}@file' (got {ep_mws})")

    if "api" in static:
        errors.append("traefik.yml must not enable the Traefik API/dashboard (it was publicly reachable without auth)")

    mw = ((dynamic.get("http") or {}).get("middlewares") or {}).get(MIDDLEWARE) or {}
    custom = ((mw.get("headers") or {}).get("customRequestHeaders")) or {}
    blanked = {k.lower() for k, v in custom.items() if v == ""}

    trusted = backend_identity_headers(deps)
    if not trusted:
        errors.append("could not find any identity Header() parameters in deps.py; update this check")
    for h in sorted(trusted | OAUTH2_PROXY_HEADERS):
        if h not in blanked:
            errors.append(f"middleware '{MIDDLEWARE}' does not blank identity header '{h}'")

    if errors:
        print("Edge identity-header contract FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"Edge identity-header contract OK: {len(blanked)} headers stripped; backend trusts {sorted(trusted)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent))
