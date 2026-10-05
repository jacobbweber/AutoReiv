/**
 * CARD-636: five shipped routines on New York local times. A fresh install seeds exactly the five,
 * each scheduled for its local slot, none fires at boot, the Studio shows the real schedule, and a
 * deleted shipped routine is gone. Nothing here runs a routine, so no model is called.
 */
import { getJson, openApp } from './lib/app.mjs';

const KEPT = {
  'hourly-sre-pulse': { at: '02:00', label: 'Daily at 02:00 ET' },
  'education-retrieval-retention': { at: '02:30', label: 'Daily at 02:30 ET' },
  'wiki-curation': { at: '03:00', label: 'Daily at 03:00 ET' },
  'weekly-note-rollover': { at: '04:00', label: 'Mondays at 04:00 ET', weekday: 'Mon' },
  'telemetry-friction-auditor': { at: '04:30', label: 'Daily at 04:30 ET' },
};
const REMOVED = ['daily-sysinfo', 'morning-briefing', 'nightly-hygiene', 'skill-eval-sleep', 'skill-curator'];
const DAY_MS = 24 * 3600 * 1000;

function newYork(iso) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York', weekday: 'short', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date(iso));
  const get = (t) => parts.find((p) => p.type === t)?.value;
  return { weekday: get('weekday'), at: `${get('hour')}:${get('minute')}` };
}

async function openRoutines(page, base) {
  await openApp(page, base);
  await page.locator('#dock-routines').click();
  await page.locator('#view-routines').waitFor({ state: 'visible', timeout: 20000 });
  // The Agent filter cannot hold "All agents" (CARD-637); four of the five belong to autoreiv.
  await page.selectOption('#routinesFilterAgent', 'autoreiv');
}

export default {
  id: 'card-636-cut-routines-local-times',
  card: 'CARD-636',
  title: 'Five routines on local times',
  async run(j, { page, request, base }) {
    await j.step('A fresh install has exactly the five routines, each on its New York time, and none fires at boot', async () => {
      // Two scheduler ticks plus slack: CARD-635's boot catch-up would have fired here.
      await page.waitForTimeout(25000);
      const list = await getJson(request, `${base}/api/routines`);
      const ids = list.map((r) => r.id).sort();
      j.note(`routines: ${ids.join(', ')}`);
      if (ids.join() !== Object.keys(KEPT).sort().join()) throw new Error(`expected the five, got ${ids.join(', ')}`);
      for (const gone of REMOVED) if (ids.includes(gone)) throw new Error(`${gone} came back`);
      for (const r of list) {
        const want = KEPT[r.id];
        const local = newYork(r.next_run_at);
        j.note(`${r.id}: ${r.human_schedule}; next ${local.weekday} ${local.at} ET (${r.next_run_eta}); last_run_at ${r.last_run_at}`);
        if (!r.enabled) throw new Error(`${r.id} is paused`);
        if (r.last_run_at) throw new Error(`${r.id} fired at boot (${r.last_run_at})`);
        if (local.at !== want.at) throw new Error(`${r.id} next run ${local.at} ET, want ${want.at}`);
        if (want.weekday && local.weekday !== want.weekday) throw new Error(`${r.id} next run on ${local.weekday}`);
        const ahead = new Date(r.next_run_at).getTime() - Date.now();
        if (ahead <= 0 || ahead > (want.weekday ? 7 : 1) * DAY_MS) throw new Error(`${r.id} next run out of range: ${r.next_run_at}`);
        if (r.human_schedule !== want.label) throw new Error(`${r.id} shows "${r.human_schedule}", want "${want.label}"`);
      }
    }, { timeoutMs: 60000 });

    await j.step('Routines Studio shows the real schedules in New York time', async () => {
      await openRoutines(page, base);
      const grid = page.locator('#routinesGrid');
      for (const label of ['Daily at 02:00 ET', 'Daily at 03:00 ET', 'Mondays at 04:00 ET', 'Daily at 04:30 ET']) {
        await grid.getByText(label, { exact: true }).first().waitFor({ state: 'visible', timeout: 15000 });
      }
      const text = await grid.innerText();
      if (/UTC/.test(text)) throw new Error('the Studio still shows a UTC schedule');
      if (/Morning Briefing|Daily Sysinfo|Nightly Hygiene/i.test(text)) throw new Error('a removed routine is listed');
      await j.screenshot('routines-studio-five-local');
    }, { timeoutMs: 60000 });

    await j.step('Deleting a shipped routine removes it from the list and the Studio', async () => {
      const del = await request.delete(`${base}/api/routines/wiki-curation`);
      if (!del.ok()) throw new Error(`delete -> ${del.status()}`);
      const ids = (await getJson(request, `${base}/api/routines`)).map((r) => r.id);
      j.note(`after delete: ${ids.join(', ')}`);
      if (ids.includes('wiki-curation')) throw new Error('wiki-curation still listed');
      if (ids.length !== 4) throw new Error(`expected 4 left, got ${ids.length}`);
      await openRoutines(page, base);
      const grid = page.locator('#routinesGrid');
      await grid.getByText('Daily at 02:00 ET', { exact: true }).first().waitFor({ state: 'visible', timeout: 15000 });
      if (await grid.getByText('Daily at 03:00 ET', { exact: true }).count()) throw new Error('deleted routine still in the Studio');
    }, { timeoutMs: 60000 });
  },
};
