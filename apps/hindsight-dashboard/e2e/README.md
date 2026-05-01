# E2E Tests (Playwright)

End-to-end tests for the Hindsight dashboard — covering whole-stack user journeys
that the existing 304 frontend component tests + 875 backend integration tests
cannot exercise (because each tier mocks the other side).

Tracker: **umbrella #96**. Full RFC: see umbrella body.

---

## Quick start

```bash
# From this directory
bun install                                # installs @playwright/test
bunx playwright install chromium           # browser binary

# Run all tests (auto-starts backend + frontend)
bun run e2e

# Or run just the smoke tier
bun run e2e -- --grep @smoke

# UI mode (interactive)
bun run e2e:ui
```

Prerequisites:

- **Postgres** must be reachable at `localhost:5432` with the credentials in
  `.env` (or matching env vars). Spin one up via `docker-compose up -d db`
  from the repo root.
- **Migrations** must be applied: `cd apps/hindsight-service && uv run alembic
  upgrade head`. This is automated in CI; locally you run it once.

The Playwright `webServer` config auto-starts the backend (`uvicorn` on :8000)
and the frontend (`vite` on :3000) — `reuseExistingServer: true` means if you
already have them running, Playwright reuses them.

---

## Patterns

### Authenticate as a specific user

```ts
import { asUser } from '../helpers/auth';
import { provisionUser } from '../helpers/provision';
import { temail } from '../helpers/runId';

const email = temail('alice');
await provisionUser(page, email, 'Alice');  // pre-approves beta access
await asUser(page, email, 'Alice');
// All subsequent requests on `page` carry x-auth-request-email + x-auth-request-user.
```

The backend resolves these headers via the same code path the 875 backend tests use.
**Do NOT enable `DEV_MODE=true`** — that hardcodes `dev@localhost` server-side and
makes header injection silently no-op.

`provisionUser` is needed because newly-created users default to
`beta_access_status='not_requested'`, and the dashboard redirects such users to
`/beta-access/request` instead of rendering the main app. The helper uses the
admin email `e2e-admin@e2e.local` (configured via `BETA_ACCESS_ADMINS` env var
in `.github/workflows/e2e.yml`) to PATCH new test users to `'accepted'` status.

### Authenticate via PAT

```ts
import { asPAT } from '../helpers/auth';

await asPAT(page, '<token-string>');
// Subsequent requests carry Authorization: Bearer ...
// The previous x-auth-request-* headers are explicitly cleared (round-2 F2).
```

### Multi-user mid-test identity swap

```ts
await asUser(page, ownerEmail);
// ... act as owner ...

await asUser(page, aliceEmail);
// hard reload + cookie clear + storage clear happens inside asUser,
// so the frontend is fully reset and now operates as alice.
```

### Native `window.confirm()` dialogs

Nine components in the dashboard fire native `confirm()` for delete:

```ts
import { autoAcceptConfirm, expectConfirm } from '../helpers/dialogs';

test.beforeEach(async ({ page }) => {
  autoAcceptConfirm(page); // every confirm() auto-accepts
});

// Strict variant — assert the confirm fired with the right message:
test('delete shows confirm', async ({ page }) => {
  const confirmed = expectConfirm(page, /Are you sure/);
  await page.getByRole('button', { name: 'Delete' }).click();
  await confirmed;
});
```

### Selectors

Preference order:

1. `getByRole('button', { name: /save/i })` — works on ~30 of 93 components
2. `getByText(/Save/)` — works most places
3. `getByLabel('Email')` — for form fields
4. `getByTestId('memory-block-row')` — last resort; **add the test-id in the
   same PR** that adds the test. Don't use CSS classes or DOM structure.

### Cleanup

Per-test resources use a unique prefix:

```ts
import { tname } from '../helpers/runId';
const agentName = tname('my-agent'); // -> "test-1730476100-abc123-my-agent"
```

In `afterEach` (or `afterAll`), call:

```ts
import { cleanupAll } from '../helpers/cleanup';
await cleanupAll(api, headers);
```

The reference dataset (`e2e-reference-agent`, owned by the search journey
fixture) is intentionally excluded.

---

## Project layout

```
e2e/
├── README.md                  # this file
├── helpers/
│   ├── auth.ts                # asUser, asPAT, asGuest
│   ├── cleanup.ts             # cleanupAll
│   ├── dialogs.ts             # autoAcceptConfirm, expectConfirm
│   └── runId.ts               # runId, tname, temail
├── fixtures/                  # added in Phase 2 (reference dataset, etc.)
└── journeys/
    ├── 01-auth-landing.spec.ts            # ✅ smoke
    ├── 02-memory-block-crud.spec.ts       # added by #98
    ├── 03a-search-fulltext.spec.ts        # added by #99
    └── ...                                # 14 journeys total per umbrella #96
```

---

## CI

`.github/workflows/e2e.yml` runs:

- **Smoke tier** (per-PR, ~3 min, `--grep @smoke`): journeys tagged `@smoke`
- **Full tier** (push to staging, ~10 min): all tagged journeys

The smoke gate ships **non-blocking initially** (`continue-on-error: true`).
Per RFC §8.1, promote to a required check after 1 week of green runs (issue #105).

Failure artifacts:

- HTML report → uploaded as `playwright-report`
- Traces + videos → retained on failure (`trace: 'retain-on-failure'`)
- Console output → in the workflow logs

---

## Out of scope (do NOT add tests in these areas)

Per RFC v3 §10:

- Visual regression
- Mobile viewport
- Real-OAuth proxy (the header injection is enough; real Google OAuth is a separate suite)
- Semantic + hybrid search (Ollama dependency)
- Cross-browser (Firefox/WebKit) — Chromium-only until suite is stable

If any of these matter later, file a fresh RFC.
