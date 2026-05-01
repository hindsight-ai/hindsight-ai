#!/usr/bin/env node
// Hindsight dashboard UI/UX audit driver.
//
// Walks every dashboard route at desktop / tablet / mobile viewports,
// captures screenshots, probes scroll behaviour and horizontal overflow,
// records console errors, and runs a small set of interaction probes
// (user menu, About modal, GetStarted modal). Outputs:
//
//   <out>/desktop/<NN-name>.png            (and -fullpage.png)
//   <out>/tablet/<NN-name>.png
//   <out>/mobile/<NN-name>.png
//   <out>/interactions/<probe>.png
//   <out>/findings.json
//
// Usage from the repo root (worktree must have node_modules installed
// in apps/hindsight-dashboard, since playwright is resolved from there):
//
//   node .claude/skills/ui-ux-audit/audit.mjs
//
// Override defaults with env vars:
//   AUDIT_BASE_URL  default http://localhost:3010
//   AUDIT_OUT       default /tmp/ui-audit
//                   (set to docs/rfcs/<NNNN>-audit-screenshots to commit
//                    a baseline alongside an RFC)
//   AUDIT_PHASE     "all" | "routes" | "interactions"  (default "all")

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Resolve repo root by walking up until we find package.json's apps/ folder.
function findRepoRoot(start) {
  let dir = start;
  for (let i = 0; i < 6; i++) {
    if (fs.existsSync(path.join(dir, 'apps', 'hindsight-dashboard', 'package.json'))) {
      return dir;
    }
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  throw new Error(`Could not find repo root from ${start}; expected apps/hindsight-dashboard/package.json somewhere up.`);
}

const REPO_ROOT = findRepoRoot(__dirname);
const BASE = process.env.AUDIT_BASE_URL || 'http://localhost:3010';
const OUT = process.env.AUDIT_OUT || '/tmp/ui-audit';
const PHASE = process.env.AUDIT_PHASE || 'all';

// Frozen instant for screenshot determinism. The dashboard renders a live
// clock via LastUpdatedLabel.tsx (toLocaleTimeString in the page header),
// which would otherwise produce pixel diffs on every run. We override
// Date.now() and the Date constructor to return this fixed instant inside
// every page context.
const FROZEN_INSTANT = new Date('2026-04-28T22:00:00Z').getTime();

// Playwright is a dev dep of the dashboard; resolve from there.
const playwrightEntry = path.join(REPO_ROOT, 'apps', 'hindsight-dashboard', 'node_modules', 'playwright', 'index.mjs');
if (!fs.existsSync(playwrightEntry)) {
  console.error(`Playwright not found at ${playwrightEntry}.`);
  console.error('Install it from the dashboard package:');
  console.error('  (cd apps/hindsight-dashboard && npm install --no-save playwright && npx playwright install chromium)');
  process.exit(2);
}
const { chromium } = await import(pathToFileURL(playwrightEntry).href);

const routes = [
  { path: '/', name: '01-root' },
  { path: '/dashboard', name: '02-dashboard' },
  { path: '/memory-blocks', name: '03-memory-blocks' },
  { path: '/keywords', name: '04-keywords' },
  { path: '/agents', name: '05-agents' },
  { path: '/analytics', name: '06-analytics' },
  { path: '/consolidation-suggestions', name: '07-consolidation' },
  { path: '/archived-memory-blocks', name: '08-archived' },
  { path: '/pruning-suggestions', name: '09-pruning' },
  { path: '/memory-optimization-center', name: '10-optimization' },
  { path: '/support', name: '11-support' },
  { path: '/profile', name: '12-profile' },
  { path: '/tokens', name: '13-tokens' },
];

const viewports = [
  { name: 'desktop', w: 1440, h: 900, dir: 'desktop', fullPage: true },
  { name: 'tablet', w: 768, h: 1024, dir: 'tablet', fullPage: false },
  { name: 'mobile', w: 375, h: 812, dir: 'mobile', fullPage: false },
];

const findings = [];
function note(severity, route, viewport, title, detail) {
  findings.push({ severity, route, viewport, title, detail });
  console.log(`[${severity}] ${route} (${viewport}) — ${title}: ${detail}`);
}

function ensureDirs() {
  for (const sub of ['desktop', 'tablet', 'mobile', 'interactions']) {
    fs.mkdirSync(path.join(OUT, sub), { recursive: true });
  }
}

// Freeze Date and disable animations in every page context so screenshots
// taken minutes apart compare clean. Inject before any app code runs.
async function injectDeterminism(context) {
  await context.addInitScript((frozen) => {
    const RealDate = Date;
    const FrozenDate = class extends RealDate {
      constructor(...args) {
        if (args.length === 0) return new RealDate(frozen);
        return new RealDate(...args);
      }
      static now() { return frozen; }
    };
    // Preserve static helpers
    Object.getOwnPropertyNames(RealDate).forEach((p) => {
      if (!(p in FrozenDate)) FrozenDate[p] = RealDate[p];
    });
    // eslint-disable-next-line no-global-assign
    Date = FrozenDate;
  }, FROZEN_INSTANT);

  await context.addInitScript(() => {
    // Disable CSS animations and transitions to settle skeletons + overlays.
    const style = document.createElement('style');
    style.textContent = `
      *, *::before, *::after {
        animation: none !important;
        transition: none !important;
      }
    `;
    // Wait for documentElement before appending.
    if (document.documentElement) {
      document.documentElement.appendChild(style);
    } else {
      document.addEventListener('DOMContentLoaded', () => {
        document.documentElement.appendChild(style);
      });
    }
  });
}

// Heuristic: a page that mounts but renders almost nothing with computed
// borders or non-default backgrounds is probably hitting an unstyled-class
// regression (the H1/H2 root cause). The check is loose on purpose — false
// positives on truly minimal pages are easy to ignore; false negatives on
// broken pages are the failure mode the script existed to catch.
async function probeStylelessness(page) {
  return page.evaluate(() => {
    const candidates = Array.from(document.querySelectorAll(
      'main button, main a, main input, main select, main textarea, main [role="button"]'
    ));
    if (candidates.length === 0) return { sampled: 0, styled: 0, ratio: null };
    let styled = 0;
    for (const el of candidates) {
      const cs = getComputedStyle(el);
      const hasBorder = cs.borderWidth && cs.borderWidth !== '0px' && cs.borderStyle !== 'none';
      const hasBg = cs.backgroundColor && cs.backgroundColor !== 'rgba(0, 0, 0, 0)' && cs.backgroundColor !== 'transparent';
      const hasShadow = cs.boxShadow && cs.boxShadow !== 'none';
      if (hasBorder || hasBg || hasShadow) styled++;
    }
    return { sampled: candidates.length, styled, ratio: styled / candidates.length };
  });
}

// Suppress the "Get Started" auto-popup on the dashboard. The flag key uses
// email or user_id; fake both since we don't always know which is set.
async function suppressGetStarted(page) {
  await page.evaluate(() => {
    const ts = new Date().toISOString();
    try {
      localStorage.setItem('hindsight.get-started.dev@localhost', ts);
      localStorage.setItem('hindsight.get-started.default', ts);
    } catch {}
  });
}

async function dismissGetStartedIfPresent(page) {
  const close = page.locator('button[aria-label="Close get started guide"]');
  if (await close.count()) {
    try { await close.first().click({ timeout: 1500 }); } catch {}
    await page.waitForTimeout(150);
  }
}

async function probe(page, route, vp) {
  const url = `${BASE}${route.path}`;
  const consoleErrors = [];
  page.removeAllListeners('console');
  page.on('console', (msg) => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });

  const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(800);
  await dismissGetStartedIfPresent(page);

  const screenshotPath = path.join(OUT, vp.dir, `${route.name}.png`);
  await page.screenshot({ path: screenshotPath, fullPage: false });
  if (vp.fullPage) {
    await page.screenshot({
      path: path.join(OUT, vp.dir, `${route.name}-fullpage.png`),
      fullPage: true,
    });
  }

  // Probe scrolling. If the document is taller than the viewport but window
  // doesn't scroll AND no inner scroller moves, the page-level scroll is dead.
  const scroll = await page.evaluate(() => {
    const before = { winY: window.scrollY, docH: document.documentElement.scrollHeight, viewH: window.innerHeight };
    window.scrollBy(0, 2000);
    const afterWin = { winY: window.scrollY };
    const scrollers = Array.from(document.querySelectorAll('main, [class*="overflow-y-auto"], [class*="overflow-auto"]'))
      .slice(0, 6)
      .map((el) => {
        const t = el.scrollTop;
        el.scrollBy(0, 2000);
        return { before: t, after: el.scrollTop };
      });
    return { before, afterWin, scrollers };
  });

  if (scroll.before.docH > scroll.before.viewH + 50 && scroll.afterWin.winY === 0) {
    const innerScrolled = scroll.scrollers.some((s) => s.after !== s.before);
    if (!innerScrolled) {
      note('high', route.path, vp.name, 'Page does not scroll',
        `docH=${scroll.before.docH} viewH=${scroll.before.viewH}, window.scrollY stayed 0, no inner scroller moved.`);
    }
  }

  const overflow = await page.evaluate((vw) => {
    const docW = document.documentElement.scrollWidth;
    return { docW, vw, hasH: docW > vw + 1 };
  }, vp.w);
  if (overflow.hasH) {
    note('medium', route.path, vp.name, 'Horizontal overflow',
      `documentElement.scrollWidth=${overflow.docW} > viewport=${overflow.vw}`);
  }

  if (consoleErrors.length) {
    note('low', route.path, vp.name, 'Console errors', consoleErrors.slice(0, 3).join(' || '));
  }
  if (resp && resp.status() >= 400) {
    note('high', route.path, vp.name, `HTTP ${resp.status()}`, url);
  }

  // Unstyled-page heuristic — flag if fewer than 30% of interactive elements
  // in <main> have a visible border, background, or shadow. Catches the
  // legacy-class regression class that the scroll/overflow probes miss.
  const styling = await probeStylelessness(page);
  if (styling.sampled >= 4 && styling.ratio !== null && styling.ratio < 0.3) {
    note('high', route.path, vp.name, 'Page may be unstyled',
      `${styling.styled}/${styling.sampled} interactive elements in <main> have computed border/background/shadow.`);
  }
}

