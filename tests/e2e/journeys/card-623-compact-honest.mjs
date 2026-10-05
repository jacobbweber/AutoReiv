/**
 * CARD-623: Compact is honest — empty/short chat says already compact; API no-op after a real shrink.
 */
import { openApp } from './lib/app.mjs';
import { waitFor } from './lib/runner.mjs';

async function ensureChat(page) {
  if (!(await page.locator('#promptInput').isVisible().catch(() => false))) {
    await page.locator('#dock-chat').click();
  }
  await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 15000 });
}

async function openCompact(page) {
  const drawer = page.locator('#chatOptionsDrawer');
  if (await drawer.evaluate((el) => el.classList.contains('hidden')).catch(() => true)) {
    await page.locator('#chatOptionsToggleBtn').click();
  }
  await page.locator('#chatManualCompactBtn').waitFor({ state: 'visible', timeout: 10000 });
  return page.locator('#chatManualCompactBtn');
}

async function toastText(page) {
  await waitFor(async () => (await page.locator('#toastContainer > div').count()) > 0, { timeoutMs: 10000 });
  return (await page.locator('#toastContainer > div').last().innerText()).replace(/\s+/g, ' ').trim();
}

export default {
  id: 'card-623-compact-honest',
  card: 'CARD-623',
  title: 'Compact already-compact toast and API honesty',
  async run(j, { page, request, base }) {
    await j.step('API: empty session compact is success with compaction_applied false', async () => {
      const sess = await (await request.post(base + '/api/sessions', { data: { agent_id: 'autoreiv', title: '623 empty ' + Date.now() } })).json();
      const res = await request.post(base + `/api/sessions/${sess.id}/compact`);
      const data = await res.json();
      if (!res.ok()) throw new Error('compact HTTP ' + res.status());
      if (data.success !== true || data.compaction_applied !== false) {
        throw new Error('empty compact should be already compact: ' + JSON.stringify(data));
      }
    });

    await j.step('UI: Compact on a fresh chat toasts already compact', async () => {
      await openApp(page, base);
      await ensureChat(page);
      const compact = await openCompact(page);
      await compact.click();
      const text = await toastText(page);
      if (!/already compact/i.test(text)) throw new Error('expected already compact toast, got: ' + text);
    });
  },
};
