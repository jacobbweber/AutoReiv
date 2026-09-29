/**
 * CARD-572 journey: a chat message becomes a job only when Jacob ticks Run as a job; routines follow their own setting.
 * 1) "First check X, then tell me ..." sent normally stays one normal reply: run_as_job false, 0 jobs, no phase sessions.
 * 2) The same text with the Run as a job box ticked (beside Auto-run) creates a standing job; the box unticks after send.
 * 3) Routines: the form's Run as a job box saves run_as_job; a routine with the box runs as a job (job_id),
 *    one with step words and no box runs as one turn (no job_id).
 * Checks are structural (request body, job rows, routine runs), never model wording.
 */
import { waitFor } from './lib/runner.mjs';
import { HITL_CARD, getJson, isStreaming, openApp, openSessionByTitle, send, trackStreams, waitReplyIdle } from './lib/app.mjs';

const ASK = 'First check the system health, then tell me in one sentence whether anything looks wrong.';

async function jobsOf(request, base, sid) {
  const j = await getJson(request, `${base}/api/chat/sessions/${encodeURIComponent(sid)}/journey`).catch(() => ({}));
  return Array.isArray(j.jobs) ? j.jobs : [];
}

async function childSessions(request, base, sid) {
  const list = await getJson(request, `${base}/api/sessions`).catch(() => []);
  return (Array.isArray(list) ? list : []).filter((s) => String(s.id).startsWith(`${sid}_`));
}

async function settle(page, done, timeoutMs) {
  let idle = 0;
  await waitFor(async () => {
    const cards = page.locator(HITL_CARD);
    const n = await cards.count();
    for (let i = 0; i < n; i += 1) {
      const btn = cards.nth(i).locator('[data-hitl-decision="APPROVED"]').first();
      if (await btn.isVisible().catch(() => false)) { await btn.click(); await page.waitForTimeout(1500); idle = 0; return false; }
    }
    if (await isStreaming(page)) { idle = 0; return false; }
    if (await done()) return true;
    idle += 1;
    return idle >= 8;
  }, { timeoutMs, intervalMs: 2000 }).catch(() => {});
  await waitReplyIdle(page, { timeoutMs: 120000 }).catch(() => {});
}

