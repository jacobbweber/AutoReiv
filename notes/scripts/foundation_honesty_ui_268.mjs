import { chromium } from '@playwright/test';
import fs from 'fs';

const base = process.env.AUTOREIV_BASE || 'http://127.0.0.1:8000';
const jobId = process.argv[2] || '';
const outPath = process.argv[3] || 'notes/marathon-card268-ui-proof.json';

const out = {
  ok: false,
  job_id: jobId,
  base,
  pageerrors: [],
  console_errors: [],
  checks: {},
};

if (!jobId) {
  out.error = 'job_id required';
  fs.writeFileSync(outPath, JSON.stringify(out, null, 2) + '\n');
  process.exit(1);
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
page.on('pageerror', (err) => out.pageerrors.push(String(err)));
page.on('console', (msg) => {
  if (msg.type() === 'error') out.console_errors.push(msg.text());
});

try {
  await page.goto(base + '/', { waitUntil: 'networkidle', timeout: 45000 });
  out.checks.home_loaded = true;

  // Agent Desktop: open Observe dock; classic rail: click tab. Force-unpark view.
  await page.evaluate(() => {
    const dock = document.getElementById('dock-observability');
    if (dock) dock.click();
    const tab = document.querySelector('.tab-btn[data-tab="observability"]');
    if (tab) tab.click();
    const view = document.getElementById('view-observability');
    if (view) {
      view.classList.remove('hidden', 'desktop-view-parked');
      view.classList.add('flex');
      view.style.display = 'flex';
      view.style.visibility = 'visible';
    }
  });
  await page.waitForTimeout(800);
  out.checks.observe_view_visible = await page.locator('#view-observability').isVisible().catch(() => false);

  const input = page.locator('#standingJourneyJobIdInput');
  out.checks.journey_input_attached = (await input.count()) > 0;

  await page.evaluate((jid) => {
    const inputEl = document.getElementById('standingJourneyJobIdInput');
    if (inputEl) {
      inputEl.value = jid;
      inputEl.dispatchEvent(new Event('input', { bubbles: true }));
      inputEl.dispatchEvent(new Event('change', { bubbles: true }));
    }
    const btn = document.getElementById('standingJourneyLoadBtn');
    if (btn) btn.click();
  }, jobId);
  await page.waitForTimeout(2000);

  const timeline = page.locator('#standingJourneyTimeline');
  const text = ((await timeline.count()) ? await timeline.innerText() : '') || '';
  out.checks.timeline_has_job = text.includes(jobId);
  out.checks.timeline_snippet = text.slice(0, 500);
  const status = page.locator('#standingJourneyStatus');
  out.checks.status_text = (await status.count()) ? await status.innerText() : '';

  // Chat surface: open Chat dock + confirm phase strip exists (operator chrome)
  await page.evaluate(() => {
    const dock = document.getElementById('dock-chat');
    if (dock) dock.click();
    const tab = document.querySelector('.tab-btn[data-tab="chat"]');
    if (tab) tab.click();
    const view = document.getElementById('view-chat');
    if (view) {
      view.classList.remove('hidden', 'desktop-view-parked');
      view.classList.add('flex');
      view.style.display = 'flex';
    }
  });
  await page.waitForTimeout(500);
  out.checks.phase_strip_attached = (await page.locator('#jobPhaseStatusStrip').count()) > 0;
  out.checks.chat_view_visible = await page.locator('#view-chat').isVisible().catch(() => false);

  // API journey must match what Observe loaded (operator receipt honesty)
  const api = await page.evaluate(async (jid) => {
    const res = await fetch(`/api/observe/jobs/${encodeURIComponent(jid)}`);
    const body = await res.json().catch(() => ({}));
    return { status: res.status, job_id: body.job_id, ok: body.ok, phase_count: (body.phases || []).length };
  }, jobId);
  out.checks.api_receipt = api;

  out.ok = Boolean(
    out.checks.journey_input_attached &&
      out.checks.timeline_has_job &&
      out.checks.phase_strip_attached &&
      api.status === 200 &&
      api.job_id === jobId &&
      out.pageerrors.length === 0
  );
} catch (e) {
  out.error = String(e);
  out.ok = false;
} finally {
  await browser.close();
}

fs.writeFileSync(outPath, JSON.stringify(out, null, 2) + '\n');
console.log(JSON.stringify({ ok: out.ok, job_id: jobId, checks: out.checks, error: out.error || null }));
process.exit(out.ok ? 0 : 1);
