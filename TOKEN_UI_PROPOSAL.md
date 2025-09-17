# PAT Management UI Proposal

This document captures findings, suggestions, and a living progress log for improving discovery and usability of Personal Access Token (PAT) management in the Hindsight dashboard.

--

## Summary

PAT management currently lives in the user profile page at `/profile`, under the "API Tokens" section. To create or manage tokens a user must open the top-right account menu → "Edit Profile" → scroll to "API Tokens".

This proposal documents code locations, suggested UI/UX placements, tradeoffs, and an incremental implementation plan.

## Files inspected

- `apps/hindsight-dashboard/src/components/ProfilePage.tsx` — current token CRUD UI (create, rotate, revoke, list), one-time secret display.
- `apps/hindsight-dashboard/src/components/UserAccountButton.tsx` — top-right user menu that links to `/profile` ("Edit Profile") and other account actions.
- `apps/hindsight-dashboard/src/api/tokenService.ts` — client API used by the dashboard for token operations.
- `apps/hindsight-dashboard/src/App.tsx` — routing, contains `/profile` route.

## Observations

- The existing token UI is fully featured and re-usable; it is already wired to `tokenService`.
- Discovery is poor: tokens are hidden inside profile edit flow which mixes general profile settings and token management.
- The `UserAccountButton` is a convenient place to add a direct link; the header / global nav is the ideal permanent landing.

## Prioritized suggestions

1. Add an "API Tokens" link to the account dropdown (very low effort, quick win).
   - Link to `/tokens` or `/profile#tokens`.
2. Add a top-level navigation item, e.g. "Developer" → "API Tokens" or a single "API Tokens" nav item.
   - Create a canonical `/tokens` route and `TokensPage` that reuses token UI from `ProfilePage`.
3. Convert the profile page to tabs (Profile | Tokens | Security) and make Tokens a first-class tab.
4. Add a quick-create token button in the header for power users (opens modal showing one-time secret).
5. Add contextual links on pages like Agents or Integrations: "Need a PAT? Create one".

## UX details and constraints

- One-time secret must remain a one-time display and obvious copy affordance.
- Keep org-scoped tokens and org dropdown in the creation UI.
- Ensure accessibility (keyboard, aria labels) and clear confirmation steps for write-scoped tokens.

## Implementation plan (incremental)

1. Quick win: add "API Tokens" to account dropdown linking to `/profile#tokens`. (~1–2 hours)
2. Medium: extract token UI into `TokenManagement` component and create `/tokens` route. (~3–5 hours)
3. Improve: add header quick-create, and contextual links where useful. (time varies)

## Progress log (living)

- 2025-09-15: Document created. Inspected `ProfilePage.tsx`, `UserAccountButton.tsx`, `tokenService.ts`, and `App.tsx`.
- 2025-09-15: Recommended prioritized options; user asked to write everything into a markdown doc and keep it updated (this file).
 - 2025-09-15: Implemented quick win: added "API Tokens" link to account dropdown (`UserAccountButton.tsx`) that navigates to `/profile#tokens`. Added `id="tokens"` anchor to tokens section in `ProfilePage.tsx`. Ran dashboard unit tests — all passing locally.
 - 2025-09-15: Implemented quick win: added "API Tokens" link to account dropdown (`UserAccountButton.tsx`) that navigates to `/profile#tokens`. Added `id="tokens"` anchor to tokens section in `ProfilePage.tsx`. Ran dashboard unit tests — all passing locally.
 - 2025-09-15: Extracted token UI into `TokenManagement.tsx` and refactored `ProfilePage.tsx` to use it. Added canonical `/tokens` route and `TokensPage.tsx` that renders `TokenManagement`.
 - 2025-09-15: Implemented header quick-create flow: added a small header button and `QuickCreateTokenModal.tsx` for fast token creation (creates limited form, shows one-time secret, reuses `tokenService`). Hook extraction pending.
 - 2025-09-15: Separated tokens from profile settings: removed embedded `TokenManagement` from `ProfilePage.tsx` and added a dedicated "Manage API Tokens" button that navigates to `/tokens`. Updated account dropdown to link directly to `/tokens`.

## Next actions and checkpoints

- Confirm which improvement to implement first. I recommend the account dropdown link as the fastest, lowest risk.
- After confirmation, implement the change and update this document with diff summary and test notes.

## Recent changes (delta)

- Added `apps/hindsight-dashboard/src/components/TokenManagement.tsx` (reusable token UI).
- Added `apps/hindsight-dashboard/src/components/TokensPage.tsx` and registered `/tokens` in `App.tsx`.
- Added `apps/hindsight-dashboard/src/components/QuickCreateTokenModal.tsx` and a header quick-create button wired into `MainContent.tsx`.

## Next steps (short)

1. Factor the token creation logic into a small hook (e.g., `useTokenCreation`) so the modal and `TokenManagement` share behavior and error handling. (low risk)
2. Add tests for the quick-create modal (unit tests for creation flow and UI display). (medium)
3. Optionally add a top-level nav item for `/tokens` and surface the page in the main sidebar. (low)

## How I validated

- Ran dashboard Jest tests after adding the `/tokens` route; all frontend tests passed (31 suites, 188 tests).

---

*End of update.*


---

*End of initial proposal.*
