/**
 * CARD-637: Routines Studio's Agent filter starts on "All agents" and keeps it. A fresh browser lists
 * every routine; picking an agent and then All agents survives a Studio refresh (which refetches the
 * agent roster and used to snap the filter to the first agent) and a page reload. No model is called.
 */
import { getJson, openApp } from './lib/app.mjs';

const BUILTINS = ['hourly-sre-pulse', 'education-retrieval-retention', 'wiki-curation', 'weekly-note-rollover', 'telemetry-friction-auditor'];

async function openRoutines(page, base) {
  await openApp(page, base);
  // A reload can restore the Routines window; clicking the dock again would minimize it.
  await page.waitForTimeout(1500);
  if (!(await page.locator('#view-routines').isVisible())) await page.locator('#dock-routines').click();
  await page.locator('#view-routines').waitFor({ state: 'visible', timeout: 20000 });
}

async function shown(page) {
  const text = await page.locator('#routinesGrid').innerText();
  return BUILTINS.filter((id) => text.includes(id));
}

async function expectAll(j, page, label) {
  // Two refetches of /api/agents happen as the Studio loads; the old bug snapped the filter after them.
  await page.waitForTimeout(3000);
  const value = await page.locator('#routinesFilterAgent').inputValue();
  const optionText = (await page.locator('#routinesFilterAgent option:checked').innerText()).trim();
  const stored = await page.evaluate(() => localStorage.getItem('autoreiv_routines_filter_agent'));
  const ids = await shown(page);
  j.note(`${label}: filter "${optionText}" (value "${value}", stored ${JSON.stringify(stored)}); routines shown ${ids.length}: ${ids.join(', ')}`);
  if (value !== '' || optionText !== 'All agents') throw new Error(`${label}: filter is "${optionText}" (${value}), not All agents`);
  if (ids.length !== BUILTINS.length) throw new Error(`${label}: ${ids.length} of ${BUILTINS.length} routines shown`);
}

export default {
  id: 'card-637-routines-filter-all-agents',
  card: 'CARD-637',
  title: 'Routines filter keeps All agents',
  async run(j, { page, request, base }) {
    await j.step('A fresh browser opens Routines on All agents with all five routines listed', async () => {
      const ids = (await getJson(request, `${base}/api/routines`)).map((r) => r.id);
      if (BUILTINS.some((id) => !ids.includes(id))) throw new Error(`env is missing builtins: ${ids.join(', ')}`);
      await openRoutines(page, base);
      await page.locator('#routinesGrid').getByText('hourly-sre-pulse', { exact: true }).first().waitFor({ state: 'visible', timeout: 15000 });
      await expectAll(j, page, 'fresh');
      await j.screenshot('all-agents-fresh');
    }, { timeoutMs: 60000 });

    await j.step('Picking AutoReiv, then All agents, survives a Studio refresh', async () => {
      await page.selectOption('#routinesFilterAgent', 'autoreiv');
      await page.waitForTimeout(800);
      const mine = await shown(page);
      j.note(`autoreiv filter shows ${mine.length}: ${mine.join(', ')}`);
      if (mine.length !== 4 || mine.includes('education-retrieval-retention')) throw new Error('autoreiv filter did not narrow the list');
      await page.selectOption('#routinesFilterAgent', '');
      await page.locator('#refreshRoutinesBtn').click();
      await expectAll(j, page, 'after refresh');
    }, { timeoutMs: 60000 });

    await j.step('All agents is still selected after a page reload', async () => {
      await page.reload({ waitUntil: 'domcontentloaded' });
      await openRoutines(page, base);
      await page.locator('#routinesGrid').getByText('hourly-sre-pulse', { exact: true }).first().waitFor({ state: 'visible', timeout: 15000 });
      await expectAll(j, page, 'after reload');
      await j.screenshot('all-agents-after-reload');
    }, { timeoutMs: 60000 });
  },
};
