# RFC 0002: UI/UX audit — bugs, polish, and responsive fixes

- Status: In progress (rev 2 after multi-agent review)
- Date: 2026-04-28
- Branch: `feature/about-window`
- Method: Playwright drive of `localhost:3010` (DEV_MODE) at three viewports
  (desktop 1440×900, tablet 768×1024, mobile 375×812). Screenshots in
  `docs/rfcs/0002-audit-screenshots/{desktop,tablet,mobile,interactions}/`.
  All screenshots prefixed with the route number; full-page variants captured
  for desktop. Re-running after fixes lets us diff frame-for-frame —
  but only after the script's noise mitigations land (see "Audit-script
  fixes" below).

## Implementation status

Updated as PRs land. **Open** = PR up, awaiting review/merge. **Pending** =
no PR yet.

| Finding | Severity | Status | PR | Notes |
|---|---|---|---|---|
| L4 — VITE build args | low | Open | [#51](https://github.com/hindsight-ai/hindsight-ai/pull/51) | Bundled with audit infra (this RFC + skill + RFC 0001 About dialog). |
| H3 — page-title route map | high | Open | [#52](https://github.com/hindsight-ai/hindsight-ai/pull/52) | 3-line fix; adds `/tokens` and `/memory-optimization-center`. |
| M6 — Button primitive (token) | medium | Open | [#53](https://github.com/hindsight-ai/hindsight-ai/pull/53) | New `<Button variant="primary">` + migrates `/agents` CTAs. Prerequisite for H1/H2. |
| H4 — GetStarted seen-flag | high | Open | [#54](https://github.com/hindsight-ai/hindsight-ai/pull/54) | Co-landed with M5. |
| M5 — Esc + backdrop dismiss | medium | Open | [#54](https://github.com/hindsight-ai/hindsight-ai/pull/54) | Co-landed with H4. |
| H1 — Legacy classes (6+ files) | high | Pending | — | Consumes M6's `<Button>`. RFC suggests possibly splitting into pages-vs-modals PRs. |
| H2 — Empty Tailwind layer | high | Pending | — | Pair with H1 (same file group). |
| M1 — Scroll model rewrite | medium | Pending | — | Touches `MainContent.tsx`; manual smoke-test of every header-anchored popover required. |
| M2 — OrgSwitcher truncate | medium | Pending | — | Lands after M1. |
| M3 — Tokens table overflow | medium | Pending | — | Lands after M1. |
| M4 — Sidebar drawer width | medium | Pending | — | Lands after M1. |
| L1 — Console error triage | low | Pending | — | Needs full-capture audit run first to decide promotion. |
| L2 — Stat card icon style | low | Pending | — | Polish. |
| L3a — Refresh aria-label | low | Pending | — | Polish. |
| L3b — Notification icon | low | Deferred | — | Punted: needs product input. |

**Audit infrastructure** (lands in #51): the `.claude/skills/ui-ux-audit/`
skill, screenshot baseline at `docs/rfcs/0002-audit-screenshots/`, the
GetStarted aria-label contract test. Re-run the audit script after each
finding lands; `findings.json` should shrink by the named entries.

## Executive summary

The audit surfaced one **broken style regression** affecting at least
six components (Consolidation, Pruning, plus four modals/lists), a
**page-title bug** affecting two routes (Tokens, Memory Optimization
Center), a **GetStarted-modal "seen-flag" bug** that the original a11y
fix would silently make worse, a **scroll model** that hurts mobile
and accessibility, and several **responsive-layout** problems. Several
empty-state CTAs are styled inconsistently with header CTAs.

Total findings: 14. Severity: 4 high · 6 medium · 4 low.

Compared to rev 1: H1 blast radius expanded from 2 to 6+ files; new
H4 covers a latent bug in the original M5 fix; M1 grew to enumerate
hidden coupling (z-index, inner-scroller chaining, scroll-reset
useEffect); M3 trimmed; M5 trimmed; L3 split; implementation order
rewritten; Tailwind v4 hedge removed (it is the current version).

## Findings

### H1. Legacy class names render unstyled across 6+ components
**Severity:** high · **Routes:** all routes that mount the affected components
**Screens:** `desktop/07-consolidation.png`, `desktop/09-pruning.png`,
`interactions/consolidation-broken-toolbar.png`,
`interactions/pruning-broken-form.png`

The audit visually flagged Consolidation and Pruning because they show
unstyled empty-states most loudly. Grep against `apps/hindsight-dashboard/src`
shows the same dead class names referenced from at least these files:

- `components/ConsolidationSuggestions.tsx`
- `components/ConsolidationSuggestionDetail.tsx`
- `components/PruningSuggestions.tsx`
- `components/MemoryBlockList.tsx`
- `components/AddMemoryBlockModal.tsx`
- `components/AddKeywordModal.tsx`

(Also worth checking: `components/BulkActionBar.tsx`,
`components/MemoryBlockTable_old.tsx`, `components/MemoryBlockTable_new.tsx`,
`components/AddAgentDialog.tsx` — flagged by reviewer grep but not
visually probed by the audit.)

Affected class names include: `memory-block-list-container`,
`bulk-actions-bar`, `filter-controls`, `delete-selected-button`,
`pruning-params-section`, `pruning-params-form`, `form-group`,
`param-hint`, `data-table-container`, `score-badge`,
`action-icon-button`, `add-button`, `empty-state-message`,
`loading-message`, `error-message`.

`MemoryBlockList.css` still exists but only defines `.search-score-badge`;
the rest were removed. The audit script's heuristics (scroll, overflow,
console errors) cannot detect "looks unstyled", so the script gave
several of these files a green light. Treat the visible cases as the
tip — the full list of consumers must be enumerated **before** any fix
PR is opened, otherwise H1 ships and three more pages remain broken.

**Verification step before any fix:**
```sh
grep -rln 'memory-block-list-container\|bulk-actions-bar\|pruning-params-section\|delete-selected-button\|filter-controls\|param-hint\|form-group\|data-table-container\|score-badge\|action-icon-button\|add-button\|empty-state-message\|loading-message\|error-message' apps/hindsight-dashboard/src --include='*.tsx' --include='*.ts'
```
Every file in that list must either be in scope or have an explicit
"out of scope" justification in the PR description.

**Fix:** Restyle each consumer with the same Tailwind tokens used by
`MemoryBlocksPage` (`px-4 py-2 rounded-md border ...`). Keep behaviour
and prop API unchanged. Add behaviour-level tests, not snapshot tests
(snapshots of Tailwind class strings get rubber-stamped on update);
assert that the toolbar buttons are real `<button>` elements, that the
status filter is a labelled `<select>` with the expected options, etc.

### H2. Pruning page renders with no styling — same root cause as H1
**Severity:** high · **Routes:** `/pruning-suggestions`
**Screens:** `desktop/09-pruning.png`, `interactions/pruning-broken-form.png`

Same legacy-class root cause as H1; treat as part of the H1 sweep. Use
a 3-column `grid md:grid-cols-3 gap-4` for the parameter inputs at
desktop, single-column on mobile. Add `min` attributes on the number
inputs to prevent negative values (currently no validation visible).

### H3. Wrong page title on Tokens & Memory Optimization Center
**Severity:** high · **Routes:** `/tokens`, `/memory-optimization-center`
**Screens:** `desktop/13-tokens.png`, `desktop/10-optimization.png`

Both pages show the page header as `Dashboard` / "Overview of your AI
memory management system." The title bar lies about which page you're on.

**Root cause:** `App.tsx` `getPageTitle` route-map (lines 287-298) is
missing entries for `/tokens` and `/memory-optimization-center`, and the
fallback returns `'Dashboard'` (line 301).

**Fix:** Add the two entries; change the fallback to `''` so missing
routes render no title row instead of the wrong one. Also gate the
`<h2>` and `<p>` rendering on `title` truthiness in `MainContent.tsx:104`
so an empty title doesn't take vertical space. Update
`defaultDescriptions` in `MainContent.tsx` (line 47) to add matching
descriptions.

```ts
'/tokens': 'API Tokens',
'/memory-optimization-center': 'AI Optimization',
```

Skip the type-tightening that was in rev 1 — it's a separate refactor.

### H4. GetStarted "seen" flag is set on every dismissal, including accidental ones
**Severity:** high (latent bug in the rev 1 M5 fix; would ship a worse bug than the one it solves)
**Routes:** `/dashboard` (auto-shown first time)
**Screens:** `interactions/getstarted-modal-on-load.png`

`App.tsx:80-83` `handleCloseGetStarted`:
```ts
const handleCloseGetStarted = useCallback(() => {
  markGetStartedSeen();          // <-- writes localStorage unconditionally
  setShowGetStarted(false);
}, [markGetStartedSeen]);
```

The original M5 fix proposed binding Esc and backdrop click to
`onClose`. Combined with the unconditional `markGetStartedSeen()`, an
accidental Esc on first load — a high-misfire key — would write
`hindsight.get-started.<email>` to localStorage and the modal would
**never appear again** for that user, with no in-app recovery.

**Fix:** Decouple "dismissed" from "acknowledged" before adding the
new dismiss affordances:

1. Only call `markGetStartedSeen()` when the user clicks **Got it**,
   not on Esc, backdrop click, or the X button.
2. Optionally: add a "Don't show again" checkbox in the footer if
   single-shot suppression is genuinely desired.

This is a prerequisite for M5 and must land in the same PR.

---

### M1. Page-level scroll is dead; the rewrite has hidden coupling
**Severity:** medium · **Routes:** all (Analytics is the most visible offender)
**Screens:** `desktop/06-analytics-fullpage.png`

`MainContent.tsx:69` sets `<main class="flex-1 ... overflow-hidden">` and
the inner content lives in `<div ref={scrollRef} class="flex-1 min-h-0
overflow-y-auto p-4">`. Result: `document.documentElement.scrollHeight ===
window.innerHeight`, and the actual scrolling happens inside a div. This
breaks four things:

1. Mobile "tap status bar to scroll to top" (iOS/Android target the
   document scroller, not nested overflow containers).
2. Browser scroll restoration on back/forward.
3. Mouse wheel when the cursor is over the header / sidebar.
4. Overscroll bounce / pull-to-refresh feels janky.

**Fix:** Promote scrolling to the document. Drop `overflow-hidden` on
`<main>` and `overflow-y-auto` on the inner div. Make the page header
`position: sticky; top: 0` and the sidebar `lg:fixed lg:inset-y-0` so
neither scrolls with content.

**Hidden coupling that must land in the same PR (rev 2 addition):**

- **Z-index ladder.** Sticky header at `z-10` will be covered by the
  sidebar (`z-50`) and modals (Portal `z-50`/`z-[9999]`) — that's
  intended. But `OrganizationSwitcher` opens a dropdown at absolute
  `z-20` *inside* the header. Once `<main>` becomes the document
  scroller and the header is sticky, that dropdown's stacking context
  may clip against the new sticky parent. Manually open every
  header-anchored popover (OrgSwitcher, NotificationBell, UserAccountButton
  menu) at desktop and mobile after the fix and confirm none are
  clipped. Document the new z-index ladder.

- **Scroll-chaining on inner scrollers.** Components inside the page
  use `max-h-[70vh] overflow-y-auto` (`MemoryBlockDetailModal:160`),
  `max-h-80 overflow-y-auto` (`OrganizationManagement:883`), and
  smaller nested lists. Mouse-wheel over these will chain to the
  document mid-list. Add `overscroll-contain` to each inner scroller
  in the same PR; smoke-test every nested list.

- **Scroll-to-top on route change.** `MainContent.tsx:23-29` currently
  calls `scrollRef.current.scrollTo(...)` first and falls back to
  `window.scrollTo`. Today the ref-path runs and the fallback never
  fires. After M1, the ref-path will silently no-op (the div no longer
  scrolls). **Delete the `scrollRef` branch in the same PR**; rely
  solely on `window.scrollTo`.

This is no longer an "M1 = touch one file" change. The PR description
must enumerate the z-index ladder, every inner scroller it visits, and
the scroll-reset useEffect deletion.

### M2. Mobile header — OrgSwitcher overlaps NotificationBell
**Severity:** medium · **Viewports:** mobile (375px) · **Routes:** all
**Screens:** `mobile/02-dashboard.png` and most other `mobile/*.png`

The "Personal" pill text wraps under the bell icon at 375px. Top row in
`MainContent.tsx:73` is `flex items-center justify-between gap-2` with
`<OrgSwitcher>` consuming `flex-1 min-w-0`, but the OrgSwitcher's pill
expands to its content width without truncation when the right cluster
is wide.

**Fix:** Add `truncate` and a tight `max-w` on the OrgSwitcher trigger
at small breakpoints. Move "Get Started" off the top header on mobile
(it's already hidden ≥sm by `hidden sm:inline` — verify it's not the
cause; if it shows on mobile, move it into the user-menu instead).

Note: this fix is sensitive to which element is the scroll ancestor;
land it **after** M1 so the sticky-header layout is in place first.

### M3. Tokens table overflows the container on tablet & mobile
**Severity:** medium · **Routes:** `/tokens` · **Viewports:** tablet, mobile
**Screens:** `tablet/13-tokens.png`, `mobile/13-tokens.png`

The `<table>` has 9 columns (Name, Token, Scopes, Org, Status, Created,
Last Used, Expires, Actions) with no `overflow-x-auto` wrapper. At 768px
the Actions column is clipped. At 375px the table becomes essentially
unusable.

**Fix:** Wrap the table in `<div class="overflow-x-auto -mx-4 sm:mx-0">`
to allow horizontal scroll within the page. Truncate token preview to
8 chars with a `title` tooltip showing the full value. Drop the
mobile-card-list swap from the rev 1 plan — the overflow wrapper alone
solves the user complaint and the card-list is a separate UI surface
that doubles maintenance.

Note: the actual file is `components/TokenManagement.tsx` (not
`TokensPage.tsx`, which is a thin wrapper). Verify before opening the PR.

### M4. Sidebar drawer too wide on mobile
**Severity:** medium · **Viewports:** mobile · **Screens:** `interactions/mobile-sidebar-open.png`

The drawer occupies ≈340px of a 375px viewport, leaving only 35px of the
underlying page visible. Standard pattern is ≤80% viewport width.

**Fix:** Set `w-72 max-w-[80vw]` on the drawer. Add `aria-modal="true"`
on the drawer itself. Tap outside should close (same handler as the
existing mask click).

### M5. GetStartedModal does not dismiss on backdrop click or Escape
**Severity:** medium · **Routes:** `/dashboard` (auto-shown first time)
**Screens:** `interactions/getstarted-modal-on-load.png`
**Depends on:** H4 (must land first or in the same PR)

Probed by the audit script: backdrop click does not close the modal,
and Escape is not handled. The user must reach the X (top-right) or
scroll to "Got it" (bottom). The modal's body is taller than the
viewport, so on small screens the close affordance scrolls away.

**Fix:**
1. Bind `keydown` on `Escape` → `onClose`.
2. Click on the overlay (outside the dialog) → `onClose`.

Items 3, 4, 5 from rev 1 ("Skip for now" link, MCP-client persistence
change, "What's new" tooltip replacement) are removed — they're
onboarding-flow redesign, not a11y fixes. Open separate findings if
they matter.

### M6. Empty-state CTA style mismatches header CTA style
**Severity:** medium · **Routes:** `/agents`, others with empty states
**Screens:** `desktop/05-agents.png`

On `/agents` the page-header CTA "Create Agent" is a black/dark filled
button, while the empty-state "Create Agent" 30 pixels below is a blue
filled button. Same label, same action, two different colours. Reads
as different actions to a new user.

**Fix:** Define a single primary-button token (`btn-primary` Tailwind
component class via `@apply` or a `<Button variant="primary">` shared
component). Use it for both CTAs. The dark variant should be reserved
for destructive or contextual actions.

**Sequencing note:** land M6 **first**, before H1/H2's restyle, so the
restyle consumes the new token instead of inventing per-file primary
styling. Otherwise H1/H2 ship one design, M6 ships another, and the
two diverge immediately after the restyle. See "Implementation order".

---

### L1. Console errors on multiple pages
**Severity:** low (may need promoting after a real sweep)
**Viewports:** all · **Source:** `findings.json` per route.

The rev 1 audit script truncated console errors to the first 3 messages
and rated all of them "low". Before closing this RFC, run the audit
with full console capture and triage what's actually being logged —
React 19 act() warnings, missing key props, and invalid hook calls
can mask behavioural bugs. If anything behavioural turns up, promote
to its own finding.

### L2. Stat card icon style inconsistency
**Severity:** low · **Routes:** `/dashboard`
**Screens:** `desktop/02-dashboard.png`

"Total Agents" uses a stylised emoji-like person icon; "Memory Blocks"
uses an outline icon; "Conversations" uses a chat bubble. Different
stroke weights and fill styles.

**Fix:** Standardise on `lucide-react` (or whatever icon set the rest
of the app uses). Defer until a user reports it; pure polish.

### L3a. Refresh icon has no accessible label
**Severity:** low · **Routes:** all
**Screens:** any `desktop/0*-*.png`

The refresh icon on the page-header row has no `aria-label`. Screen
readers can't find it; sighted users can't tell what it does until they
click.

**Fix:** Add `aria-label="Refresh data"`. One line.

### L3b. Page-header clock vs OS clock
**Severity:** low (defer — needs product input)
**Routes:** all

Rev 1 proposed dropping the page-header clock because "the OS already
shows time". But the clock may be doing work the OS can't (e.g.
matching the server's timezone, not the user's). Don't change without
checking with whoever decided to add it.

### L4. About dialog frontend section shows "unknown" in local dev
**Severity:** low · **Routes:** About dialog · **Found by self-test**
**Screens:** `interactions/about-modal-open.png`

The Frontend Dashboard section shows `unknown` for Version / Build SHA /
Build / Image Tag. The backend section shows real values. Cause:
`docker-compose.dev.yml`'s `hindsight-dashboard` block doesn't pass the
`VITE_*` env vars as build args to the Dockerfile.

**Fix:** Add `args:` block to the dashboard service in
`docker-compose.dev.yml` mapping each `VITE_*` env to a build arg so
the Dockerfile's `ARG VITE_BUILD_SHA` etc. (Dockerfile lines 7-11) get
values. Two lines, no UI surface, can ship today.

---

## Implementation order (rev 2)

The rev 1 order put L4 in step 3 and M1 in step 6; rev 2 fronts the
zero-risk standalone fixes and lands the scroll-model rewrite **before**
the responsive sweep so M2/M3 don't get patched against the wrong
coordinate system.

1. **L4** — VITE build args in `docker-compose.dev.yml`. Two-line PR,
   ships today, unblocks accurate About-dialog output during every
   subsequent review.
2. **H3** — page-title route map. Strict bug fix, ≤10 lines, no design
   tradeoffs. Standalone PR.
3. **M6 (token only)** — define `<Button variant="primary">` (or
   `btn-primary` `@apply` class) and migrate `/agents` empty-state +
   header to it as the proof. No other consumers yet — but the token
   exists for H1/H2 to consume in step 5.
4. **H4 + M5** — decouple seen-from-dismissed in
   `App.tsx:80-83`, then add Esc and backdrop dismissal to
   `GetStartedModal`. Co-land as one PR; H4 alone has no user-visible
   change so doesn't need its own.
5. **H1 + H2** — restyle every legacy-class consumer (full list per
   the H1 grep). Split into two PRs by file group if reviewable: pages
   (Consolidation, Pruning) vs modals (AddMemoryBlock, AddKeyword,
   plus any `*Detail` / `*Table` / `MemoryBlockList`). Use the M6 token
   from step 3.
6. **M1** — scroll model rewrite. Single PR; PR description must
   enumerate every inner scroller it visits (`overscroll-contain`),
   the z-index ladder, and the `MainContent.tsx:23-29` scroll-reset
   change. Manual smoke-test every header-anchored popover before
   merging.
7. **M2, M3, M4** — responsive sweep, now that M1 is the baseline.
   `truncate` on OrgSwitcher (M2), `overflow-x-auto` on Tokens table
   (M3), `w-72 max-w-[80vw]` on sidebar drawer (M4).
8. **L2, L3a** — icon standardisation + refresh `aria-label`. Last.
9. **L1** — console-error sweep + triage.
10. **L3b** — punt until product input.

## Audit-script fixes (prerequisite for the diff workflow)

The rev 1 verification section claimed the script's screenshots could
be diffed frame-for-frame with `magick compare`. They can't, until
the script removes non-deterministic content. Before relying on the
diff workflow:

- **Mock `Date.now()`** via `page.addInitScript`. `LastUpdatedLabel.tsx:19`
  renders `lastUpdated.toLocaleTimeString(...)` in every page header,
  so a screenshot taken one minute apart from the baseline produces
  pixel diffs on the title row.
- **Settle animations.** `animate-pulse` skeletons (e.g.
  `ConsolidationSuggestions:382`) cycle indefinitely. Before
  screenshotting, either `await page.waitForFunction(() => !document.querySelector('.animate-pulse'))`
  or override CSS to disable animations.
- **Mask known-volatile regions.** Notification toasts, the avatar
  initial, lastUpdated labels — either CSS `visibility: hidden` via
  `addStyleTag` or screenshot `clip:` to exclude them.
- **Add a "page looks unstyled" heuristic.** Sample computed-style
  borders/backgrounds on a fixed selector set; if the count of
  styled elements drops below a threshold for a route, flag it. The
  current heuristics (scroll, overflow, console errors) cannot detect
  H1/H2-class regressions.
- **Move `AUDIT_OUT` default off the RFC-numbered path.** Default to
  `/tmp/ui-audit/` so the skill is reusable across future RFCs without
  silently overwriting `0002-audit-screenshots`. The current default
  bakes RFC 0002 into a "reusable" tool.
- **Pin the GetStarted close-button selector.**
  `aria-label="Close get started guide"` is a contract — add a Jest
  test on `GetStartedModal.tsx` that asserts the label, otherwise a
  rename silently breaks the audit's modal-suppression path.

These changes are mechanical edits to
`.claude/skills/ui-ux-audit/audit.mjs` and `SKILL.md`. Land them in
the same PR as L4 (step 1 of the implementation order) so the diff
workflow is trustworthy from PR #2 onward.

## Wire the audit into CI

The skill is described as reusable but rev 1 didn't propose CI
integration. Without it, dead-class regressions (the H1 root cause)
re-enter on the next refactor with no automated signal.

**Proposed:** GitHub Actions job that runs
`node .claude/skills/ui-ux-audit/audit.mjs` against a Playwright-driven
preview build of the PR's branch, uploads the screenshots as an
artifact, and runs `magick compare -metric AE -fuzz 5%` against the
`main` baseline. Fail the job if any image's pixel-AE exceeds a
configurable threshold *and* the baseline is older than 7 days (to
avoid breaking unrelated PRs).

This is a separate PR after step 6 of the implementation order — the
audit-script fixes (deterministic clock, animation freeze) must land
first, otherwise CI will fail on every PR for noise reasons.

## Verification & "before/after" comparison

After the audit-script fixes ship:

```bash
# Snapshot the current screenshots as the baseline
for d in desktop tablet mobile interactions; do
  cp -r "docs/rfcs/0002-audit-screenshots/$d" "docs/rfcs/0002-audit-screenshots/before-$d"
done

# Apply your fix, then re-run
node .claude/skills/ui-ux-audit/audit.mjs

# Visual diff (requires ImageMagick)
for f in docs/rfcs/0002-audit-screenshots/desktop/*.png; do
  base=$(basename "$f")
  magick compare -metric AE -fuzz 5% \
    "docs/rfcs/0002-audit-screenshots/before-desktop/$base" "$f" \
    "/tmp/diff-$base" 2>&1 || true
done
```

Override the target with `AUDIT_BASE_URL` to audit staging or another
deployment; override `AUDIT_OUT` to write somewhere outside the repo.

## Out of scope

- Backend changes (`/build-info`, `/support/contact`, etc.).
- Reskinning the sidebar dark theme.
- Replacing native `<select>` with a custom combobox component.
- Adding new pages.
- Onboarding-flow redesign (skip-for-now link, "What's new" tooltip,
  MCP-client persistence model).
- Multi-step flow recordings (e.g. "create token → use in CLI" video
  evidence). The current audit captures isolated route + interaction
  snapshots; flow coverage is its own RFC.

The Tailwind v3→v4 hedge from rev 1 was wrong — `package.json` shows
`tailwindcss@^4.1.12` is the current version, not migration-in-flight.
The utility classes proposed for H1/H2 (`px-4 py-2 rounded-md border`)
are stable in v4.
