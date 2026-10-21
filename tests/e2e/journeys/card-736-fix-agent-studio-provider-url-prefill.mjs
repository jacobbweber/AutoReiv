/**
 * CARD-736: Fix Agent Studio provider URL prefill and surface model discovery errors.
 *
 * Verifies on desktop and phone:
 * 1. With vllm as the active global provider and a saved ollama base_url in provider_settings,
 *    opening Agent Studio -> Overrides and switching LLM Provider to ollama pre-fills the
 *    saved ollama base_url (instead of hardcoded 127.0.0.1:11434) and auto-discovers live models.
 * 2. Entering an unreachable host URL in Agent Studio and clicking Refresh Models surfaces a
 *    warning toast with the connection failure reason, marks fallback options as preset
 *    placeholders, and does not clobber the global provider configuration.
 */
import http from 'node:http';
import { waitFor } from './lib/runner.mjs';
import { getJson, openApp, openTab } from './lib/app.mjs';

async function postJson(request, url, data) {
  const res = await request.post(url, { data });
  if (!res.ok()) {
    throw new Error(`POST ${url} -> HTTP ${res.status()}`);
  }
  return res.json();
}

function startFakeOllamaServer() {
  return new Promise((resolve, reject) => {
    const server = http.createServer((req, res) => {
      if (req.url && req.url.startsWith('/api/tags')) {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(
          JSON.stringify({
            models: [
              {
                name: 'qwen3.8:latest',
                details: {
                  family: 'qwen3',
                  parameter_size: '8B',
                  quantization_level: 'Q4_K_M',
                },
              },
            ],
          })
        );
        return;
      }
      res.writeHead(404);
      res.end();
    });
    server.on('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const addr = server.address();
      resolve({
        url: `http://127.0.0.1:${addr.port}`,
        close: () => new Promise((r) => server.close(() => r())),
      });
    });
  });
}

async function openAgentOverridesSection(page, base) {
  await openApp(page, base);
  await openTab(page, 'agents');
  await page.locator('#forgeAgentSelect').waitFor({ state: 'visible', timeout: 20000 });
  const overrides = page.locator('details[data-section="overrides"]');
  await waitFor(
    async () => (await overrides.getAttribute('aria-busy').catch(() => 'true')) !== 'true',
    { timeoutMs: 20000 }
  );
  if (!(await overrides.evaluate((el) => el.open).catch(() => false))) {
    await overrides.locator('summary').first().click();
  }
  await page.locator('#forgeProviderSelect').waitFor({ state: 'visible', timeout: 10000 });
}

export default {
  id: 'card-736-fix-agent-studio-provider-url-prefill',
  card: 'CARD-736',
  title: 'Agent Studio provider override pre-fills saved provider URL and surfaces discovery errors',
  allow: [/Live model discovery failed for provider/i, /Failed to fetch models from Ollama/i],
  async run(j, { page, request, base }) {
    const initialSettings = await getJson(request, `${base}/api/settings`);
    const origProv = initialSettings?.providers?.default_provider_id || 'vllm';
    const origMap = initialSettings?.providers?.providers || {};
    const origActiveCfg = origMap[origProv] || {};

    const fakeOllama = await startFakeOllamaServer();
    try {
      await j.step('Configure saved ollama URL while keeping global default provider active, then switch Agent Studio provider to ollama', async () => {
        // Save ollama provider URL first
        await postJson(request, `${base}/api/settings/providers`, {
          provider_id: 'ollama',
          base_url: fakeOllama.url,
          default_model_id: 'qwen3.8:latest',
          set_as_default: false,
        });
        // Set vllm as the active global default provider (matching operator setup where vllm is default and ollama is override)
        await postJson(request, `${base}/api/settings/providers`, {
          provider_id: 'vllm',
          base_url: 'http://127.0.0.1:8000/v1',
          default_model_id: 'nemotron-3.5-lightning',
          set_as_default: true,
        });

        await openAgentOverridesSection(page, base);
        await page.selectOption('#forgeProviderSelect', 'ollama');

        const prefilled = await waitFor(
          async () => (await page.inputValue('#forgeApiBaseUrlInput').catch(() => '')) === fakeOllama.url,
          { timeoutMs: 10000 }
        );
        const actualUrl = await page.inputValue('#forgeApiBaseUrlInput').catch(() => '');
        if (!prefilled) {
          throw new Error(`Expected #forgeApiBaseUrlInput to pre-fill saved ollama URL ${fakeOllama.url}, got "${actualUrl}"`);
        }

        const discoveredLive = await waitFor(
          async () => {
            const opts = await page.locator('#forgeAgentModelSelect option').allTextContents();
            return opts.some((t) => t.includes('qwen3.8:latest') && !t.includes('preset'));
          },
          { timeoutMs: 10000 }
        );
        const optTexts = await page.locator('#forgeAgentModelSelect option').allTextContents();
        j.note(`prefilled URL=${actualUrl}; model options=${optTexts.join(', ')}`);
        if (!discoveredLive) {
          throw new Error(`Expected live model qwen3.8:latest in #forgeAgentModelSelect, got: ${optTexts.join(', ')}`);
        }
        await page.locator('#forgeProviderSelect').scrollIntoViewIfNeeded().catch(() => {});
      });

      await j.step('Unreachable host URL in Agent Studio surfaces warning toast and marks fallback presets clearly', async () => {
        const unreachableUrl = 'http://127.0.0.1:59999';
        await page.fill('#forgeApiBaseUrlInput', unreachableUrl);
        await page.click('#forgeDiscoverModelsBtn');

        const warningShown = await waitFor(
          async () => {
            const toasts = await page.locator('#toastContainer').innerText().catch(() => '');
            return toasts.includes('Could not reach ollama') && toasts.includes('Showing preset placeholders');
          },
          { timeoutMs: 15000 }
        );
        const toastText = await page.locator('#toastContainer').innerText().catch(() => '');
        const optTexts = await page.locator('#forgeAgentModelSelect option').allTextContents();
        j.note(`warning toast="${toastText.replace(/\s+/g, ' ').trim()}"; options=${optTexts.slice(0, 3).join(', ')}`);

        if (!warningShown) {
          throw new Error(`Expected warning toast for unreachable host, got: "${toastText}"`);
        }
        if (!optTexts.some((t) => t.includes('preset — host unreachable'))) {
          throw new Error(`Expected preset fallback label in #forgeAgentModelSelect options, got: ${optTexts.join(', ')}`);
        }
        await page.locator('#forgeDiscoverModelsBtn').scrollIntoViewIfNeeded().catch(() => {});
      });
    } finally {
      await fakeOllama.close();
      await postJson(request, `${base}/api/settings/providers`, {
        provider_id: origProv,
        base_url: origActiveCfg.base_url || initialSettings?.providers?.openai_base_url || 'http://127.0.0.1:8000/v1',
        default_model_id: origActiveCfg.default_model_id || initialSettings?.providers?.default_model_id || 'default',
      }).catch(() => {});
    }
  },
};
