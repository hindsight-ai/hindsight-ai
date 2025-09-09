# Hindsight AI Roadmap & Execution Guide
Status: Draft (auto-generated from consolidated doc review)
Last updated: 2025-09-09

Purpose
- Provide a single, actionable roadmap translating design/requirements/ADR docs into ordered engineering work.
- Capture themes, gaps, phases, acceptance criteria, and traceability to existing docs.

Source Documents Mapped
- requirements.md (product & technical baseline)
- data-governance-orgs-users.md (governance design)
- implementation-progress-and-plan.md (current progress log)
- HINDSIGHT_FIXES_RESUME.md (recent fixes & aliasing choices)
- traefik_troubleshooting.md (infra edge cases)
- ADRs 0001–0006 (architecture decisions)

High-Level Themes
1. Data Governance & RBAC maturation
2. Frontend org-aware UX & permission gating
3. Secure, reproducible deployments (single image + runtime config)
4. Observability, auditing, and safety (audit logs, bulk ops transparency)
5. Guest/public experience & demo data
6. Type safety & consistency (TS strictness, API field normalization)
7. Performance & resilience (scope indexes, rate limiting, background jobs)
8. Defense-in-depth (future RLS, rate limiting, publish dual-control)

Gap Inventory (Condensed)
- Backend governance: incomplete invitation lifecycle, scope moves (consent), publish workflow, bulk ops execution worker, search scope tests, audit coverage.
- Frontend: lacks org switcher, membership management UI, scoped create forms, audit viewer, bulk/empty org wizard, publish/unpublish flows.
- Public demo: system account + seeded public data missing (guest mode limited value).
- TypeScript: remaining any casts; OrgContext still JS (to migrate); no strict mode.
- API: id vs memory_id alias ambiguity unresolved; scope move collision handling unspecified.
- Security: no rate limiting; RLS deferred without feature flag scaffold.
- CI: only migrations E2E; missing permission/search matrix; coverage gate absent.
- Observability: structured audit & operation progress endpoints incomplete.

Execution Phases
(Each phase is independently shippable; prioritize stability & test coverage before UX polish.)

Phase 1 (Complete / Baseline)
- Schema & basic scoped filtering (done per implementation-progress-and-plan.md).

Phase 2 (Finish Core Governance Backend)
Items:
- Invitation endpoints: create/list/resend/revoke/accept
- Scope-move endpoints (agents, memory blocks) + consent + superadmin override
- Expanded audit logging (invitations, role changes, scope moves, deletes, publish stubs)
- Search endpoint tests (guest vs user vs superadmin)
- CRUD deduplication confirmed
Acceptance:
- 100% governance endpoints return documented status codes
- Audit entries present for all sensitive actions
- Tests: permission matrix + search scope; zero leakage

Phase 3 (Frontend Org Foundations)
Items:
- Convert OrgContext to TS; add OrgProvider state (active org id or personal)
- Org switcher UI (header/sidebar)
- Update create forms (Agent/Memory/Keyword) with scope/org selection & permission gating
- Basic membership list (read-only) + roles reflected
Acceptance:
- Switching org triggers refetch & filtered lists
- Viewer role hides write controls (no 403 noise in normal usage)

Phase 4 (Membership & Invitations UI)
Items:
- Members management page (list/add/change role/remove/invite resend/revoke)
- Invitation acceptance simulation hook (pending UI or toast)
Acceptance:
- Invite flows fully E2E (pending -> accepted)
- Role changes reflected immediately in UI gating

Phase 5 (Bulk Operations Foundations)
Items:
- Backend: inventory + dry-run bulk-move & bulk-delete endpoints
- Frontend: Empty Organization wizard (inventory + dry-run UX)
- Seed system account + public demo data seeding script/migration
Acceptance:
- Dry-run returns collisions & plan structures
- Guest sees non-empty curated public dataset

