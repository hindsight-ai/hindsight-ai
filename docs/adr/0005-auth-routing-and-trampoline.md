# ADR 0005: Auth routing and root trampoline

- Status: Accepted
- Date: 2025-09-07

## Context
We need consistent, user-friendly routes that support deep links, a dedicated login page, and a predictable dashboard URL. Prior attempts at SPA-based navigation caused errors during auth state changes.

## Decision
Use `/login` as a full-screen standalone page; `/dashboard` as the main app route; `/` as a trampoline to `/dashboard` (if authenticated) or `/login` (if not and not in guest). Use `window.location.replace` for the minimal redirects to avoid router hook races. Preserve deep links by passing `rd=<current_path>` when initiating OAuth from within the app; from `/login`, always `rd=/dashboard`.

## Consequences
- Stable URLs; easy bookmarks and QA.
- No React hook mismatch errors during redirection.
- Guest flows behave predictably; session switches are clear and robust.

## Alternatives Considered
- Router-driven redirects with `useNavigate`: introduced instability under rapid auth state changes.

