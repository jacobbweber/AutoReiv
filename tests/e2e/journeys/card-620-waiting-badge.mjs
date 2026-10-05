/**
 * CARD-620: waiting_answer strip shows WAITING; a rejected/stopped job still shows STOPPED.
 * Uses the journey hydrate path via a mocked session journey payload rendered after open.
 */
import { openApp } from './lib/app.mjs';
import { waitFor } from './lib/runner.mjs';

async function ensureChat(page) {
  if (!(await page.locator('#promptInput').isVisible().catch(() => false))) {
    await page.locator('#dock-chat').click();
  }
  await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 15000 });
}

export default {
  id: 'card-620-waiting-badge',
  card: 'CARD-620',
  title: 'Job waiting for answer shows WAITING; stopped shows STOPPED',
  async run(j, { page, request, base }) {
    const sess = await (await request.post(base + '/api/sessions', { data: { agent_id: 'autoreiv', title: 'CARD-620 wait ' + Date.now() } })).json();
    const sid = sess.id;

    await j.step('Open chat and inject waiting_answer strip state', async () => {
      await openApp(page, base);
      await ensureChat(page);
      await page.evaluate(async (id) => {
        const { hydrateJobPhaseStateFromJourney } = await import('/static/modules/studios/chat/session_select.js');
        const { formatJobPhaseStrip } = await import('/static/modules/studios/chat/job_strip.js');
        const state = hydrateJobPhaseStateFromJourney({
          jobs: [{
            id: 'job_620', status: 'running', stopped: false, waiting_answer: true,
            phases: [{ id: 'p1', index: 0, name: 'Execute', status: 'queued', assigned_agent_id: 'autoreiv' }],
          }],
        });
        window.__card620 = { state, strip: formatJobPhaseStrip(state), sessionId: id };
        const strip = document.getElementById('jobPhaseStatusStrip');
        if (strip) {
          strip.classList.remove('hidden');
          strip.dataset.testid = 'job-phase-strip';
          strip.innerHTML = `<span data-testid="job-status">${state && window.__card620.strip.jobStatusLabel}</span>`
            + `<span data-testid="job-react">${window.__card620.strip.reactState}</span>`;
        }
      }, sid);
      await waitFor(async () => (await page.locator('[data-testid="job-react"]').innerText()) === 'WAITING', { timeoutMs: 5000 });
      const label = await page.locator('[data-testid="job-status"]').innerText();
      if (!/waiting for answer/i.test(label)) throw new Error('expected waiting label, got ' + label);
    });

    await j.step('Stopped job strip model is STOPPED', async () => {
      const info = await page.evaluate(async () => {
        const { hydrateJobPhaseStateFromJourney } = await import('/static/modules/studios/chat/session_select.js');
        const { formatJobPhaseStrip } = await import('/static/modules/studios/chat/job_strip.js');
        const state = hydrateJobPhaseStateFromJourney({
          jobs: [{
            id: 'job_620s', status: 'running', stopped: true, waiting_answer: false,
            phases: [{ id: 'p1', index: 0, name: 'Execute', status: 'queued', assigned_agent_id: 'autoreiv' }],
          }],
        });
        return formatJobPhaseStrip(state);
      });
      if (info.reactState !== 'STOPPED') throw new Error('expected STOPPED got ' + info.reactState);
      if (info.jobStatusLabel !== 'Job stopped') throw new Error('expected Job stopped got ' + info.jobStatusLabel);
    });
  },
};
