/**
 * CARD-703 journey: Local inference port auto-probing in Models / Settings Studio.
 * 1) Opens Settings Studio (#dock-settings -> #view-settings) and verifies #settingsLocalProbeCard
 *    and #scanLocalServersBtn render.
 * 2) Clicks "Scan Local Servers" (#scanLocalServersBtn) and verifies POST /api/models/probe-local
 *    discovers active inference endpoints (/v1/models on 8006 and/or 11434), excludes non-model
 *    HTTP servers (like port 8000 web server), and renders selectable model cards.
 * 3) Clicks "Use Model" on a discovered card and verifies the provider and active default model
 *    are activated in the UI and persisted in /api/settings with zero horizontal overflow on desktop and phone.
 */
import { clickExpect, waitFor } from './lib/runner.mjs';
import { getJson, openApp, openTab } from './lib/app.mjs';

export default {
  id: 'card-703-local-inference-port-auto-probing',
  card: 'CARD-703',
  title: 'Settings Studio Scan Local Servers discovers /v1/models endpoints and activates a local model in one click',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    await j.step('Open Settings Studio and verify Local Inference Auto-Probe card is visible', async () => {
      await openApp(page, base);
      await openTab(page, 'settings');
      await page.locator('#settingsLocalProbeCard').waitFor({ state: 'visible', timeout: 15000 });
      await page.locator('#scanLocalServersBtn').waitFor({ state: 'visible', timeout: 10000 });
      j.note(`Local Inference Auto-Probe card visible on ${viewport.name}`);
    });

    await j.step('Click Scan Local Servers and verify discovered model cards and non-model port exclusion', async () => {
      const scanBtn = page.locator('#scanLocalServersBtn');
      await clickExpect(
        scanBtn,
        async () => {
          const count = await page.locator('[data-testid="local-model-card"]').count();
          return count > 0;
        },
        { what: 'scan local inference servers', label: '#scanLocalServersBtn', timeoutMs: 15000 },
      );

      const statusText = (await page.locator('#localModelProbeStatus').innerText()).trim();
      if (!/Discovered \d+ model\(s\) across \d+ local server\(s\)/i.test(statusText)) {
        throw new Error(`Unexpected #localModelProbeStatus after scan: "${statusText}"`);
      }

      // Verify API contract directly including negative assertion (port 8000 web server is not a /v1/models server)
      const probeRes = await request.post(`${base}/api/models/probe-local`, {
        data: {},
      });
      if (!probeRes.ok()) throw new Error(`POST /api/models/probe-local -> ${probeRes.status()}`);
      const probeData = await probeRes.json();
      if (!(probeData.total_servers >= 1) || !(probeData.total_models >= 1)) {
        throw new Error(`Expected >= 1 discovered server/model, got: ${JSON.stringify(probeData)}`);
      }
      if (
        (probeData.servers || []).some(
          (s) => s.host === '127.0.0.1' && Number(s.port) === 8000,
        )
      ) {
        throw new Error('Negative assertion failed: port 8000 web server should not be reported as a /v1/models server');
      }

      const cardCount = await page.locator('[data-testid="local-model-card"]').count();
      j.note(`rendered ${cardCount} discovered local model card(s): ${statusText}`);
    });

    await j.step('Click Use Model on a discovered card and verify provider + default model activation', async () => {
      // Prefer qwen3.8:latest if present so QA environment keeps its primary model, else first card
      let targetCard = page.locator('[data-testid="local-model-card"][data-model-id="qwen3.8:latest"]').first();
      if ((await targetCard.count()) === 0) {
        targetCard = page.locator('[data-testid="local-model-card"]').first();
      }
      const targetModel = await targetCard.getAttribute('data-model-id');
      const targetProvider = await targetCard.getAttribute('data-provider-id');
      const useBtn = targetCard.locator('[data-use-local-model]');

      await clickExpect(
        useBtn,
        async () => {
          const txt = ((await useBtn.innerText().catch(() => '')) || '').trim();
          return txt === 'Active';
        },
        { what: `activate discovered model ${targetModel}`, label: '[data-use-local-model]', timeoutMs: 15000 },
      );

      const activatedStatus = await waitFor(
        async () => {
          const t = (await page.locator('#localModelProbeStatus').innerText().catch(() => '')).trim();
          return t.includes(`Activated ${targetModel}`) ? t : null;
        },
        { timeoutMs: 10000, intervalMs: 250 },
      );
      if (!activatedStatus) {
        throw new Error(`Expected #localModelProbeStatus to confirm activation of ${targetModel}`);
      }

      const settings = await getJson(request, `${base}/api/settings`);
      if (!settings?.matrix || settings.matrix.default_model !== targetModel) {
        throw new Error(
          `Expected /api/settings matrix.default_model === "${targetModel}", got "${settings?.matrix?.default_model}"`,
        );
      }
      if (settings?.providers?.default_provider_id !== targetProvider) {
        throw new Error(
          `Expected /api/settings providers.default_provider_id === "${targetProvider}", got "${settings?.providers?.default_provider_id}"`,
        );
      }

      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      if (overflow > 2) {
        throw new Error(`Horizontal overflow on ${viewport.name}: ${overflow}px`);
      }
      j.note(`activated ${targetModel} (${targetProvider}) on ${viewport.name} with 0px overflow`);
    });
  },
};
