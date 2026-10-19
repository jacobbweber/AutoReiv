/**
 * CARD-723 journey:
 * 1) POST /api/settings/matrix rejects out-of-range max_concurrent_generations (400) and POST /api/chat/stream rejects invalid approval_mode (400).
 * 2) When #agentSelect is already on 'tutor', creating a Tutor session via POST /api/sessions and calling openSessionByTitle refreshes the drawer and opens it.
 * 3) A Teach card adopted on AutoReiv shows "On for autoreiv", and after the skill is deleted and the chat is reloaded, the card reconciles back to actionable (.btn-adopt-skill).
 */
import { clickExpect, waitFor } from './lib/runner.mjs';
import { getJson, openApp, openSessionByTitle, send, trackStreams, waitReplyIdle } from './lib/app.mjs';

export default {
  id: 'card-723-chat-settings-validation-and-teach-reconcile',
  card: 'CARD-723',
  title: 'Chat/Settings validation, Tutor drawer refresh, and Teach card adoption reconciliation',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    const stamp = `${viewport.name}-${Date.now() % 100000}`;
    const tutorTitle = `Tutor API Chat ${stamp}`;
    const arTitle = `AutoReiv Teach ${stamp}`;
    let arSessionId = '';

    await j.step('Settings matrix and chat stream reject invalid max_concurrent_generations and approval_mode with HTTP 400', async () => {
      const badMatrix = await request.post(`${base}/api/settings/matrix`, {
        data: { default_model: 'default', max_concurrent_generations: 4 },
      });
      if (badMatrix.status() !== 400) {
        throw new Error(`Expected 400 for max_concurrent_generations=4, got ${badMatrix.status()}`);
      }

      const okMatrix = await request.post(`${base}/api/settings/matrix`, {
        data: { default_model: 'default', max_concurrent_generations: 1 },
      });
      if (okMatrix.status() !== 200) {
        throw new Error(`Expected 200 for max_concurrent_generations=1, got ${okMatrix.status()}`);
      }

      const sessRes = await request.post(`${base}/api/sessions`, {
        data: { agent_id: 'autoreiv', title: arTitle },
      });
      if (!sessRes.ok()) throw new Error(`create session -> ${sessRes.status()}`);
      arSessionId = (await sessRes.json()).id;

      const badStream = await request.post(`${base}/api/chat/stream`, {
        data: {
          agent_id: 'autoreiv',
          session_id: arSessionId,
          content: 'test',
          approval_mode: 'auto',
        },
      });
      if (badStream.status() !== 400) {
        throw new Error(`Expected 400 for approval_mode='auto', got ${badStream.status()}`);
      }

      await openApp(page, base);
    }, { timeoutMs: 30000 });

    await j.step('openSessionByTitle opens an API-created Tutor chat even when #agentSelect is already on tutor', async () => {
      if (!(await page.locator('#promptInput').isVisible().catch(() => false))) {
        await page.locator('#dock-chat').click();
      }
      await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 15000 });
      await page.selectOption('#agentSelect', 'tutor');
      await page.waitForTimeout(800);

      // Create the Tutor session via API AFTER #agentSelect is already 'tutor'
      const tutorRes = await request.post(`${base}/api/sessions`, {
        data: { agent_id: 'tutor', title: tutorTitle },
      });
      if (!tutorRes.ok()) throw new Error(`create tutor session -> ${tutorRes.status()}`);

      await openSessionByTitle(page, tutorTitle, { agentId: 'tutor' });
      const activeVal = await page.locator('#agentSelect').inputValue();
      if (activeVal !== 'tutor') throw new Error(`Expected #agentSelect='tutor', got '${activeVal}'`);
    }, { timeoutMs: 45000 });

    await j.step('Adopt a Teach lesson on AutoReiv, remove the skill, and verify the reloaded card reverts from On for autoreiv to Adopt', async () => {
      await openSessionByTitle(page, arTitle, { agentId: 'autoreiv' });
      const n = streams.count;
      await send(page, 'Reply with one word: pong.');
      await waitFor(() => streams.count > n, { timeoutMs: 15000 });
      await waitReplyIdle(page, { timeoutMs: 180000 });

      const teachBtn = page.locator('.msg-teach-agent-btn').last();
      await clickExpect(
        teachBtn,
        () => page.locator('#teachAgentModal').isVisible(),
        { label: 'Teach', what: 'the Teach modal', timeoutMs: 10000 }
      );
      await page.locator('#teachAgentGuidanceInput').fill('Always reply concisely in plain sentences.');
      const proposalCard = page.locator('.skill-proposal-card').last();
      await clickExpect(
        page.locator('#submitTeachAgentBtn'),
        () => proposalCard.isVisible(),
        { label: 'Submit Teach', what: 'the distilled skill proposal card', timeoutMs: 180000 }
      );

      const skillId = await proposalCard.getAttribute('data-skill-id');
      if (!skillId) throw new Error('Proposal card missing data-skill-id');

      const adoptBtn = proposalCard.locator('.btn-adopt-skill');
      await clickExpect(
        adoptBtn,
        async () => (await proposalCard.innerText()).includes('On for'),
        { label: 'Adopt Skill', what: 'On for autoreiv banner', timeoutMs: 20000 }
      );

      // Delete the adopted skill via API and reload the chat
      const delRes = await request.delete(`${base}/api/skills/user-skills/${encodeURIComponent(skillId)}?confirm=true`);
      if (!delRes.ok()) throw new Error(`DELETE skill ${skillId} -> ${delRes.status()}`);

      const msgs = await getJson(request, `${base}/api/sessions/${encodeURIComponent(arSessionId)}/messages`);
      const propMsg = (Array.isArray(msgs) ? msgs : []).find((m) => String(m.role || '').toLowerCase() === 'skill_proposal');
      if (!propMsg) throw new Error('Expected skill_proposal message in session');
      const parsed = JSON.parse(propMsg.content);
      if (parsed.adoption_state !== 'pending') {
        throw new Error(`Expected reconciled adoption_state='pending', got '${parsed.adoption_state}'`);
      }

      await page.reload({ waitUntil: 'domcontentloaded' });
      await openSessionByTitle(page, arTitle, { agentId: 'autoreiv' });
      const reloadedCard = page.locator('.skill-proposal-card').last();
      await reloadedCard.waitFor({ state: 'visible', timeout: 15000 });
      const cardText = await reloadedCard.innerText();
      if (cardText.includes('On for autoreiv')) {
        throw new Error(`Reloaded Teach card still shows 'On for autoreiv' after skill deletion: ${cardText}`);
      }
      const adoptAgainVisible = await reloadedCard.locator('.btn-adopt-skill').isVisible();
      if (!adoptAgainVisible) {
        throw new Error('Expected .btn-adopt-skill to be visible again after skill removal');
      }
    }, { timeoutMs: 260000 });
  },
};
