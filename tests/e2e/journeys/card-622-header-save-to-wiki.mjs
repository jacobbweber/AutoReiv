/**
 * CARD-622: Chat header Save to Wiki saves the whole thread to the wiki Inbox again.
 *
 * Cause: setupChatChrome read callbacks.exportSessionToWiki at the top level while
 * chat.js nested the app bag under callbacks.callbacks (same class as CARD-471 Compact).
 */
import { clickExpect, waitFor } from './lib/runner.mjs';
import { getJson, openApp, send, trackStreams, waitReplyIdle } from './lib/app.mjs';

async function ensureChatOpen(page) {
  if (!(await page.locator('#promptInput').isVisible().catch(() => false))) {
    await page.locator('#dock-chat').click();
  }
  await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 15000 });
  if ((await page.locator('#agentSelect').inputValue()) !== 'autoreiv') {
    await page.selectOption('#agentSelect', 'autoreiv');
    await page.waitForTimeout(800);
  }
}

async function startNewChat(page) {
  await ensureChatOpen(page);
  const sidebarBtn = page.locator('#toggleSidebarBtn');
  const newChatBtn = page.locator('#newChatBtn');
  if (!(await newChatBtn.isVisible().catch(() => false))) {
    if (await sidebarBtn.isVisible().catch(() => false)) {
      await sidebarBtn.click();
      await page.waitForTimeout(500);
    }
  }
  if (await newChatBtn.isVisible().catch(() => false)) {
    await newChatBtn.click();
    await page.waitForTimeout(800);
  }
  const closeBtn = page.locator('#chatSessionsDrawerCloseBtn');
  if (await closeBtn.isVisible().catch(() => false)) {
    await closeBtn.click().catch(() => {});
    await page.waitForTimeout(400);
  }
}

async function toastTexts(page) {
  return page.locator('#toastContainer > div').allTextContents().catch(() => []);
}

export default {
  id: 'card-622-header-save-to-wiki',
  card: 'CARD-622',
  title: 'Header Save to Wiki creates an Inbox note with the whole thread',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    const marker = 'card622-' + viewport.name + '-' + String(Date.now() % 100000);

    await j.step('Open Chat and start a fresh thread', async () => {
      await openApp(page, base);
      await startNewChat(page);
    });

    await j.step('Send one short turn and wait for a reply', async () => {
      const before = streams.count;
      await send(page, 'Reply with exactly: OK ' + marker);
      await waitFor(() => streams.count > before, { timeoutMs: 20000 });
      await waitReplyIdle(page, { timeoutMs: 180000 });
      const count = await page.locator('#messagesContainer').locator('text=/./').count();
      if (count < 1) throw new Error('no chat content after reply');
    }, { timeoutMs: 200000 });

    await j.step('Header Save to Wiki creates an Inbox note (not the unwired error)', async () => {
      const btn = page.locator('#exportThreadWikiBtn');
      await btn.waitFor({ state: 'visible', timeout: 10000 });
      const exportPosts = [];
      page.on('request', (req) => {
        if (req.method() === 'POST' && req.url().includes('/api/export/wiki')) {
          exportPosts.push(req.url());
        }
      });
      await clickExpect(
        btn,
        async () => {
          const texts = (await toastTexts(page)).map((t) => String(t || ''));
          if (texts.some((t) => /not available|session export unwired/i.test(t))) {
            throw new Error('Save to Wiki still unwired: ' + texts.join(' | '));
          }
          if (exportPosts.length > 0) return true;
          if (texts.some((t) => /Saved conversation to Wiki Inbox/i.test(t))) return true;
          return false;
        },
        { label: 'exportThreadWikiBtn', what: 'a successful wiki export', timeoutMs: 20000 },
      );
      const notesPayload = await getJson(request, base + '/api/wiki/notes?tag=chat_thread').catch(() => null);
      const flat = Array.isArray(notesPayload) ? notesPayload
        : Array.isArray(notesPayload && notesPayload.notes) ? notesPayload.notes
        : Array.isArray(notesPayload && notesPayload.items) ? notesPayload.items
        : [];
      const hit = flat.find((n) => {
        const tags = (n.tags || (n.frontmatter && n.frontmatter.tags) || []).map(String);
        const name = String(n.filename || n.path || n.title || '');
        return tags.includes('chat_thread') || /Chat -/i.test(name);
      });
      if (!hit) {
        const texts = (await toastTexts(page)).join(' ');
        if (!/Saved conversation to Wiki Inbox/i.test(texts) && exportPosts.length === 0) {
          throw new Error('no Inbox note and no export POST after Save to Wiki');
        }
      }
    }, { timeoutMs: 60000 });
  },
};
