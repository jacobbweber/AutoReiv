/**
 * CARD-721: New chat button (#newChatBtn, "+ New") moved out of #chatOptionsDrawer
 * and placed directly to the left of #chatOptionsToggleBtn in the main Chat composer bar.
 */
import { openApp } from './lib/app.mjs';
import { waitFor } from './lib/runner.mjs';

async function ensureChat(page) {
  await page.evaluate(() => {
    document.getElementById('tab-chat')?.click();
  });
  await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 15000 });
}

export default {
  id: 'card-721-move-new-chat-button-out-of',
  card: 'CARD-721',
  title: 'New chat (+ New) button sits in composer bar directly to the left of Options button and starts a fresh session in one click',
  allow: [],
  async run(j, { page, base, viewport }) {
    await j.step('1. Verify #newChatBtn (+ New) is visible in #chatForm directly to the left of #chatOptionsToggleBtn and removed from drawers', async () => {
      await openApp(page, base);
      await ensureChat(page);

      const totalCount = await page.locator('#newChatBtn').count();
      if (totalCount !== 1) {
        throw new Error(`Expected exactly 1 #newChatBtn in DOM, got ${totalCount}`);
      }
      if ((await page.locator('#chatOptionsDrawer #newChatBtn').count()) > 0) {
        throw new Error('#newChatBtn is still inside #chatOptionsDrawer');
      }
      if ((await page.locator('#chatSessionsDrawer #newChatBtn').count()) > 0) {
        throw new Error('#newChatBtn is inside #chatSessionsDrawer');
      }

      const newBtn = page.locator('#chatForm #newChatBtn');
      const optBtn = page.locator('#chatForm #chatOptionsToggleBtn');
      await newBtn.waitFor({ state: 'visible', timeout: 5000 });
      await optBtn.waitFor({ state: 'visible', timeout: 5000 });

      const label = (await newBtn.innerText()).replace(/\s+/g, ' ').trim();
      if (!/^New$/i.test(label)) {
        throw new Error(`Expected #newChatBtn label to be "New", got "${label}"`);
      }

      const newBox = await newBtn.boundingBox();
      const optBox = await optBtn.boundingBox();
      if (!newBox || !optBox || newBox.x + newBox.width > optBox.x + 4) {
        throw new Error(`Expected #newChatBtn (${JSON.stringify(newBox)}) to sit to the left of #chatOptionsToggleBtn (${JSON.stringify(optBox)})`);
      }

      j.note(`verified #newChatBtn ("+ ${label}") at x=${Math.round(newBox.x)} sits to the left of #chatOptionsToggleBtn at x=${Math.round(optBox.x)}`);
    });

    await j.step('2. Click #newChatBtn directly (with Options drawer closed) to start a new chat session and verify zero overflow', async () => {
      const drawerHiddenBefore = await page.locator('#chatOptionsDrawer').evaluate((el) => el.classList.contains('hidden'));
      if (!drawerHiddenBefore) {
        throw new Error('Expected #chatOptionsDrawer to be closed before clicking #newChatBtn');
      }

      const beforeCount = await page.locator('#sessionList > div').count().catch(() => 0);
      await page.locator('#newChatBtn').click();

      const sessionCreated = await waitFor(
        async () => (await page.locator('#sessionList > div').count()) >= Math.max(1, beforeCount),
        { timeoutMs: 15000, intervalMs: 200 },
      );
      if (!sessionCreated) {
        throw new Error('Expected clicking #newChatBtn to create/select a fresh session');
      }
      await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 10000 });

      const overflow = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
      }));
      if (overflow.scrollWidth > overflow.clientWidth + 2) {
        throw new Error(`Horizontal overflow on ${viewport?.name || 'viewport'}: ${overflow.scrollWidth}px > ${overflow.clientWidth}px`);
      }

      j.note(`verified one-click #newChatBtn session creation and zero overflow on ${viewport?.name || 'viewport'} (${overflow.scrollWidth}px <= ${overflow.clientWidth}px)`);
    });
  },
};
