# RFC 0001: About dialog — entry point and light polish

- Status: Proposed
- Date: 2026-04-28
- Branch: `feature/about-window`

## Context

The dashboard already ships a fully-functional `AboutModal.tsx` (TS, Tailwind,
Portal-based) wired to `GET /build-info` and to `import.meta.env.VITE_*` build
metadata. The modal also embeds a Contact Support form that posts to
`POST /support/contact`. App state, the `<AboutModal/>` mount, and the
prop-drill `App → Layout → MainContent` for `onOpenAbout` already exist.

The only missing piece is a user-facing trigger. `MainContent` accepts
`onOpenAbout` and silently drops it; `UserAccountButton`'s dropdown has
Donate / Profile / API Tokens / Manage Organizations / Sign Out — but no
"About" entry. The dialog is therefore unreachable from the UI.

## Decision

Add an "About" entry to the user-account dropdown that opens the existing
modal, by extending the prop drill that is already half-built. Apply light
polish to the dialog so the build-info table and the Contact Support form
read as two clearly separated regions instead of a single dense column.

### Wiring

1. `UserAccountButton` accepts an optional `onOpenAbout?: () => void` prop.
   Render a new menu item ("About Hindsight AI") above Sign Out. Style and
   icon match the existing items (Profile / API Tokens / etc.).
2. `MainContent` passes its already-received `onOpenAbout` into
   `<UserAccountButton onOpenAbout={onOpenAbout} />`. No change to the
   `Layout`/`App` plumbing.

The state stays in `App.tsx` so the dialog survives anywhere `Layout` is
mounted. No new context is introduced.

### Light polish (`AboutModal.tsx`)

Scope-limited; keep the file shape and APIs.

- Promote the section structure: render Build Info (Backend + Frontend) as
  one card, and Contact Support as a separate card below it, with a clear
  visual divider.
- Tighten the build-info rows: two columns (label / value) on a subtle
  background, monospace for `build_sha` and `image_tag`, friendly format for
  `build_timestamp` (ISO is fine; just trim sub-second noise if present).
- Add a small "Copy diagnostics" button that copies the full backend +
  frontend block as plain text — useful when filing an issue out-of-band.
- Move "Open mail app instead" next to "Contact Support" with consistent
  button sizing; keep the mailto fallback behaviour.
- A11y: focus the dialog on open, trap focus, close on `Esc`, restore focus
  on close. Use `role="dialog"` + `aria-modal="true"` + `aria-labelledby`.
- Loading skeleton replaces the spinner-only state; error banner uses the
  existing red/yellow Tailwind tokens already present in the codebase.

### Out of scope

- No backend changes. `/build-info` and `/support/contact` stay as-is.
- No new env vars or build-arg pipeline changes. ADR 0001 (runtime
  `env.js`) explicitly does not cover build SHA — `VITE_BUILD_SHA` is
  build-time-baked on purpose, since it identifies which build is running.
- No redesign of the user-account dropdown beyond adding one entry.
- No changes to `Layout` / `App` wiring beyond the one-line MainContent
  forward.

## Alternatives considered

- **Status quo (do nothing).** Rejected: the dialog is unreachable.
- **Move state into a context.** Rejected: state lives in one place and is
  consumed in one place; one prop is simpler than a provider.
- **Trigger from the topbar header instead of the dropdown.** Rejected:
  topbar real estate is contested (org switcher, Get Started, notifications,
  account). The user-account dropdown is the conventional home for "About".
- **Full redesign of the dialog.** Rejected: the existing component already
  matches the codebase's Tailwind/Portal idiom; rewriting it would churn
  with no user-visible benefit beyond what "light polish" provides.

## Consequences

- Users can open About from the account menu, see backend + frontend build
  info, copy diagnostics, and reach support — same surface they had before
  the UI refactor, with the bonus support flow.
- One small new prop on `UserAccountButton`. No public API of any other
  component changes.

## Verification

- Manual: open dropdown → click About → backend + frontend sections render
  with real values in dev (or "unknown" with no warning when env vars are
  unset). Click Copy diagnostics → clipboard has plain-text dump. Close
  with `Esc` and with the X button. Focus restored to the trigger button.
- Existing Jest tests (`memoryService.misc.test.ts`,
  `memoryService.401.test.ts`) continue to pass.
- No new tests required for the menu wiring (one prop drill); add a small
  Jest test that the dropdown renders the About entry and calls the
  callback when clicked.
