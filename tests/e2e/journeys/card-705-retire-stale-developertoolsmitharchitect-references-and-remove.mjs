/**
 * CARD-705 journey: Retire stale Developer/Toolsmith/Architect references and remove Chat header role pill.
 * 1) Open Chat (#view-chat) and verify #activeAgentTone ('Autonomous Multi-Agent Orchestrator' / 'Engine: AutoReiv')
 *    is completely absent from the DOM while #agentSelect remains functional.
 * 2) Verify GET /api/agents/autoreiv includes capability-authoring, project-cards, software-development, and user:*
 *    and its system_prompt contains no stale Developer/Toolsmith routing instructions.
 * 3) Send a Chat turn on AutoReiv that runs a platform health check and mentions an unavailable raw shell command,
 *    and verify AutoReiv replies without appending 'You can use Ask Developer to add this.' or rendering any
 *    .msg-ask-developer-btn button.
 */
import { waitFor } from './lib/runner.mjs';
import { getJson, openApp, send, waitReplyIdle } from './lib/app.mjs';

const AGENT_ID = 'autoreiv';

export default {
  id: 'card-705-retire-stale-developertoolsmitharchitect-references-and-remove',
  card: 'CARD-705',
  title: 'Retire stale Developer/Toolsmith/Architect references and remove Chat header role pill',
  allow: [],
  async run(j, { page, request, base }) {
    await j.step('Verify Chat header has no #activeAgentTone static pill and AutoReiv profile is clean', async () => {
      await openApp(page, base);
      if (!(await page.locator('#promptInput').isVisible().catch(() => false))) {
        await page.locator('#dock-chat').click();
      }
      await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 15000 });

      const toneCount = await page.locator('#activeAgentTone').count();
      if (toneCount !== 0) {
        throw new Error(`Expected #activeAgentTone to be removed from DOM, found ${toneCount}`);
      }

      const headerText = await page.locator('#view-chat').innerText();
      if (headerText.includes('Autonomous Multi-Agent Orchestrator') || headerText.includes('Engine: AutoReiv')) {
        throw new Error(`Unexpected static role pill text in #view-chat: ${headerText.slice(0, 200)}`);
      }

      const autoreiv = await getJson(request, `${base}/api/agents/${AGENT_ID}`);
      const skills = Array.isArray(autoreiv.allowed_skill) ? autoreiv.allowed_skill : [];
      for (const reqSkill of ['capability-authoring', 'project-cards', 'software-development', 'user:*']) {
        if (!skills.includes(reqSkill)) {
          throw new Error(`Expected ${reqSkill} in AutoReiv allowed_skill, got: ${JSON.stringify(skills)}`);
        }
      }
      const sysPrompt = String(autoreiv.system_prompt || '');
      if (sysPrompt.includes('Developer/Toolsmith') || sysPrompt.includes('open Developer in Chat')) {
        throw new Error(`Stale retired agent reference in AutoReiv system_prompt: ${sysPrompt.slice(0, 300)}`);
      }

      j.note('Chat header verified without #activeAgentTone pill; AutoReiv profile has consolidated skills and clean prompt.');
    });

    await j.step('Verify AutoReiv health check reply never appends Ask Developer line or button', async () => {
      if ((await page.locator('#agentSelect').inputValue()) !== AGENT_ID) {
        await page.selectOption('#agentSelect', AGENT_ID);
        await page.waitForTimeout(500);
      }
      await send(
        page,
        'Call inspect_system_health now and reply in 2 short sentences with the health status, noting that raw shell commands are not used during health checks.'
      );
      const gotReply = await waitFor(
        async () => (await page.locator('#messagesContainer .copy-msg-btn').count()) >= 1,
        { timeoutMs: 120000, intervalMs: 1000 }
      );
      if (!gotReply) {
        throw new Error('Timed out waiting for AutoReiv assistant reply bubble');
      }
      await waitReplyIdle(page, { timeoutMs: 120000 });

      const chatText = await page.locator('#messagesContainer').innerText();
      if (chatText.includes('You can use Ask Developer to add this.')) {
        throw new Error(`AutoReiv reply unexpectedly appended Ask Developer line: ${chatText}`);
      }
      if (chatText.includes('Developer in Chat')) {
        throw new Error(`AutoReiv reply unexpectedly referenced retired Developer in Chat: ${chatText}`);
      }

      const askDevBtnCount = await page.locator('.msg-ask-developer-btn').count();
      if (askDevBtnCount !== 0) {
        throw new Error(`Expected 0 .msg-ask-developer-btn buttons on AutoReiv reply, found ${askDevBtnCount}`);
      }

      j.note('AutoReiv reply verified clean with zero Ask Developer buttons or stale Developer references.');
    });
  },
};
