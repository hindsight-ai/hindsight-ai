import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright config for the Hindsight dashboard E2E suite.
 *
 * Per RFC v3 (umbrella #96):
 * - Chromium only (cross-browser is future work; multiplies CI cost 5x for marginal value)
 * - workers: 4 in CI (justifies the smoke tier scope)
 * - retries: 1 in CI (genuine network blips, but not enough to mask flake)
 * - webServer auto-starts backend (uvicorn) + frontend (vite dev) for fully-turnkey local runs
 * - timeout: 120s on webServer (default 60s won't survive cold migration / first-build)
 *
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './e2e/journeys',
  globalSetup: './e2e/global-setup.ts',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 4 : undefined,
  reporter: process.env.CI ? [['html'], ['github']] : 'html',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Auto-start backend (uvicorn) and frontend (vite) for E2E.
  // `reuseExistingServer: true` skips startup when ports already respond — handy for
  // local dev when you already have `bun run dev` and a uvicorn instance running.
  // In CI the ports are free, so Playwright starts them itself.
  webServer: [
    {
      command:
        'cd ../hindsight-service && DEV_MODE=false uv run uvicorn core.api.main:app --host 0.0.0.0 --port 8000',
      port: 8000,
      reuseExistingServer: true,
      timeout: 120_000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
    {
      command: 'bun run dev',
      port: 3000,
      reuseExistingServer: true,
      timeout: 60_000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
  ],
});
