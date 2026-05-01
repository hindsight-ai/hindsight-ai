---
name: ui-ux-audit
description: Drives the running Hindsight dashboard with Playwright across desktop/tablet/mobile viewports, captures screenshots of every route and key interactions, probes scroll behaviour and horizontal overflow, and writes a findings.json. Use when the user asks for a UI audit, UX review, visual diff, before/after comparison, or "screenshot the dashboard". Output lands in docs/rfcs/0002-audit-screenshots/ by default so the same paths can be reused for diffing after fixes.
---

# UI/UX audit

A repeatable Playwright audit of the Hindsight dashboard. Captures
screenshots of every route at three viewports, plus a small set of
interaction probes (user menu, About modal, GetStarted modal, mobile
drawer, legacy-class regression close-ups). Output paths are stable so
re-running after a fix produces a frame-for-frame diff against the
previous run.

## When to run this

Use this skill whenever the user asks to:

- Audit / review the dashboard UI/UX
- Take screenshots across breakpoints
- Compare before/after of a UI change
- Reproduce a visual bug at a specific viewport
- Verify responsive behaviour

For one-off "screenshot a single page" requests this is overkill; just
write a minimal Playwright snippet inline. Use this skill when the user
wants coverage across the whole dashboard.

## Prerequisites

1. The local stack must be running and the dashboard reachable. The
   default URL is `http://localhost:3010`. Check with
   `curl -sI http://localhost:3010 | head -1`.
2. Playwright must be installed in `apps/hindsight-dashboard/node_modules`.
   The script auto-checks this and prints the install command if missing:
   ```sh
   (cd apps/hindsight-dashboard && npm install --no-save playwright && npx playwright install chromium)
   ```
3. The dashboard must accept dev login (`DEV_MODE=true` in `.env`).
   Without it, every route redirects to the OAuth flow and the audit
   captures only the login page.

## How to run

From the repo root:

```sh
node .claude/skills/ui-ux-audit/audit.mjs
```

That writes (default `AUDIT_OUT=/tmp/ui-audit`):

```
/tmp/ui-audit/
├── desktop/         01-root.png … 13-tokens.png   (+ -fullpage.png)
├── tablet/          01-root.png … 13-tokens.png
├── mobile/          01-root.png … 13-tokens.png
├── interactions/    user-menu-open.png, about-modal-open.png,
│                    getstarted-modal-on-load.png, mobile-sidebar-open.png,
│                    consolidation-broken-toolbar.png,
│                    pruning-broken-form.png, …
└── findings.json    structured array of automated findings
```

To capture a baseline that ships alongside an RFC, point `AUDIT_OUT`
into the repo: `AUDIT_OUT=docs/rfcs/0003-my-rfc/screenshots node ...`.

Total runtime: ~60–90 s on a warm Vite build.

## Configuration

Override defaults with env vars:

| Var              | Default                                         | Purpose                                  |
|------------------|-------------------------------------------------|------------------------------------------|
| `AUDIT_BASE_URL` | `http://localhost:3010`                         | Where the dashboard is served            |
| `AUDIT_OUT`      | `/tmp/ui-audit`                                 | Where screenshots and findings.json land. Set to `docs/rfcs/<NNNN>-audit-screenshots` when capturing a baseline alongside a specific RFC. |
| `AUDIT_PHASE`    | `all`                                           | `routes` (sweep only) or `interactions` only |

Examples:

```sh
# Compare against staging instead of local
AUDIT_BASE_URL=https://staging.hindsight-ai.com \
AUDIT_OUT=/tmp/staging-audit \
node .claude/skills/ui-ux-audit/audit.mjs

# Just re-run the interaction probes after a modal change
AUDIT_PHASE=interactions node .claude/skills/ui-ux-audit/audit.mjs
```

## Before/after diff workflow

To compare the current screenshots against a previous run, copy the
working set to a "before" snapshot first, then re-run:

```sh
# Snapshot the current screenshots as the baseline
for d in desktop tablet mobile interactions; do
  cp -r "docs/rfcs/0002-audit-screenshots/$d" "docs/rfcs/0002-audit-screenshots/before-$d"
done

# Apply your fix, then re-run
node .claude/skills/ui-ux-audit/audit.mjs

# Visual diff (requires ImageMagick)
for f in docs/rfcs/0002-audit-screenshots/desktop/*.png; do
  base=$(basename "$f")
  magick compare -metric AE \
    "docs/rfcs/0002-audit-screenshots/before-desktop/$base" "$f" \
    "/tmp/diff-$base" 2>&1 || true
done
```

## What the script catches automatically

The probe heuristics are intentionally narrow (false positives are worse
than missed issues — humans reading screenshots do most of the work):

- **Page does not scroll** — `documentElement.scrollHeight > viewport`
  but `window.scrollY` stays 0 *and* no inner scroller moves.
- **Horizontal overflow** — `documentElement.scrollWidth > viewport`.
- **Page may be unstyled** — fewer than 30% of interactive elements in
  `<main>` have computed border / background / shadow. Catches the
  legacy-class regression class (H1/H2 in RFC 0002).
- **Console errors** — non-`error` messages are ignored.
- **HTTP ≥ 400** on the navigated route.
- **GetStarted modal a11y** — backdrop click and Escape are both probed
  on first dashboard load.

Anything else (wrong page titles, layout bugs, design inconsistencies)
is found by **looking at the screenshots**. The script generates them;
you read them.

## Determinism

The script injects two `addInitScript` hooks into every browser
context before any app code runs:

1. **Frozen `Date`.** `Date.now()` and `new Date()` (no args) return a
   fixed instant (`FROZEN_INSTANT` near the top of `audit.mjs`). This
   prevents `LastUpdatedLabel.tsx`'s `toLocaleTimeString` clock from
   producing pixel diffs between runs taken minutes apart.
2. **Animation freeze.** A global stylesheet sets
   `animation: none !important; transition: none !important` so
   `animate-pulse` skeletons and dropdown transitions don't sample at
   different frames between runs.

Without these, `magick compare` will report thousands of pixel deltas
per page even when nothing meaningful changed. If a test needs the
real clock or animations, override `FROZEN_INSTANT` or remove the
init scripts in a forked context.

## Updating routes

Routes live in the `routes` array near the top of `audit.mjs`. When a
new page is added under `App.tsx`, append it here so the audit covers
it. Numbering convention: keep `NN-name` order matching the sidebar so
filenames sort the way the sidebar reads.

## Updating interaction probes

The interaction probes live in `runInteractionSweep`. Each one is
self-contained: a new context, a goto, suppress GetStarted, take the
shot, close the context. To add a new probe, model it on the user-menu
probe — robust selectors (avoid `nth-child`), explicit `waitForTimeout`
after async-rendered overlays, and a `note(...)` call when the
expected element is missing so regressions show up in `findings.json`.

## Known caveats

- **Avatar selector heuristic.** The user account button is matched by
  "rounded-full div containing a single uppercase letter". If the user's
  email starts with a non-ASCII char, the regex `/^[A-Z0-9]$/` won't
  match. Override by adding the specific initial.
- **localStorage suppression for GetStarted.** Keys are `hindsight.get-started.<email-or-default>`.
  If `App.tsx`'s storage key scheme changes, update the
  `suppressGetStarted` evaluator.
- **Networkidle wait** can hang for up to 15 s on routes with persistent
  WebSocket activity (notifications). The script catches the timeout
  and proceeds; expect occasional slow runs.
