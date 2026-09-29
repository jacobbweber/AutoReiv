/**
 * CARD-573 journey: an agent's Always auto-run preference starts Chat's Auto-run box checked, per chat.
 * 1) Agent Studio -> tutor -> Agent Preferences: tick Always auto-run and save (API shows always_auto_run true).
 * 2) A chat with tutor opens with Auto-run checked (Run as a job still off beside it).
 * 3) Unticking in that chat sends approval_mode "ask"; another tutor chat still starts checked; the first stays unticked;
 *    a chat with another agent (autoreiv, no preference) starts unchecked.
 * 4) Routines: a new routine for tutor starts with Auto-run checked and saves "run"; a routine saved with "ask" keeps it.
 * Checks are structural (checkbox state, request body, saved fields), never model wording.
 */
import { waitFor } from './lib/runner.mjs';
import { getJson, openApp, openSessionByTitle, send, trackStreams, waitReplyIdle } from './lib/app.mjs';

const AGENT = 'tutor';

async function makeSession(request, base, agentId, title) {
  const made = await request.post(`${base}/api/sessions`, { data: { agent_id: agentId, title } });
  if (!made.ok()) throw new Error(`create session -> ${made.status()}`);
  return (await made.json()).id;
}

async function openChat(page, title, agentId) {
  await openSessionByTitle(page, title, { agentId });
  if (await page.locator('#sessionList').isVisible().catch(() => false)) await page.locator('#toggleSidebarBtn').click().catch(() => {});
}

async function autoRunChecked(page) {
  const opened = await page.locator('#approvalToggle').isVisible().catch(() => false);
  if (!opened) await page.locator('#chatOptionsToggleBtn').click();
  await page.locator('#approvalToggle').waitFor({ state: 'visible', timeout: 10000 });
  return page.locator('#approvalToggle').isChecked();
}

async function closeOptions(page) {
  if (await page.locator('#approvalToggle').isVisible().catch(() => false)) await page.locator('#chatOptionsToggleBtn').click();
}

