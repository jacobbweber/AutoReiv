/**
 * CARD-532 journey for CARD-530: approve a HITL card while the Developer reply is still streaming.
 * Expect one turn, one reply, the job ends done (or failed with a reason, never running), no "Reply failed".
 */
import { clickExpect, waitFor } from './lib/runner.mjs';
import { HITL_CARD, isStreaming, jobStripText, openApp, sessionJobStatus, trackStreams, waitReplyIdle } from './lib/app.mjs';

export default {
  id: 'card-530-approve-mid-stream',
  card: 'CARD-530',
  title: 'Approve a HITL card while the Developer reply is still streaming',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    const tool = `get_moon_phase_${viewport.name}_${Date.now() % 100000}`;
    let sessionId = '';
    let cardSeen = false;

    await j.step('Open Tools Studio and describe a small tool', async () => {
      await openApp(page, base);
      await page.locator('#dock-tools-studio').click();
      await page.locator('#toolsStudioToolNameInput').waitFor({ state: 'visible', timeout: 15000 });
      await page.selectOption('#toolsStudioIntentSelect', 'create');
      await page.locator('#toolsStudioToolNameInput').fill(tool);
      await page.locator('#toolsStudioBehaviorInput').fill('Return the moon phase name for a given date (pure computation, no network, no API key). Before registering, submit a proposal with propose_tool and wait for my approval.');
    });

    await j.step('Talk to developer opens a Developer chat that starts replying', async () => {
      const talk = page.waitForResponse((r) => r.url().includes('/api/tools_studio/authoring/talk'), { timeout: 30000 });
      await clickExpect(page.locator('#toolsStudioTalkBtn'), () => streams.count >= 1, { label: 'Talk to developer', what: 'a Developer reply (POST /api/chat/stream)', timeoutMs: 30000 });
      sessionId = String((await (await talk).json()).session_id || '');
      if (!sessionId) throw new Error('Talk did not return a session_id');
    });

    await j.step('An approval card appears while the reply is still streaming', async () => {
      const card = page.locator(HITL_CARD).first();
      const seen = await waitFor(async () => {
        if (await card.isVisible()) return 'card';
        if (!(await isStreaming(page)) && streams.count >= 1) {
          await page.waitForTimeout(3000);
          if (await card.isVisible()) return 'card';
          if (!(await isStreaming(page))) return 'ended';
        }
        return null;
      }, { timeoutMs: 240000, intervalMs: 500 });
      if (seen !== 'card') throw new Error(seen === 'ended' ? 'the reply ended without an approval card (the model did not file a draft this run)' : 'no approval card within 240 s');
      if (!(await isStreaming(page))) throw new Error('the approval card appeared only after the reply ended; not a mid-stream approval');
      cardSeen = true;
      await card.scrollIntoViewIfNeeded();
    }, { timeoutMs: 250000 });

    await j.step('Approve mid-stream records the decision and starts no second stream', async () => {
      if (!cardSeen) throw new Error('no card to approve');
      const card = page.locator(HITL_CARD).first();
      const id = await card.getAttribute('data-approval-id');
      const before = streams.count;
      await clickExpect(card.locator('[data-hitl-decision="APPROVED"]'), async () => !(await page.locator(`#pendingHitlHost [data-approval-id="${id}"] [data-hitl-decision="APPROVED"]`).isVisible()),
        { label: 'Approve', what: 'the card leaving its pending state', timeoutMs: 15000 });
      await page.waitForTimeout(2500);
      if (streams.count !== before) throw new Error(`Approve started ${streams.count - before} new stream request(s) while the reply was live`);
      j.note(`approved ${id} while streaming=${await isStreaming(page)}`);
    }, { timeoutMs: 30000 });

    await j.step('The reply finishes once and the job ends honestly', async () => {
      await waitReplyIdle(page, { timeoutMs: 360000 });
      const strip = await jobStripText(page);
      j.note(`strip: ${strip}`);
      if (streams.count !== 1 || streams.resumes !== 0) throw new Error(`expected 1 stream and 0 resumes, saw ${streams.count} and ${streams.resumes}`);
      const status = await sessionJobStatus(request, base, sessionId);
      j.note(`job status: ${status}`);
      if (status === 'running' || status === 'queued') throw new Error(`job is still ${status} after the reply ended`);
      if (/Job failed/.test(strip) && !/Job failed:/.test(strip)) throw new Error('strip says failed without a reason');
    }, { timeoutMs: 370000 });

    await j.step('End of chat (evidence)', async () => {
      await page.locator('#messagesContainer').evaluate((el) => { el.scrollTop = el.scrollHeight; });
    });
  },
};
