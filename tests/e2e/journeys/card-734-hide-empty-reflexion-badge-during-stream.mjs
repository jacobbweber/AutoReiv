/**
 * CARD-734 journey: Hide empty reflexion badge during chat streaming.
 * 1) Open Chat Studio, start a new session, and send a prompt that streams a normal assistant response.
 * 2) Observe the active streaming bubble (`[data-job-chrome-card="1"]`) while streaming is in progress and assert `.reflexion-status-badge` remains `.hidden` (never rendered as an empty amber box above Thinking Process).
 * 3) Wait for the turn to complete and verify the final message renders cleanly with no empty reflexion badge.
 */
import { waitFor } from './lib/runner.mjs';
import {
  isStreaming,
  openApp,
  openTab,
  send,
  trackStreams,
  waitReplyIdle,
} from './lib/app.mjs';

export default {
  id: 'card-734-hide-empty-reflexion-badge-during-stream',
  card: 'CARD-734',
  title: 'Reflexion status badge stays hidden during normal chat streaming',
  allow: [],
  async run(j, { page, base }) {
    const streams = trackStreams(page);

    await j.step('Stream a normal chat turn and verify .reflexion-status-badge never unhides empty', async () => {
      await openApp(page, base);
      await openTab(page, 'chat');
      await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 15000 });
      if (await page.locator('#newSessionBtn').isVisible().catch(() => false)) {
        await page.locator('#newSessionBtn').click();
        await page.waitForTimeout(400);
      }

      // Install a MutationObserver on #messagesContainer before sending so even a sub-100ms unhide is caught
      await page.evaluate(() => {
        window.__card734EmptyBadgeUnhidden = false;
        const container = document.getElementById('messagesContainer');
        if (!container) return;
        const checkBadges = () => {
          const badges = container.querySelectorAll('.reflexion-status-badge');
          for (const b of badges) {
            if (!b.classList.contains('hidden') && !b.textContent.trim()) {
              window.__card734EmptyBadgeUnhidden = true;
            }
          }
        };
        const obs = new MutationObserver(checkBadges);
        obs.observe(container, { childList: true, subtree: true, attributes: true, attributeFilter: ['class'] });
        window.__card734Observer = obs;
      });

      const n = streams.count;
      await send(
        page,
        'Reply with two short sentences explaining why automated tests are useful. Do not call any tools.',
      );
      await waitFor(() => streams.count > n, { timeoutMs: 20000, label: 'chat stream started' });

      // Wait until either streaming bubble is mounted or streaming finishes
      await waitFor(
        async () => {
          const hasBubble = (await page.locator('[data-job-chrome-card="1"]').count()) > 0;
          const streaming = await isStreaming(page);
          return hasBubble || !streaming;
        },
        { timeoutMs: 30000, intervalMs: 100, label: 'stream bubble mounted or stream completed' },
      );

      // Check badge state during stream if bubble is present
      const badgeCount = await page.locator('.reflexion-status-badge').count();
      if (badgeCount > 0) {
        const isBadgeHidden = await page
          .locator('.reflexion-status-badge')
          .first()
          .evaluate((el) => el.classList.contains('hidden'));
        if (!isBadgeHidden) {
          throw new Error('Expected .reflexion-status-badge to have class "hidden" during normal chat stream');
        }
      }

      await waitReplyIdle(page, { timeoutMs: 120000 });

      const emptyUnhidden = await page.evaluate(() => {
        if (window.__card734Observer) window.__card734Observer.disconnect();
        return Boolean(window.__card734EmptyBadgeUnhidden);
      });
      if (emptyUnhidden) {
        throw new Error('MutationObserver caught an empty .reflexion-status-badge unhidden during chat streaming');
      }

      const msgText = await page.locator('#messagesContainer').innerText();
      if (!msgText || msgText.trim().length < 20) {
        throw new Error(`Expected assistant reply in #messagesContainer, got: ${JSON.stringify(msgText)}`);
      }
      j.note('Verified .reflexion-status-badge stayed hidden throughout the entire streaming lifecycle');
    }, { timeoutMs: 180000 });
  },
};