export default {
  id: 'card-573-always-auto-run',
  card: 'CARD-573',
  title: 'Always auto-run per agent starts Chat Auto-run checked; untick sticks per chat; new routines pre-checked',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    const tag = `${viewport.name} ${Date.now() % 100000}`;

    await j.step('Agent Studio: tick Always auto-run in Agent Preferences for tutor and save', async () => {
      await openApp(page, base);
      if (!(await page.locator('#forgeAgentSelect').isVisible().catch(() => false))) await page.locator('#dock-agents').click();
      await page.locator('#forgeAgentSelect').waitFor({ state: 'visible', timeout: 15000 });
      await page.selectOption('#forgeAgentSelect', AGENT);
      await page.waitForTimeout(1000);
      const prefs = page.locator('details[data-section="preferences"]');
      if (!(await prefs.evaluate((d) => d.open))) await prefs.locator('summary').click();
      const box = page.locator('#forgeAlwaysAutoRunInput');
      await box.scrollIntoViewIfNeeded();
      if (await box.isChecked()) throw new Error('Always auto-run starts checked for tutor');
      await box.check();
      await j.screenshot('agent-studio-always-auto-run');
      await page.locator('#saveAgentBtn').click();
      await waitFor(async () => (await getJson(request, `${base}/api/agents/${AGENT}`)).always_auto_run === true, { timeoutMs: 20000, intervalMs: 1000 });
      const other = await getJson(request, `${base}/api/agents/autoreiv`);
      const a = await getJson(request, `${base}/api/agents/${AGENT}`);
      j.note(`tutor always_auto_run ${a.always_auto_run}; autoreiv always_auto_run ${other.always_auto_run}; tutor tools ${(a.allowed_tools || []).length}`);
      if (other.always_auto_run) throw new Error('autoreiv picked up the preference');
      await page.locator('.desktop-window:has(#forgeAgentSelect) .desktop-win-min').first().click({ timeout: 5000 }).catch(() => {});
    }, { timeoutMs: 90000 });

    let titleA = '';
    let titleB = '';
    await j.step('A chat with tutor opens with Auto-run checked; Run as a job stays off beside it', async () => {
      titleA = `QA 573 A ${tag}`;
      titleB = `QA 573 B ${tag}`;
      await makeSession(request, base, AGENT, titleA);
      await makeSession(request, base, AGENT, titleB);
      await openApp(page, base);
      await openChat(page, titleA, AGENT);
      const on = await autoRunChecked(page);
      const job = await page.locator('#runAsJobToggle').isChecked();
      const badge = await page.locator('#approvalBadge').isVisible().catch(() => false);
      await j.screenshot('composer-both-boxes');
      j.note(`chat A Auto-run checked ${on}; Auto-run badge ${badge}; Run as a job checked ${job}`);
      if (!on) throw new Error('Auto-run not checked for a tutor chat');
      if (job) throw new Error('Run as a job started checked');
    }, { timeoutMs: 90000 });

    await j.step('Untick in chat A sends "ask"; chat B still starts checked; chat A stays unticked; autoreiv chat starts unchecked', async () => {
      await page.locator('#approvalToggle').uncheck();
      await closeOptions(page);
      const n = streams.count;
      await send(page, 'Reply with the single word: ok');
      await waitFor(() => streams.count > n, { timeoutMs: 15000 });
      const body = streams.posts[streams.posts.length - 1] || {};
      await waitReplyIdle(page, { timeoutMs: 300000 }).catch(() => {});
      await openChat(page, titleB, AGENT);
      const bOn = await autoRunChecked(page);
      await closeOptions(page);
      await openChat(page, titleA, AGENT);
      const aOn = await autoRunChecked(page);
      await closeOptions(page);
      const titleC = `QA 573 C ${tag}`;
      await makeSession(request, base, 'autoreiv', titleC);
      await openChat(page, titleC, 'autoreiv');
      const cOn = await autoRunChecked(page);
      await closeOptions(page);
      j.note(`chat A send approval_mode ${body.approval_mode}; chat B checked ${bOn}; chat A after return checked ${aOn}; autoreiv chat checked ${cOn}`);
      if (body.approval_mode !== 'ask') throw new Error(`unticked chat sent ${body.approval_mode}`);
      if (!bOn) throw new Error('another tutor chat did not start checked');
      if (aOn) throw new Error('chat A forgot its untick');
      if (cOn) throw new Error('an agent without the preference started checked');
    }, { timeoutMs: 400000 });

    await j.step('Routines: a new tutor routine starts with Auto-run checked; a saved "ask" routine keeps its value', async () => {
      const keep = `qa-573-keep-${Date.now() % 100000}`;
      const made = await request.post(`${base}/api/routines`, { data: { id: keep, name: `QA 573 keep ${tag}`, agent_id: AGENT, enabled: false, approval_mode: 'ask', prompt_template: 'Say hi.' } });
      if (!made.ok()) throw new Error(`create keep routine -> ${made.status()}`);
      await page.locator('#dock-routines').click();
      await page.locator('#newRoutineBtn').click();
      await page.locator('#routineModal').waitFor({ state: 'visible', timeout: 10000 });
      await page.selectOption('#routineAgentSelect', AGENT);
      await page.waitForTimeout(300);
      const pre = await page.locator('#routineApprovalRunInput').isChecked();
      await page.locator('#routineNameInput').fill(`QA 573 new ${tag}`);
      await page.locator('#routinePromptInput').fill('Say hello in one short sentence.');
      await page.locator('#routineEnabledInput').uncheck();
      await j.screenshot('new-routine-auto-run-prechecked');
      await page.locator('#saveRoutineBtn').click();
      await page.locator('#routineModal').waitFor({ state: 'hidden', timeout: 15000 });
      const list = await getJson(request, `${base}/api/routines`);
      const saved = list.find((r) => r.name === `QA 573 new ${tag}`) || {};
      const kept = list.find((r) => r.id === keep) || {};
      const apiNew = await request.post(`${base}/api/routines`, { data: { id: `${keep}-api`, name: `QA 573 api ${tag}`, agent_id: AGENT, enabled: false, prompt_template: 'Say hi.' } });
      const apiSaved = apiNew.ok() ? ((await getJson(request, `${base}/api/routines`)).find((r) => r.id === `${keep}-api`) || {}) : {};
      j.note(`new routine box pre-checked ${pre}; saved approval_mode ${saved.approval_mode}; kept routine ${kept.approval_mode}; API-created with no value ${apiSaved.approval_mode}`);
      for (const id of [saved.id, keep, `${keep}-api`]) if (id) await request.delete(`${base}/api/routines/${encodeURIComponent(id)}`).catch(() => {});
      if (!pre) throw new Error('new routine box not pre-checked');
      if (saved.approval_mode !== 'run') throw new Error(`new routine saved ${saved.approval_mode}`);
      if (kept.approval_mode !== 'ask') throw new Error(`existing routine changed to ${kept.approval_mode}`);
    }, { timeoutMs: 90000 });
  },
};