async function newCtx(browser, viewport) {
  const ctx = await browser.newContext({ viewport });
  await injectDeterminism(ctx);
  return ctx;
}

async function runRouteSweep(browser) {
  for (const vp of viewports) {
    const ctx = await newCtx(browser, { width: vp.w, height: vp.h });
    const page = await ctx.newPage();
    await page.goto(BASE, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1500);
    await suppressGetStarted(page);
    await dismissGetStartedIfPresent(page);
    for (const r of routes) {
      try {
        await probe(page, r, vp);
      } catch (e) {
        note('high', r.path, vp.name, 'Probe threw', String(e.message || e));
      }
    }
    await ctx.close();
  }
}

async function runInteractionSweep(browser) {
  // 1. GetStarted modal — first-load behaviour + a11y dismiss probes
  try {
    const ctx = await newCtx(browser, { width: 1440, height: 900 });
    const page = await ctx.newPage();
    await page.goto(`${BASE}/dashboard`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    await page.screenshot({ path: path.join(OUT, 'interactions', 'getstarted-modal-on-load.png') });

    const before = await page.locator('button[aria-label="Close get started guide"]').count();
    await page.mouse.click(20, 20); // backdrop
    await page.waitForTimeout(400);
    const afterBackdrop = await page.locator('button[aria-label="Close get started guide"]').count();
    if (before > 0 && afterBackdrop > 0) {
      note('medium', '/dashboard', 'desktop',
        'GetStarted modal does not dismiss on backdrop click',
        'The Portal overlay swallows the click but the close handler is only on the X button.');
    }
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
    const afterEsc = await page.locator('button[aria-label="Close get started guide"]').count();
    if (afterEsc > 0) {
      note('medium', '/dashboard', 'desktop',
        'GetStarted modal does not close on Escape',
        'No keydown handler bound to Escape; user must hit X or scroll to "Got it".');
    }
    await ctx.close();
  } catch (e) {
    note('low', '/dashboard', 'desktop', 'GetStarted probe failed', String(e.message || e));
  }

  // 2. User menu open + About dialog open + Esc dismiss
  try {
    const ctx = await newCtx(browser, { width: 1440, height: 900 });
    const page = await ctx.newPage();
    await page.goto(`${BASE}/dashboard`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1500);
    await suppressGetStarted(page);
    await dismissGetStartedIfPresent(page);

    // Avatar button = the header button containing a rounded-full div with the user initial.
    // We don't know the initial, so match any letter via a regex; first char of dev@localhost is "D".
    const avatar = page.locator('header button').filter({
      has: page.locator('div.rounded-full').filter({ hasText: /^[A-Z0-9]$/ }),
    });
    if (await avatar.count() === 0) {
      note('low', '/dashboard', 'desktop', 'User menu probe — avatar not found',
        'Could not locate header avatar button; selector may need updating.');
      await ctx.close();
    } else {
      await avatar.first().click({ timeout: 5000 });
      await page.waitForTimeout(400);
      await page.screenshot({ path: path.join(OUT, 'interactions', 'user-menu-open.png') });

      const aboutBtn = page.locator('button:has-text("About Hindsight AI")');
      if (await aboutBtn.count() > 0) {
        await aboutBtn.click({ timeout: 5000, force: true });
        await page.waitForTimeout(1200);
        await page.screenshot({ path: path.join(OUT, 'interactions', 'about-modal-open.png') });
        await page.keyboard.press('Escape');
        await page.waitForTimeout(300);
        await page.screenshot({ path: path.join(OUT, 'interactions', 'about-modal-after-esc.png') });
      } else {
        note('medium', '/dashboard', 'desktop', 'About menu entry missing',
          'User dropdown opened but "About Hindsight AI" entry not found.');
      }
      await ctx.close();
    }
  } catch (e) {
    note('low', '/dashboard', 'desktop', 'User menu probe failed', String(e.message || e));
  }

  // 3. Mobile sidebar drawer
  try {
    const ctx = await newCtx(browser, { width: 375, height: 812 });
    const page = await ctx.newPage();
    await page.goto(`${BASE}/dashboard`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1200);
    await suppressGetStarted(page);
    await dismissGetStartedIfPresent(page);
    await page.screenshot({ path: path.join(OUT, 'interactions', 'mobile-dashboard.png') });
    const burger = page.locator('button[aria-label="Open navigation"]');
    if (await burger.count() > 0) {
      await burger.first().click();
      await page.waitForTimeout(400);
      await page.screenshot({ path: path.join(OUT, 'interactions', 'mobile-sidebar-open.png') });
    } else {
      note('medium', '/dashboard', 'mobile', 'No burger button found',
        'expected button[aria-label="Open navigation"]');
    }
    await ctx.close();
  } catch (e) {
    note('low', '/dashboard', 'mobile', 'Mobile drawer probe failed', String(e.message || e));
  }

  // 4. Close-up shots of legacy-class pages (regression detectors)
  try {
    const ctx = await newCtx(browser, { width: 1440, height: 900 });
    const page = await ctx.newPage();
    await page.goto(`${BASE}/dashboard`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1200);
    await suppressGetStarted(page);
    await dismissGetStartedIfPresent(page);

    await page.goto(`${BASE}/consolidation-suggestions`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(900);
    await page.screenshot({
      path: path.join(OUT, 'interactions', 'consolidation-broken-toolbar.png'),
      clip: { x: 256, y: 0, width: 1184, height: 400 },
    });

    await page.goto(`${BASE}/pruning-suggestions`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(900);
    await page.screenshot({
      path: path.join(OUT, 'interactions', 'pruning-broken-form.png'),
      clip: { x: 256, y: 0, width: 1184, height: 500 },
    });

    await ctx.close();
  } catch (e) {
    note('low', '/consolidation-suggestions', 'desktop', 'Close-up probe failed', String(e.message || e));
  }
}

async function reachable() {
  try {
    const r = await fetch(BASE, { method: 'GET' });
    return r.status < 500;
  } catch {
    return false;
  }
}

async function main() {
  if (!(await reachable())) {
    console.error(`AUDIT_BASE_URL ${BASE} is not reachable.`);
    console.error('Start the local stack first (e.g. ./start_hindsight.sh, then visit http://localhost:3010).');
    process.exit(1);
  }
  ensureDirs();
  const browser = await chromium.launch();
  try {
    if (PHASE === 'all' || PHASE === 'routes') await runRouteSweep(browser);
    if (PHASE === 'all' || PHASE === 'interactions') await runInteractionSweep(browser);
  } finally {
    await browser.close();
  }
  fs.writeFileSync(path.join(OUT, 'findings.json'), JSON.stringify(findings, null, 2));
  console.log(`\n=== ${findings.length} findings written to ${path.join(OUT, 'findings.json')} ===`);
  console.log(`=== screenshots in ${OUT} ===`);
}

main().catch((e) => {
  console.error('FATAL:', e);
  process.exit(1);
});
