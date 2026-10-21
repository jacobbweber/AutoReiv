/**
 * CARD-735 journey: Fix vision attachment timeout, retry carry-forward, and image prompt note.
 * 1) Open Chat Studio, start a new session, and attach a PNG image via #chatFileInput.
 * 2) Verify the staged attachment chip renders in #chatAttachmentsPreviewList.
 * 3) Send the turn, wait for completion, and verify the persisted user prompt carries IMAGE_ONLY_NOTE
 *    ("do not call `read_document_file` on image files") and completes without read_document_file .png errors.
 */
import { waitFor } from './lib/runner.mjs';
import {
  openApp,
  openTab,
  send,
  trackStreams,
  waitReplyIdle,
} from './lib/app.mjs';

const PNG_BYTES = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
  'base64',
);

export default {
  id: 'card-735-fix-vision-attachment-timeout-retry-carry',
  card: 'CARD-735',
  title: 'Image attachment turn uses IMAGE_ONLY_NOTE and completes without read_document_file .png errors',
  allow: [],
  async run(j, { page, request, base }) {
    const streams = trackStreams(page);

    await j.step('Attach a PNG image in Chat, send the turn, and verify IMAGE_ONLY_NOTE and clean reply', async () => {
      await openApp(page, base);
      await openTab(page, 'chat');
      await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 15000 });
      if (await page.locator('#newSessionBtn').isVisible().catch(() => false)) {
        await page.locator('#newSessionBtn').click();
        await page.waitForTimeout(400);
      }

      await page.locator('#chatFileInput').setInputFiles({
        name: 'card735_slide.png',
        mimeType: 'image/png',
        buffer: PNG_BYTES,
      });

      await waitFor(
        async () => {
          const previewText = (await page.locator('#chatAttachmentsPreviewList').innerText().catch(() => '')) || '';
          return previewText.includes('card735_slide.png');
        },
        { timeoutMs: 15000, label: 'staged PNG attachment chip rendered' },
      );

      const prevStreams = streams.count;
      await send(
        page,
        'Reply in one short sentence acknowledging my message. Do not call any tools.',
      );
      await waitFor(() => streams.count > prevStreams, { timeoutMs: 20000, label: 'chat stream started' });
      await waitReplyIdle(page, { timeoutMs: 120000 });

      const activeSid = await page.evaluate(() => localStorage.getItem('autoreiv_active_session_id'));
      if (!activeSid) {
        throw new Error('Expected active session ID in localStorage after sending image turn');
      }

      const msgRes = await request.get(`${base}/api/sessions/${activeSid}/messages`);
      if (!msgRes.ok()) {
        throw new Error(`GET /api/sessions/${activeSid}/messages failed with ${msgRes.status()}`);
      }
      const messages = await msgRes.json();
      const userMsg = messages.find((m) => m.role === 'user');
      if (!userMsg || !userMsg.content) {
        throw new Error(`Expected saved user message in session ${activeSid}`);
      }
      if (!userMsg.content.includes('do not call `read_document_file` on image files')) {
        throw new Error(`Expected IMAGE_ONLY_NOTE in user message content, got: ${userMsg.content}`);
      }
      if (userMsg.content.includes('You can read documents using `read_document_file`')) {
        throw new Error(`Unexpected AGENT_NOTE in image-only user message: ${userMsg.content}`);
      }

      const containerText = await page.locator('#messagesContainer').innerText();
      if (containerText.includes('Unsupported document format: .png')) {
        throw new Error('Unexpected read_document_file .png error in chat thread');
      }
      j.note(`Verified IMAGE_ONLY_NOTE and clean image attachment turn on session ${activeSid}`);
    }, { timeoutMs: 180000 });
  },
};
