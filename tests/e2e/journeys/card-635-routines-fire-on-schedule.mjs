/**
 * CARD-635: routines fire only at their scheduled time. A new routine waits for its slot,
 * a failure moves the next run forward, and resuming schedules from now. No model is called:
 * the routine targets a missing agent, so even a wrong fire fails fast without loading Spark/Nimo.
 */
import { getJson, openApp } from './lib/app.mjs';
import { clickExpect, waitFor } from './lib/runner.mjs';

const HOUR_MS = 3600 * 1000;

async function find(request, base, id) {
  const list = await getJson(request, `${base}/api/routines`);
  return list.find((r) => r.id === id);
}

function msUntil(iso) {
  return new Date(iso).getTime() - Date.now();
}

export default {
  id: 'card-635-routines-fire-on-schedule',
  card: 'CARD-635',
  title: 'Routines fire only at their scheduled time',
  async run(j, { page, request, base, viewport }) {
    const id = `qa-635-${viewport.name}-${Date.now() % 100000}`;
    const name = `QA 635 ${viewport.name}`;

    await j.step('A new enabled routine waits for its scheduled time instead of firing right away', async () => {
      const made = await request.post(`${base}/api/routines`, {
        data: { id, name, agent_id: 'ghost-635', schedule_type: 'interval', interval_seconds: 3600,
          prompt_template: 'never sent', enabled: true },
      });
      if (!made.ok()) throw new Error(`create -> ${made.status()}`);
      // Two scheduler ticks (10 s each) plus slack: the old "never ran so it's due" fallback fired here.
      await page.waitForTimeout(25000);
      const r = await find(request, base, id);
      j.note(`after 25 s: last_run_at ${r.last_run_at}, status ${r.last_status}, next_run_at ${r.next_run_at}`);
      if (r.last_run_at) throw new Error(`fired without its slot at ${r.last_run_at}`);
      if (!r.next_run_at) throw new Error('no next run was scheduled');
      if (msUntil(r.next_run_at) < 0.8 * HOUR_MS) throw new Error(`next run too soon: ${r.next_run_at}`);
    }, { timeoutMs: 60000 });

    await j.step('Running it by hand with a missing agent fails once and moves the next run forward', async () => {
      const run = await (await request.post(`${base}/api/routines/${encodeURIComponent(id)}/run`)).json();
      if (run.status !== 'failed') throw new Error(`expected failed, got ${run.status}`);
      const after = await find(request, base, id);
      if (msUntil(after.next_run_at) < 0.8 * HOUR_MS) throw new Error(`next run not moved forward: ${after.next_run_at}`);
      await page.waitForTimeout(22000);
      const later = await find(request, base, id);
      j.note(`failed run at ${after.last_run_at}; 22 s later last_run_at ${later.last_run_at}; next ${later.next_run_at}`);
      if (later.last_run_at !== after.last_run_at) throw new Error('the failed routine re-fired (retry storm)');
    }, { timeoutMs: 60000 });

    await j.step('Pausing and resuming it in Routines Studio schedules the next slot from now', async () => {
      await openApp(page, base);
      await page.locator('#dock-routines').click();
      await page.locator('#view-routines').waitFor({ state: 'visible', timeout: 20000 });
      // The Agent filter starts on the active agent; show every agent, then find this routine.
      await clickExpect(page.locator('#routinesFilterClearBtn'), async () => {
        await waitFor(async () => (await page.locator('#routinesFilterAgent').inputValue()) === '', { timeoutMs: 5000 });
      }, { label: 'Clear', what: 'filters cleared' });
      await page.locator('#routinesFilterSearch').fill(id);
      const card = () => page.locator('#routinesGrid > *').filter({ hasText: name }).first();
      await card().waitFor({ state: 'visible', timeout: 15000 });
      await clickExpect(card().locator('.toggle-routine-btn'), async () => {
        await waitFor(async () => (await find(request, base, id)).enabled === false, { timeoutMs: 10000 });
      }, { label: 'Pause', what: 'routine paused' });
      await card().waitFor({ state: 'visible', timeout: 15000 });
      await clickExpect(card().locator('.toggle-routine-btn'), async () => {
        await waitFor(async () => (await find(request, base, id)).enabled === true, { timeoutMs: 10000 });
      }, { label: 'Resume', what: 'routine resumed' });
      const r = await find(request, base, id);
      j.note(`resumed: next_run_at ${r.next_run_at}`);
      if (msUntil(r.next_run_at) < 0.8 * HOUR_MS) throw new Error(`resume kept a stale or immediate slot: ${r.next_run_at}`);
      await j.screenshot('routines-studio-resumed');
      await request.delete(`${base}/api/routines/${encodeURIComponent(id)}`).catch(() => {});
    }, { timeoutMs: 90000 });
  },
};