Phase 6 (Execution & Background Worker)
Items:
- Background worker for bulk operations (thread/async) with resumable state
- Execute endpoints for bulk-move/delete producing operation_id
- Operation status polling UI panel
Acceptance:
- Operation progress increments; restart resilience test passes
- Audit entries for operation start/finish

Phase 7 (Publish / Unpublish Workflow)
Items:
- Request publish endpoint (owner/admin)
- Approve publish (superadmin) + unpublish endpoint
- Dual-control UI modal with confirmation guardrails
Acceptance:
- visibility_scope transitions logged & enforced (public read-only except superadmin)
- Guests see published items immediately

Phase 8 (Consent-Based Scope Moves & Notifications)
Items:
- Proposal model or reuse audit with pending state
- Approve/deny endpoints; UI notifications panel
Acceptance:
- Personal->Org move requires owner approval (or override with reason)
- Tests for consent & override paths

Phase 9 (Hardening & Type Strictness)
Items:
- Enable TS strict + noUncheckedIndexedAccess
- Remove remaining any casts (env, memory block bridging)
- API field normalization (choose `id` canonical; alias others) & MCP client alignment
- Add rate limiting middleware (guest-friendly)
Acceptance:
- tsc passes under strict
- 429 returned for aggressive guest bursts

Phase 10 (Defense & Observability Enhancements)
Items:
- Feature-flagged RLS policies (parity tests)
- Structured logging (JSON) + request IDs
- Prometheus metrics exposure (optional)
- Audit Explorer UI (filters, pagination)
Acceptance:
- RLS-on test suite green & identical result sets
- Logs include correlation id and user scope

Deferred / Optional
- Custom roles system (org-defined roles)
- Data export/import endpoints
- Publication metadata (approved_by, reason)
- External queue for operations (Celery/RQ)

Cross-Phase Testing Strategy
- Governance unit tests: permissions helpers edge cases
- Integration: list/detail/search scope filtering
- Bulk ops: dry-run vs execute parity, idempotency
- Publish: dual control, audit presence, guest visibility
- Consent moves: pending -> approved/denied, override path
- RLS parity (when flag enabled)

Traceability Table (Doc → Phase)
- data-governance-orgs-users.md: Phases 2–8, 10
- implementation-progress-and-plan.md: Phase 2 starting point
- requirements.md: Baseline (guest mode, deployment parity) → Phase 5 (public demo fulfillment)
- HINDSIGHT_FIXES_RESUME.md: API alias cleanup (Phase 9)
- traefik_troubleshooting.md: Deployment reliability (implicit baseline) supports all phases
- ADR 0001 (env.js), 0002 (single compose): baseline enabling reproducible deploys (Phase 0+)
- ADR 0003–0005: Auth & routing constraints shaping Phase 3+ UI flows
- ADR 0006: CI concurrency baseline (affects all phases)

Acceptance Criteria Summary (Immediate = Phase 2)
- Invitations + scope-move endpoints implemented
- Audit expansion completed
- Search & permission tests added (no leakage)
- CRUD duplication resolved

Open Risks & Mitigations
- Risk: Scope leakage via ad hoc queries → Mitigation: central filtering helpers + pending RLS
- Risk: Complex bulk operation partial failures → Mitigation: chunked idempotent worker + audit + progress state
- Risk: Public publishing data exfiltration → Mitigation: dual-control + audit + confirmation UX
- Risk: Type drift after rapid feature additions → Mitigation: strict TS phase scheduled (Phase 9) after core surfaces stable

Getting Started (If Resuming Mid-Phase)
1. Read implementation-progress-and-plan.md recent changes section.
2. Run migrations E2E (forward) and permission tests.
3. Implement next endpoint from Phase 2 list with tests first.
4. Update both this roadmap and implementation-progress-and-plan.md.

Update Policy
- On completing any item: update implementation-progress-and-plan.md ("What’s already implemented" + recent changes) and adjust this roadmap phase if fully delivered.

---
End of document.