export default {
  id: 'card-572-explicit-job',
  card: 'CARD-572',
  title: 'Chat runs a job only when Run as a job is ticked; routines follow their own setting',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    let sid = '';

    await j.step('An AutoReiv chat is open; the Run as a job box sits beside Auto-run and starts off', async () => {
      const title = `QA 572 ${viewport.name} ${Date.now() % 100000}`;
      const made = await request.post(`${base}/api/sessions`, { data: { agent_id: 'autoreiv', title } });
      if (!made.ok()) throw new Error(`create session -> ${made.status()}`);
      sid = (await made.json()).id;
      await openApp(page, base);
      try {
        await openSessionByTitle(page, title, { agentId: 'autoreiv' });
      } catch (err) {
        const active = await page.evaluate(() => localStorage.getItem('autoreiv_active_session_id'));
        if (active !== sid) throw err;
        await page.locator('#toggleSidebarBtn').click();
      }
      await page.locator('#chatOptionsToggleBtn').click();
      await page.locator('#runAsJobToggle').waitFor({ state: 'visible', timeout: 10000 });
      if (await page.locator('#runAsJobToggle').isChecked()) throw new Error('Run as a job starts checked');
      if (!(await page.locator('#approvalToggle').isVisible())) throw new Error('Auto-run box not visible');
      await j.screenshot('composer-both-boxes');
      await page.locator('#chatOptionsToggleBtn').click();
      j.note(`session ${sid}`);
    }, { timeoutMs: 60000 });

    await j.step('"First check X, then tell me" without the box stays one normal reply (0 jobs)', async () => {
      const n = streams.count;
      await send(page, ASK);
      await waitFor(() => streams.count > n, { timeoutMs: 15000 });
      const body = streams.posts[streams.posts.length - 1] || {};
      await settle(page, async () => !(await isStreaming(page)), 600000);
      const jobs = await jobsOf(request, base, sid);
      const kids = await childSessions(request, base, sid);
      j.note(`run_as_job sent: ${body.run_as_job}; jobs ${jobs.length}; child sessions ${kids.length}`);
      if (body.run_as_job !== false) throw new Error(`run_as_job was ${body.run_as_job}`);
      if (jobs.length) throw new Error(`a job was created: ${jobs.map((x) => x.id).join(',')}`);
      if (kids.length) throw new Error('phase sessions were created');
      await j.screenshot('normal-reply');
    }, { timeoutMs: 700000 });

    await j.step('The same text with Run as a job ticked creates a job; the box unticks after send', async () => {
      await page.locator('#chatOptionsToggleBtn').click();
      await page.locator('#runAsJobToggle').check();
      if (!(await page.locator('#runAsJobBadge').isVisible())) throw new Error('Run as a job badge not shown');
      await j.screenshot('run-as-job-ticked');
      await page.locator('#chatOptionsToggleBtn').click();
      const n = streams.count;
      await send(page, ASK);
      await waitFor(() => streams.count > n, { timeoutMs: 15000 });
      const body = streams.posts[streams.posts.length - 1] || {};
      const unticked = !(await page.locator('#runAsJobToggle').isChecked());
      const badgeHidden = !(await page.locator('#runAsJobBadge').isVisible());
      await waitFor(async () => (await jobsOf(request, base, sid)).length > 0, { timeoutMs: 120000, intervalMs: 2000 }).catch(() => {});
      await settle(page, async () => {
        const jobs = await jobsOf(request, base, sid);
        return jobs.length > 0 && /done|failed|waiting/i.test(String(jobs[jobs.length - 1].status || ''));
      }, 1200000);
      const jobs = await jobsOf(request, base, sid);
      const last = jobs[jobs.length - 1] || {};
      j.note(`run_as_job sent: ${body.run_as_job}; box unticked after send: ${unticked}; badge hidden: ${badgeHidden}; jobs ${jobs.length}; last job ${last.id || '-'} ${last.status || '-'}`);
      if (body.run_as_job !== true) throw new Error(`run_as_job was ${body.run_as_job}`);
      if (!unticked || !badgeHidden) throw new Error('the box did not reset after send');
      if (jobs.length !== 1) throw new Error(`expected 1 job, got ${jobs.length}`);
      await j.screenshot('job-run');
    }, { timeoutMs: 1400000 });

    await j.step('Routines: the form saves Run as a job; that routine runs as a job, a step-worded one without it does not', async () => {
      const tag = `${viewport.name}-${Date.now() % 100000}`;
      await page.locator('#dock-routines').click();
      await page.locator('#newRoutineBtn').click();
      await page.locator('#routineModal').waitFor({ state: 'visible', timeout: 10000 });
      await page.locator('#routineNameInput').fill(`QA 572 job ${tag}`);
      await page.selectOption('#routineAgentSelect', 'autoreiv').catch(() => {});
      await page.locator('#routinePromptInput').fill('Say hello in one short sentence.');
      await page.locator('#routineEnabledInput').uncheck();
      await page.locator('#routineRunAsJobInput').check();
      await j.screenshot('routine-form-run-as-job');
      await page.locator('#saveRoutineBtn').click();
      await page.locator('#routineModal').waitFor({ state: 'hidden', timeout: 15000 });
      const list = await getJson(request, `${base}/api/routines`);
      const saved = list.find((r) => r.name === `QA 572 job ${tag}`);
      if (!saved) throw new Error('routine not saved');
      if (saved.run_as_job !== true) throw new Error(`saved run_as_job ${saved.run_as_job}`);
      const words = `qa-572-words-${tag}`;
      const made = await request.post(`${base}/api/routines`, { data: { id: words, name: `QA 572 words ${tag}`, agent_id: 'autoreiv', enabled: false,
        prompt_template: 'First check the system health, then write one sentence about it, finally say done.' } });
      if (!made.ok()) throw new Error(`create words routine -> ${made.status()}`);
      const runJob = await (await request.post(`${base}/api/routines/${encodeURIComponent(saved.id)}/run`, { timeout: 1200000 })).json();
      const runWords = await (await request.post(`${base}/api/routines/${encodeURIComponent(words)}/run`, { timeout: 600000 })).json();
      j.note(`with box: status ${runJob.status}, job ${runJob.job_id || 'none'}; step words, no box: status ${runWords.status}, job ${runWords.job_id || 'none'}`);
      if (!runJob.job_id) throw new Error('routine with Run as a job did not run as a job');
      if (runWords.job_id) throw new Error('routine without the box ran as a job');
      await request.delete(`${base}/api/routines/${encodeURIComponent(saved.id)}`).catch(() => {});
      await request.delete(`${base}/api/routines/${encodeURIComponent(words)}`).catch(() => {});
    }, { timeoutMs: 1900000 });
  },
};
