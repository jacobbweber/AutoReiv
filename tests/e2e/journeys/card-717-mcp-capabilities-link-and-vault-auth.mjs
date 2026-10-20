/**
 * CARD-717 journey: MCP Capabilities Studio link & Vault Credential authentication.
 * 1) Open Settings -> Connections and verify `#settingsOpenToolsStudioBtn` reads "Open in Capabilities Studio".
 * 2) Create a Bearer token credential in Credential Vault (`mcp-bearer-test-token`).
 * 3) Click `#settingsOpenToolsStudioBtn` ("Open in Capabilities Studio") and verify it opens `#view-capabilities` on `mcp/ (MCP Servers)`.
 * 4) Add an HTTP/SSE MCP server referencing `mcp-bearer-test-token` with `bearer` auth, verify the row displays `[data-testid="mcp-vault-auth-badge"]`, and verify `/api/settings/mcp` stores `credential_id` without leaking the secret.
 * 5) Verify zero horizontal overflow on desktop and phone.
 */
import { waitFor } from './lib/runner.mjs';
import { openApp, openTab } from './lib/app.mjs';

export default {
  id: 'card-717-mcp-capabilities-link-and-vault-auth',
  card: 'CARD-717',
  title: 'Settings Open in Capabilities Studio link and MCP Vault Credential authentication',
  allow: [],
  async run(j, { page, base, viewport }) {
    const credId = `mcp-bearer-${viewport.name}`;
    const serverName = `http-bearer-${viewport.name}`;
    const secretVal = 'tok_live_secret_card717_xyz';

    await j.step('Open Settings Connections, verify Open in Capabilities Studio button label, and add a Vault credential', async () => {
      await openApp(page, base);
      await openTab(page, 'settings');

      const connDetails = page.locator('[data-settings-section="connections"]');
      await connDetails.waitFor({ state: 'attached', timeout: 15000 });
      if (!(await connDetails.evaluate((el) => el.open).catch(() => false))) {
        await connDetails.locator('summary').first().evaluate((s) => s.click());
      }

      const openMcpBtn = page.locator('#settingsOpenToolsStudioBtn');
      await openMcpBtn.waitFor({ state: 'visible', timeout: 15000 });
      const btnText = (await openMcpBtn.innerText()).trim();
      if (btnText !== 'Open in Capabilities Studio') {
        throw new Error(`Expected #settingsOpenToolsStudioBtn text to be "Open in Capabilities Studio", got "${btnText}"`);
      }

      const addCredBtn = page.locator('#addCredentialBtn');
      await addCredBtn.scrollIntoViewIfNeeded();
      await addCredBtn.click();

      await page.locator('#credentialFormContainer').waitFor({ state: 'visible', timeout: 10000 });
      await page.fill('#credNameInput', 'MCP Bearer Test Token');
      await page.fill('#credIdInput', credId);
      await page.selectOption('#credTypeSelect', 'token');
      await page.fill('#credSecretInput', secretVal);
      await page.click('#saveCredentialBtn');

      const savedInTable = await waitFor(
        async () => {
          const txt = await page.locator('#credentialsTableBody').innerText().catch(() => '');
          return txt.includes(credId);
        },
        { timeoutMs: 15000 },
      );
      if (!savedInTable) {
        throw new Error(`Expected #credentialsTableBody to list newly saved credential "${credId}"`);
      }
      j.note(`Verified "Open in Capabilities Studio" label and saved Vault credential "${credId}"`);
    });

    await j.step('Click Open in Capabilities Studio and add an HTTP MCP server referencing the Vault Bearer credential', async () => {
      const openMcpBtn = page.locator('#settingsOpenToolsStudioBtn');
      await openMcpBtn.scrollIntoViewIfNeeded();
      await openMcpBtn.click();

      await page.locator('#view-capabilities').waitFor({ state: 'visible', timeout: 20000 });
      await page.locator('#capabilitiesMcpPane').waitFor({ state: 'visible', timeout: 15000 });

      const addMcpBtn = page.locator('#capabilitiesMcpAddBtn');
      await addMcpBtn.click();
      await page.locator('#capabilitiesMcpForm').waitFor({ state: 'visible', timeout: 10000 });

      const credOptionReady = await waitFor(
        async () => (await page.locator(`#capabilitiesMcpCredentialSelect option[value="${credId}"]`).count()) > 0,
        { timeoutMs: 10000 },
      );
      if (!credOptionReady) {
        throw new Error(`Expected #capabilitiesMcpCredentialSelect to include Vault credential "${credId}"`);
      }

      await page.fill('#capabilitiesMcpNameInput', serverName);
      await page.selectOption('#capabilitiesMcpTransportSelect', 'sse');
      await page.locator('#capabilitiesMcpUrlInput').waitFor({ state: 'visible', timeout: 5000 });
      await page.fill('#capabilitiesMcpUrlInput', 'http://127.0.0.1:19876/sse');
      await page.selectOption('#capabilitiesMcpCredentialSelect', credId);
      await page.selectOption('#capabilitiesMcpAuthTypeSelect', 'bearer');
      // Uncheck enabled so we don't wait on a dead port timeout during save, or keep enabled=false for clean config check
      const enabledBox = page.locator('#capabilitiesMcpEnabledCheckbox');
      if (await enabledBox.isChecked()) {
        await enabledBox.uncheck();
      }
      await page.click('#capabilitiesMcpSaveBtn');

      const rowVisible = await waitFor(
        async () => {
          const row = page.locator(`#capabilitiesMcpList [data-server-name="${serverName}"]`);
          if ((await row.count()) === 0) return false;
          const badgeTxt = await row.locator('[data-testid="mcp-vault-auth-badge"]').innerText().catch(() => '');
          return badgeTxt.includes('bearer') && badgeTxt.includes('MCP Bearer Test Token');
        },
        { timeoutMs: 15000 },
      );
      if (!rowVisible) {
        throw new Error(`Expected MCP server row "${serverName}" with Vault auth badge in #capabilitiesMcpList`);
      }

      const apiCheck = await page.evaluate(async (expectedServer) => {
        const res = await fetch('/api/settings/mcp');
        const list = await res.json();
        const rawText = JSON.stringify(list);
        const found = list.find((s) => s && s.name === expectedServer);
        return { found, rawText };
      }, serverName);

      if (!apiCheck.found || apiCheck.found.credential_id !== credId || apiCheck.found.auth_type !== 'bearer') {
        throw new Error(`Expected /api/settings/mcp to return credential_id="${credId}" and auth_type="bearer", got: ${JSON.stringify(apiCheck.found)}`);
      }
      if (apiCheck.rawText.includes(secretVal)) {
        throw new Error('Expected /api/settings/mcp response not to leak plaintext secret');
      }

      const overflow = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
      }));
      if (overflow.scrollWidth > overflow.innerWidth + 2) {
        throw new Error(`Horizontal overflow on ${viewport.name}: scrollWidth=${overflow.scrollWidth} > innerWidth=${overflow.innerWidth}`);
      }

      // Cleanup test server and credential
      await page.evaluate(
        async ({ sName, cId }) => {
          await fetch(`/api/settings/mcp/${encodeURIComponent(sName)}`, { method: 'DELETE' });
          await fetch(`/api/vault/credentials/${encodeURIComponent(cId)}`, { method: 'DELETE' });
        },
        { sName: serverName, cId: credId },
      );

      j.note(`Added MCP server "${serverName}" with Vault Bearer credential "${credId}" on ${viewport.name} (${overflow.scrollWidth}px <= ${overflow.innerWidth}px)`);
    });
  },
};
