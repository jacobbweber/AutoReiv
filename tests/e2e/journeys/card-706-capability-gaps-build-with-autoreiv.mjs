/**
 * CARD-706 journey: Capability gap rows render Build with AutoReiv (plus Dismiss),
 * removing Open in Skill Studio and Ask Developer, and clicking Build with AutoReiv
 * opens a Chat session on AutoReiv pre-prompted with the capability gap details.
 */
import { waitFor } from './lib/runner.mjs';
import { openApp, trackStreams, waitReplyIdle } from './lib/app.mjs';

const GAP = {
  user_prompt:
    'Do not call register_native_tool yet; reply in 2 short sentences summarizing how you would implement count_words_706.',
  identified_capability: 'count_words_gap_706',
  suggested_tool_name: 'count_words_706',
};

export default {
  id: 'card-706-capability-gaps-build-with-autoreiv',
  card: 'CARD-706',
  title: 'Capability gap rows show Build with AutoReiv and open a pre-prompted AutoReiv Chat session',
  allow: [],
  async run(j, { page, request, base }) {
    const streams = trackStreams(page);

    await j.step('Agents Studio capability gap row renders Build with AutoReiv and Dismiss only', async () => {
      const res = await request.post(`${base}/api/agents/tutor/gaps`, { data: GAP });
      if (!res.ok()) throw new Error(`POST /api/agents/tutor/gaps -> ${res.status()}`);

      await openApp(page, base);
      if (!(await page.locator('#forgeAgentSelect').isVisible().catch(() => false))) {
        await page.locator('#dock-agents').click();
      }
      await page.locator('#forgeAgentSelect').waitFor({ state: 'visible', timeout: 20000 });
      await waitFor(
        async () => (await page.locator('#forgeAgentSelect option[value="tutor"]').count()) > 0,
        { timeoutMs: 20000 }
      );
      await page.selectOption('#forgeAgentSelect', 'tutor');

      const backlogCard = page.locator('#agentTrainingBacklogCard');
      await backlogCard.scrollIntoViewIfNeeded().catch(() => {});
      if (!(await backlogCard.evaluate((el) => el.open).catch(() => true))) {
        await backlogCard.locator('summary').first().click();
      }

      const buildBtn = page.locator('#agentBacklogList .btn-gap-build-autoreiv').first();
      const shown = await waitFor(() => buildBtn.isVisible().catch(() => false), { timeoutMs: 15000 });
      if (!shown) throw new Error('Expected .btn-gap-build-autoreiv to be visible in #agentBacklogList');

      const btnText = (await buildBtn.innerText()).trim();
      if (btnText !== 'Build with AutoReiv') {
        throw new Error(`Expected button text "Build with AutoReiv", got "${btnText}"`);
      }

      const skillStudioBtnCount = await page.locator('#agentBacklogList .btn-gap-open-skill-studio').count();
      if (skillStudioBtnCount !== 0) {
        throw new Error(`Expected 0 .btn-gap-open-skill-studio buttons, found ${skillStudioBtnCount}`);
      }

      const backlogText = await page.locator('#agentBacklogList').innerText();
      if (backlogText.includes('Open in Skill Studio') || backlogText.includes('Ask Developer')) {
        throw new Error(`Stale button label found in #agentBacklogList: ${backlogText}`);
      }

      j.note('Verified capability gap row renders Build with AutoReiv + Dismiss with no Open in Skill Studio or Ask Developer.');
    });

    await j.step('Clicking Build with AutoReiv opens Chat on AutoReiv pre-prompted with the capability gap', async () => {
      const buildBtn = page.locator('#agentBacklogList .btn-gap-build-autoreiv').first();
      await buildBtn.scrollIntoViewIfNeeded().catch(() => {});
      const streamCountBefore = streams.count;
      await buildBtn.click();

      const started = await waitFor(() => streams.count > streamCountBefore, { timeoutMs: 20000 });
      if (!started) throw new Error('Clicking Build with AutoReiv did not start a Chat stream turn');

      await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 15000 });
      const selectedAgent = await page.locator('#agentSelect').inputValue().catch(() => '');
      if (selectedAgent !== 'autoreiv') {
        throw new Error(`Expected Chat #agentSelect to be "autoreiv", got "${selectedAgent}"`);
      }

      const headerTitle = (await page.locator('#activeAgentTitle').innerText().catch(() => '')).trim();
      if (headerTitle !== 'AutoReiv') {
        throw new Error(`Expected #activeAgentTitle to be "AutoReiv", got "${headerTitle}"`);
      }

      const gotReply = await waitFor(
        async () => (await page.locator('#messagesContainer .copy-msg-btn').count()) >= 1,
        { timeoutMs: 120000, intervalMs: 1000 }
      );
      if (!gotReply) {
        throw new Error('Timed out waiting for AutoReiv reply to capability gap prompt');
      }
      await waitReplyIdle(page, { timeoutMs: 120000 });

      const chatText = await page.locator('#messagesContainer').innerText();
      if (!chatText.includes('count_words_706') || !chatText.includes('count_words_gap_706')) {
        throw new Error(`Expected capability gap details in Chat messages, got: ${chatText.slice(0, 400)}`);
      }
      if (!chatText.includes('capability-authoring')) {
        throw new Error(`Expected capability-authoring skill reference in pre-prompt, got: ${chatText.slice(0, 400)}`);
      }

      j.note('Build with AutoReiv opened Chat on AutoReiv, sent the pre-prompted capability gap, and received AutoReiv reply.');
    });
  },
};
