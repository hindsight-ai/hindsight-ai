# Task Plan: Codebase Documentation and Architecture Docs Generator

## Goal
- Improve internal documentation by adding concise, PEP 257–style module docstrings summarizing purpose and key responsibilities for first‑party Python modules.
- Create a helper script under `scripts/` to generate `docs/architecture.md` with:
  - Current project layout (folders, subfolders, and all `.py` files) excluding virtual envs and caches.
  - A list of Python modules with their module docstrings.

## Plan
1. Catalog Python modules
2. Add/refresh module docstrings
3. Create docs generator script
4. Generate `docs/architecture.md`
5. Final review and polish

## Notes
- Exclude `.venv`, `node_modules`, and cache directories like `.uv-cache` from scanning and documentation.
- Do not modify third‑party or auto‑generated files (migrations) or tests unless necessary.
- Keep docstrings concise (1–3 lines summary; optional short details).

## Acceptance Criteria
- Every first‑party module in `apps/hindsight-service/core/**` and relevant app entry points has a clear module docstring.
- `scripts/generate_architecture_docs.py` exists and when run produces `docs/architecture.md` with the requested content.
- Plan is updated as work progresses.

