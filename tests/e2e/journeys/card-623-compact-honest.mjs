/**
 * CARD-623: Compact is honest — empty session API and UI toast say already compact.
 */
import { openApp } from './lib/app.mjs';
import { waitFor } from './lib/runner.mjs';

async function ensureChat(page) {
  if (!(await page.locator('#promptInput').isVisible().catch(() => false))) {
    await page.locator('#dock-chat').click();
  }
  await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 15000 });
  if ((await page.locator('#agentSelect').inputValue().catch(() => '')) !== 'autoreiv') {
    await page.selectOption('#agentSelect', 'autoreiv').catch(() => {});
    await page.waitForTimeout(800);
  }
  // Wait until Chat has an active session (desktop can open with none briefly).
  await waitFor(async () => {
    const sid = await page.evaluate(() => {
      try {
        return localStorage.getItem('autoreiv.activeSessionId')
          || localStorage.getItem('autoreiv_last_session_id')
          || document.body.getAttribute('data-active-session')
          || '';
      } catch { return ''; }
    });
    // Also: composer enabled / session chip
    const hasList = (await page.locator('#sessionList > div').count()) > 0;
    return Boolean(sid) || hasList;
  }, { timeoutMs: 15000 });
  // If still no session row, click New chat if present in options, else send a noop via creating through UI
  if ((await page.locator('#sessionList > div').count()) === 0) {
    const drawer = page.locator('#chatOptionsDrawer');
    if (await drawer.evaluate((el) => el.classList.contains('hidden')).catch(() => true)) {
      await page.locator('#chatOptionsToggleBtn').click();
    }
    // Prefer creating by posting a session via evaluate fetch using cookies
    await page.evaluate(async () => {
      const res = await fetch('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: 'autoreiv', title: '623 journey' }),
      });
      const s = await res.json();
      // Trigger UI pick if a global exists; otherwise reload
      if (s && s.id) {
        localStorage.setItem('autoreiv_last_session_autoreiv', s.id);
        location.reload();
      }
    });
    await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 20000 });
    await page.waitForTimeout(1000);
  }
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

    await j.step('UI: Compact on a chat with an active session toasts already compact', async () => {
      await openApp(page, base);
      await ensureChat(page);
      // Create + select a session the UI will use
      const sess = await (await request.post(base + '/api/sessions', { data: { agent_id: 'autoreiv', title: '623 ui ' + Date.now() } })).json();
      await page.evaluate(async (id) => {
        // Prefer the real sessions drawer pick if listed after reload
        localStorage.setItem('autoreiv_last_session_autoreiv', id);
      }, sess.id);
      await page.reload({ waitUntil: 'domcontentloaded' });
      await ensureChat(page);
      // Open sessions drawer and click the row if present
      const drawerHidden = await page.locator('#chatSessionsDrawer').evaluate((el) => el.classList.contains('hidden')).catch(() => true);
      if (drawerHidden) await page.locator('#toggleSidebarBtn').click().catch(() => {});
      const row = page.locator('#sessionList > div', { hasText: '623 ui' }).first();
      if (await row.count()) {
        await row.click();
        await page.waitForTimeout(600);
      }
      const compact = await openCompact(page);
      await compact.click();
      const text = await toastText(page);
      if (!/already compact/i.test(text)) throw new Error('expected already compact toast, got: ' + text);
    });
  },
};
