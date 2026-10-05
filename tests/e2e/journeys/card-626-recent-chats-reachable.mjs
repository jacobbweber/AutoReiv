/**
 * CARD-626: every Recent Chats row is clickable on desktop (not under the composer).
 *
 * Seeds 8 chats, opens the sessions drawer, scrolls the last row into view, asserts
 * elementFromPoint at the row centre is the row (not #promptInput / #chatForm), then
 * clicks it and expects the drawer to close.
 */
import { clickExpect, waitFor } from './lib/runner.mjs';
import { openApp } from './lib/app.mjs';

async function seedSessions(request, base, count, tag) {
  const made = [];
  for (let i = 0; i < count; i += 1) {
    const res = await request.post(base + '/api/sessions', {
      data: { agent_id: 'autoreiv', title: '626 row ' + String(i + 1) + ' ' + tag },
    });
    if (!res.ok()) throw new Error('POST /api/sessions -> ' + res.status());
    made.push(await res.json());
    // titles sort by updated_at; small gap keeps order stable enough for "last in list"
    await new Promise((r) => setTimeout(r, 200));
  }
  return made;
}

async function ensureChatOpen(page) {
  if (!(await page.locator('#promptInput').isVisible().catch(() => false))) {
    await page.locator('#dock-chat').click();
  }
  await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 15000 });
  if ((await page.locator('#agentSelect').inputValue()) !== 'autoreiv') {
    await page.selectOption('#agentSelect', 'autoreiv');
    await page.waitForTimeout(600);
  }
}

async function openSessionsDrawer(page) {
  const drawer = page.locator('#chatSessionsDrawer');
  if (await drawer.evaluate((el) => el.classList.contains('hidden')).catch(() => true)) {
    await page.locator('#toggleSidebarBtn').click();
  }
  await drawer.waitFor({ state: 'visible', timeout: 10000 });
}

async function hitTestCenter(page, locator) {
  const box = await locator.boundingBox();
  if (!box) throw new Error('no bounding box');
  const x = box.x + box.width / 2;
  const y = box.y + box.height / 2;
  const info = await page.evaluate(({ x, y }) => {
    const el = document.elementFromPoint(x, y);
    if (!el) return { id: null, tag: null, text: '' };
    const row = el.closest('#sessionList > div');
    return {
      id: el.id || null,
      tag: el.tagName,
      inSessionRow: !!row,
      rowText: row ? (row.textContent || '').trim().slice(0, 80) : '',
    };
  }, { x, y });
  return { x, y, box, ...info };
}

export default {
  id: 'card-626-recent-chats-reachable',
  card: 'CARD-626',
  title: 'Last Recent Chats row is clickable above the composer on desktop and phone',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    // Journey runner sets viewport; also re-check the short desktop height from the card.
    const tag = viewport.name + '-' + String(Date.now() % 100000);
    const seeded = await seedSessions(request, base, 8, tag);
    const last = seeded[seeded.length - 1];

    await j.step('Open Chat with 8 seeded Recent Chats', async () => {
      await openApp(page, base);
      await ensureChatOpen(page);
      await waitFor(
        async () => (await page.locator('#sessionList > div', { hasText: last.title }).count()) >= 1,
        { timeoutMs: 15000 },
      );
    });

    await j.step('Open Sessions drawer and scroll the last row into view', async () => {
      await openSessionsDrawer(page);
      const row = page.locator('#sessionList > div', { hasText: last.title }).first();
      await row.scrollIntoViewIfNeeded();
      await page.waitForTimeout(300);
    });

    await j.step('Last row centre hit-tests to the row (not the composer)', async () => {
      const row = page.locator('#sessionList > div', { hasText: last.title }).first();
      const hit = await hitTestCenter(page, row);
      if (hit.id === 'promptInput' || hit.id === 'chatForm') {
        throw new Error('composer still intercepts last row at (' + hit.x + ',' + hit.y + ') id=' + hit.id);
      }
      if (!hit.inSessionRow) {
        throw new Error('elementFromPoint missed session row: ' + JSON.stringify(hit));
      }
    });

    await j.step('Clicking the last row opens that chat (drawer closes)', async () => {
      const row = page.locator('#sessionList > div', { hasText: last.title }).first();
      await clickExpect(
        row,
        async () => {
          const hidden = await page.locator('#chatSessionsDrawer').evaluate((el) => el.classList.contains('hidden'));
          return hidden;
        },
        { label: 'last Recent Chats row', what: 'drawer close', timeoutMs: 10000 },
      );
    });

    // Extra desktop short-height check only when viewport is desktop-sized.
    if (viewport.name === 'desktop') {
      await j.step('Also reachable at 1024x640 (card repro size)', async () => {
        await page.setViewportSize({ width: 1024, height: 640 });
        await openSessionsDrawer(page);
        // Re-seed visibility: list still has the last title
        const row = page.locator('#sessionList > div', { hasText: last.title }).first();
        await row.scrollIntoViewIfNeeded();
        await page.waitForTimeout(200);
        const hit = await hitTestCenter(page, row);
        if (hit.id === 'promptInput' || hit.id === 'chatForm' || !hit.inSessionRow) {
          throw new Error('1024x640 still blocked: ' + JSON.stringify(hit));
        }
      });
    }
  },
};
