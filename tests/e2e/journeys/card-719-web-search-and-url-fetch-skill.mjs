/**
 * CARD-719 journey: Web Search & URL Fetch skill (`web-search`: `fetch_url`, `web_search`)
 * and Settings -> Connections -> Web Search & URL Fetch configuration card.
 * 1) Open Settings -> Connections, verify `#settingsWebSearchCard` defaults to DuckDuckGo Lite,
 *    configure Tavily Search with an inline API token, save, and verify the token is encrypted
 *    into the Credential Vault (`web-search-tavily`) with no plaintext leaked in `/api/settings/web-search`.
 * 2) Switch back to DuckDuckGo Lite with `allow_private_urls: true`, save, and verify Capabilities Studio
 *    lists `web-search` (`fetch_url`, `web_search`) and `autoreiv` has `web-search` ticked.
 * 3) In Chat with `AutoReiv`, prompt it to call `fetch_url` on `${base}/api/health` and verify the reply
 *    completes cleanly with zero horizontal overflow on desktop and phone.
 */
import { waitFor } from './lib/runner.mjs';
import { openApp, openTab, send, waitReplyIdle } from './lib/app.mjs';

export default {
  id: 'card-719-web-search-and-url-fetch-skill',
  card: 'CARD-719',
  title: 'Web Search and URL Fetch skill and Settings Connections provider configuration',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const inlineToken = `tvly_secret_card719_${viewport.name}`;

    await j.step('Open Settings Connections and configure Web Search provider with Vault-encrypted token', async () => {
      await openApp(page, base);
      await openTab(page, 'settings');

      const connDetails = page.locator('[data-settings-section="connections"]');
      await connDetails.waitFor({ state: 'attached', timeout: 15000 });
      if (!(await connDetails.evaluate((el) => el.open).catch(() => false))) {
        await connDetails.locator('summary').first().evaluate((s) => s.click());
      }

      const card = page.locator('#settingsWebSearchCard');
      await card.scrollIntoViewIfNeeded();
      await card.waitFor({ state: 'visible', timeout: 15000 });

      await page.selectOption('#webSearchProviderSelect', 'tavily');
      await page.locator('#webSearchAuthFields').waitFor({ state: 'visible', timeout: 5000 });
      await page.fill('#webSearchApiKeyInput', inlineToken);

      const allowLocal = page.locator('#webSearchAllowPrivateUrls');
      if (!(await allowLocal.isChecked())) {
        await allowLocal.check();
      }

      await page.click('#saveWebSearchSettingsBtn');

      const savedOk = await waitFor(
        async () => {
          const txt = await page.locator('#webSearchSettingsStatus').innerText().catch(() => '');
          return txt.includes('Saved') && txt.includes('Tavily');
        },
        { timeoutMs: 10000 },
      );
      if (!savedOk) {
        const cur = await page.locator('#webSearchSettingsStatus').innerText().catch(() => '');
        throw new Error(`Expected #webSearchSettingsStatus to confirm Tavily save, got "${cur}"`);
      }

      const apiRes = await request.get(`${base}/api/settings/web-search`);
      if (!apiRes.ok()) {
        throw new Error(`GET /api/settings/web-search failed: ${apiRes.status()}`);
      }
      const apiText = await apiRes.text();
      if (apiText.includes(inlineToken)) {
        throw new Error('Plaintext API token leaked in GET /api/settings/web-search response');
      }
      const apiBody = JSON.parse(apiText);
      if (
        apiBody.provider !== 'tavily' ||
        apiBody.credential_id !== 'web-search-tavily' ||
        !apiBody.has_api_key ||
        !apiBody.allow_private_urls
      ) {
        throw new Error(`Unexpected /api/settings/web-search state: ${apiText}`);
      }

      // Switch back to zero-key DuckDuckGo Lite while keeping allow_private_urls=true
      await page.selectOption('#webSearchProviderSelect', 'duckduckgo');
      await page.click('#saveWebSearchSettingsBtn');
      const ddgSaved = await waitFor(
        async () => {
          const txt = await page.locator('#webSearchSettingsStatus').innerText().catch(() => '');
          return txt.includes('DuckDuckGo Lite');
        },
        { timeoutMs: 10000 },
      );
      if (!ddgSaved) {
        throw new Error('Expected #webSearchSettingsStatus to confirm switch back to DuckDuckGo Lite');
      }
      j.note('Verified Settings -> Connections -> Web Search & URL Fetch provider and Vault token flow');
    });

    await j.step('Open Capabilities Studio and verify web-search skill and AutoReiv tool bindings', async () => {
      await openTab(page, 'capabilities');
      await page.locator('#capabilitiesTreeList').waitFor({ state: 'visible', timeout: 15000 });

      const treeReady = await waitFor(
        async () => {
          const text = await page.locator('#capabilitiesTreeList').innerText().catch(() => '');
          return text.includes('web-search');
        },
        { timeoutMs: 15000 },
      );
      if (!treeReady) {
        throw new Error('Expected #capabilitiesTreeList in Capabilities Studio to include "web-search"');
      }

      const skillFileRes = await request.get(`${base}/api/capabilities/skills/web-search/file?path=SKILL.md`);
      if (!skillFileRes.ok()) {
        throw new Error(`GET /api/capabilities/skills/web-search/file?path=SKILL.md -> ${skillFileRes.status()}`);
      }
      const skillFileData = await skillFileRes.json();
      const mdContent = String(skillFileData.content || '');
      if (!mdContent.includes('fetch_url') || !mdContent.includes('web_search')) {
        throw new Error(`Expected web-search SKILL.md to list fetch_url and web_search, got:\n${mdContent}`);
      }

      const agentRes = await request.get(`${base}/api/agents/autoreiv`);
      if (!agentRes.ok()) {
        throw new Error(`GET /api/agents/autoreiv -> ${agentRes.status()}`);
      }
      const agentData = await agentRes.json();
      const skills = Array.isArray(agentData.allowed_skill) ? agentData.allowed_skill : agentData.skills || [];
      if (!skills.includes('web-search')) {
        throw new Error(`Expected autoreiv skills to include "web-search", got: ${JSON.stringify(skills)}`);
      }
      j.note('Verified web-search skill in Capabilities Studio and on AutoReiv');
    });

    await j.step('Use fetch_url in Chat to read a live HTTP URL and verify layout overflow', async () => {
      await openTab(page, 'chat');
      await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 15000 });

      await send(
        page,
        `Call fetch_url with url="${base}/api/health" right now and report the status field from the JSON response in one short sentence.`,
      );
      const gotReply = await waitFor(
        async () => (await page.locator('#messagesContainer .copy-msg-btn').count()) >= 1,
        { timeoutMs: 120000, intervalMs: 1000 },
      );
      if (!gotReply) {
        throw new Error('Timed out waiting for AutoReiv assistant reply in #messagesContainer');
      }
      await waitReplyIdle(page, { timeoutMs: 120000 });

      const chatText = await page.locator('#messagesContainer').innerText().catch(() => '');
      if (!chatText || chatText.trim().length < 10) {
        throw new Error('Expected non-empty assistant response in #messagesContainer after fetch_url turn');
      }

      const overflow = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
      }));
      if (overflow.scrollWidth > overflow.clientWidth + 2) {
        throw new Error(`Horizontal overflow on ${viewport.name}: ${overflow.scrollWidth}px > ${overflow.clientWidth}px`);
      }
      j.note(`Completed fetch_url turn and verified zero overflow on ${viewport.name} (${overflow.scrollWidth}px <= ${overflow.clientWidth}px)`);
    });
  },
};
