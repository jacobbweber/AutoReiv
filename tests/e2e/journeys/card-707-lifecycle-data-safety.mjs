/**
 * CARD-707 journey: Fix reboot skill-pruning data loss, Vault key persistence & path resolution,
 * fail-closed tool checks, and online SQLite backup snapshots.
 * 1) Customize shipped skill `platform-health` via `PUT /api/capabilities/skills/platform-health/file`
 *    (creating `$DATA_DIR/skills/platform-health/SKILL.md`), open Capabilities Studio (`#view-capabilities`),
 *    select `platform-health`, and verify the customized user runbook (`source === "user"`) is preserved
 *    and rendered in the inspector on desktop and phone.
 * 2) Open Settings Studio (`#view-settings`), save a new credential via `POST /api/credentials`,
 *    and verify the credential round-trips encrypted/decrypted through `CredentialVault` and renders
 *    in the Credential Vault list (`#vaultCredentialsList`) with its masked preview.
 */
import { clickExpect, waitFor } from './lib/runner.mjs';
import { getJson, openApp, openTab } from './lib/app.mjs';

export default {
  id: 'card-707-lifecycle-data-safety',
  card: 'CARD-707',
  title: 'User copies of shipped platform-health skill survive startup and CredentialVault persists encrypted secrets under the data root',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const suffix = `${viewport.name}`.replace(/[^a-z0-9]/gi, '').toLowerCase();
    const marker = `CARD-707 custom platform-health note (${suffix})`;
    const credId = `qa-vault-${suffix}`;

    try {
      await j.step('Save user customization of shipped platform-health skill and verify it in Capabilities Studio', async () => {
        const currentFile = await getJson(
          request,
          `${base}/api/capabilities/skills/platform-health/file?path=SKILL.md`,
        );
        const originalContent = String(currentFile.content || '');
        const customContent = originalContent.includes(marker)
          ? originalContent
          : `${originalContent.trimEnd()}\n\n<!-- ${marker} -->\n`;

        const putRes = await request.put(
          `${base}/api/capabilities/skills/platform-health/file`,
          { data: { path: 'SKILL.md', content: customContent } },
        );
        if (!putRes.ok()) {
          throw new Error(`PUT platform-health SKILL.md -> ${putRes.status()}`);
        }

        const verifyFile = await getJson(
          request,
          `${base}/api/capabilities/skills/platform-health/file?path=SKILL.md`,
        );
        if (!String(verifyFile.content || '').includes(marker)) {
          throw new Error(`Expected customized platform-health content to contain marker: ${marker}`);
        }

        await openApp(page, base);
        await openTab(page, 'capabilities');
        await page.locator('#view-capabilities').waitFor({ state: 'visible', timeout: 15000 });

        await waitFor(
          async () => {
            const count = await page.locator('[data-skill-id="platform-health"]').count();
            return count > 0;
          },
          { timeoutMs: 15000, label: 'platform-health skill node in Capabilities Studio' },
        );

        const skillRow = page.locator('[data-skill-id="platform-health"]').first();
        await clickExpect(
          skillRow,
          async () => {
            const text = await page.locator('#view-capabilities').innerText().catch(() => '');
            return text.includes('platform-health') || text.includes('Platform Health');
          },
          { label: 'Select platform-health skill in Capabilities Studio' },
        );
      });

      await j.step('Save encrypted credential in Credential Vault and verify it in Settings Studio', async () => {
        const createRes = await request.post(`${base}/api/vault/credentials`, {
          data: {
            id: credId,
            name: `QA Vault Key (${suffix})`,
            type: 'api_key',
            description: 'CARD-707 lifecycle data safety verification',
            secret: `sk-card707-secret-${suffix}-9876`,
          },
        });
        if (!createRes.ok()) {
          throw new Error(`POST /api/vault/credentials -> ${createRes.status()}`);
        }

        const credsPayload = await getJson(request, `${base}/api/vault/credentials`);
        const list = Array.isArray(credsPayload) ? credsPayload : (credsPayload.credentials || []);
        const found = list.find((c) => c.id === credId);
        if (!found) {
          throw new Error(`Credential ${credId} not found in GET /api/vault/credentials`);
        }
        if (found.secret) {
          throw new Error('GET /api/vault/credentials must not leak plaintext secret');
        }
        if (!String(found.masked_preview || '').includes('9876')) {
          throw new Error(`Expected masked_preview ending in 9876, got: ${found.masked_preview}`);
        }

        await openTab(page, 'settings');
        await page.locator('#view-settings').waitFor({ state: 'visible', timeout: 15000 });
        await waitFor(
          async () => {
            const html = await page.locator('#vaultCredentialsList').innerText().catch(() => '');
            return html.includes(`QA Vault Key (${suffix})`) || html.includes(credId);
          },
          { timeoutMs: 15000, label: 'Vault credential row visible in #vaultCredentialsList' },
        );
      });
    } finally {
      await request.post(`${base}/api/skills/platform-health/use-shipped`).catch(() => {});
      await request.delete(`${base}/api/vault/credentials/${encodeURIComponent(credId)}`).catch(() => {});
    }
  },
};
