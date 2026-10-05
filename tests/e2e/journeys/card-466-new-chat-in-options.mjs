/**
 * CARD-466: New chat lives under + Options; sessions drawer has no New Conversation.
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
  id: 'card-466-new-chat-in-options',
  card: 'CARD-466',
  title: 'New chat under + Options menu',
  async run(j, { page, base }) {
    await j.step('+ Options shows New chat; sessions drawer does not', async () => {
      await openApp(page, base);
      await ensureChat(page);
      const n = await page.locator('#newChatBtn').count();
      if (n !== 1) throw new Error('expected exactly one #newChatBtn, got ' + n);
      if (await page.locator('#chatSessionsDrawer #newChatBtn').count()) {
        throw new Error('newChatBtn still inside sessions drawer');
      }
      const drawer = page.locator('#chatOptionsDrawer');
      if (await drawer.evaluate((el) => el.classList.contains('hidden'))) {
        await page.locator('#chatOptionsToggleBtn').click();
      }
      await page.locator('#chatOptionsDrawer #newChatBtn').waitFor({ state: 'visible', timeout: 5000 });
      const label = (await page.locator('#chatOptionsDrawer #newChatBtn').innerText()).replace(/\s+/g, ' ').trim();
      if (!/New chat/i.test(label)) throw new Error('label was: ' + label);
    });

    await j.step('New chat closes Options and starts a conversation', async () => {
      const before = await page.locator('#sessionList > div').count().catch(() => 0);
      await page.locator('#chatOptionsDrawer #newChatBtn').click();
      await waitFor(async () => {
        const expanded = await page.locator('#chatOptionsToggleBtn').getAttribute('aria-expanded');
        return expanded === 'false';
      }, { timeoutMs: 8000 });
      const hidden = await page.locator('#chatOptionsDrawer').evaluate((el) => el.classList.contains('hidden'));
      if (!hidden) throw new Error('options drawer still open');
      await waitFor(async () => (await page.locator('#sessionList > div').count()) >= Math.max(1, before), { timeoutMs: 15000 });
      await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 10000 });
    });

    await j.step('Sessions drawer lists recent chats without a New Conversation button', async () => {
      if (await page.locator('#chatSessionsDrawer').evaluate((el) => el.classList.contains('hidden'))) {
        await page.locator('#toggleSidebarBtn').click();
      }
      await page.locator('#chatSessionsDrawer').waitFor({ state: 'visible', timeout: 8000 });
      if (await page.locator('#chatSessionsDrawer #newChatBtn').count()) {
        throw new Error('sessions drawer still has newChatBtn');
      }
      const sub = (await page.locator('#chatSessionsDrawer p.font-mono').first().innerText()).trim();
      if (!/^Recent$/i.test(sub)) throw new Error('subtitle expected Recent, got: ' + sub);
    });
  },
};
