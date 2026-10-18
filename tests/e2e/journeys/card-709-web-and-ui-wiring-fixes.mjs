/**
 * CARD-709 journey: Fix study_entry.js broken #chatInput selector and listener short-circuit,
 * live wiki_service refresh, API key query leak, and active project pill on AutoReiv.
 * 1) Sets an active study topic via PUT /api/education/selected, clicks #chatStudyEntryBtn in Chat,
 *    and verifies #promptInput is populated with [Tutor Education Mode] and the topic on desktop and phone.
 * 2) Creates and selects a project in a throwaway projects_root, switches #agentSelect to 'autoreiv',
 *    and verifies #chatActiveProjectPill is visible in the Chat header with the active project slug.
 * 3) Opens Settings Studio (#view-settings), fills #provKeyInput with a test secret, clicks #discoverModelsBtn,
 *    and verifies the GET /api/models/discover URL does not leak api_key in the query string and instead
 *    sends the X-Provider-Api-Key request header.
 */
import fs from 'node:fs';
import path from 'node:path';
import { clickExpect, waitFor } from './lib/runner.mjs';
import { openApp } from './lib/app.mjs';

const REPO_ROOT = process.cwd();
const QA_PROJECTS_ROOT = path.join(REPO_ROOT, 'scratch', 'live_qa_data', 'qa_projects_709');

export default {
  id: 'card-709-web-and-ui-wiring-fixes',
  card: 'CARD-709',
  title: 'Study entry populates #promptInput, AutoReiv shows active project pill, and model discovery sends API key in header',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const suffix = `${viewport.name}`.replace(/[^a-z0-9]/gi, '').toLowerCase();
    const topic = `Consensus Protocols (${suffix})`;
    const projSlug = `qa-proj-709-${suffix}`;

    try {
      await j.step('Trigger Study entry from Chat header and verify #promptInput receives the study prompt', async () => {
        const selRes = await request.put(`${base}/api/education/selected`, {
          data: {
            topic,
            course_id: `course_709_${suffix}`,
            agent_id: 'tutor',
          },
        });
        if (!selRes.ok()) {
          throw new Error(`PUT /api/education/selected -> ${selRes.status()}`);
        }

        await openApp(page, base);
        if (!(await page.locator('#promptInput').isVisible().catch(() => false))) {
          await page.locator('#dock-chat').click();
        }
        await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 15000 });

        await clickExpect(
          page.locator('#chatStudyEntryBtn'),
          async () => {
            const val = await page.locator('#promptInput').inputValue().catch(() => '');
            return val.includes('[Tutor Education Mode]') && val.includes(topic);
          },
          { label: 'Click #chatStudyEntryBtn and populate #promptInput', timeoutMs: 15000 },
        );

        const stripVisible = await page.locator('#chatEducationModeStrip').isVisible().catch(() => false);
        if (!stripVisible) {
          throw new Error('Expected #chatEducationModeStrip to be visible after entering Study mode');
        }
        j.note(`verified #promptInput prefilled with Study prompt for topic="${topic}"`);
      });

      await j.step('Select an active project and verify #chatActiveProjectPill appears for AutoReiv in Chat', async () => {
        const projPath = path.join(QA_PROJECTS_ROOT, projSlug);
        fs.mkdirSync(projPath, { recursive: true });
        const rootRes = await request.put(`${base}/api/settings/projects_root`, {
          data: { path: QA_PROJECTS_ROOT },
        });
        if (!rootRes.ok()) {
          throw new Error(`PUT /api/settings/projects_root -> ${rootRes.status()}`);
        }

        const pickRes = await request.put(`${base}/api/projects/selected`, {
          data: { slug: projSlug, path: projPath },
        });
        if (!pickRes.ok()) {
          throw new Error(`PUT /api/projects/selected -> ${pickRes.status()}`);
        }

        await page.selectOption('#agentSelect', 'autoreiv');
        await waitFor(
          async () => {
            const visible = await page.locator('#chatActiveProjectPill').isVisible().catch(() => false);
            const text = await page.locator('#chatActiveProjectName').innerText().catch(() => '');
            return visible && text.includes(projSlug);
          },
          { timeoutMs: 15000, label: '#chatActiveProjectPill visible for autoreiv' },
        );
        j.note(`verified #chatActiveProjectPill visible for autoreiv (${projSlug})`);
      });

      await j.step('Verify Settings Studio model discovery sends API key via X-Provider-Api-Key header, not URL query', async () => {
        const discoverRequests = [];
        page.on('request', (req) => {
          if (req.url().includes('/api/models/discover')) {
            discoverRequests.push({
              url: req.url(),
              headers: req.headers(),
            });
          }
        });

        await page.evaluate(() => {
          if (typeof window.__autoreivSwitchTab === 'function') {
            window.__autoreivSwitchTab('settings');
          }
        });
        await page.locator('#view-settings').waitFor({ state: 'visible', timeout: 15000 });
        await page.evaluate(() => {
          const det = document.querySelector('[data-settings-section="providers"]');
          if (det) det.open = true;
        });
        await page.locator('#provKeyInput').waitFor({ state: 'visible', timeout: 15000 });

        await page.evaluate(() => {
          const sel = document.getElementById('provVaultCredSelect');
          if (sel) {
            sel.value = 'direct';
            sel.dispatchEvent(new Event('change'));
          }
          const inp = document.getElementById('provKeyInput');
          if (inp) {
            inp.disabled = false;
            inp.value = 'sk-card709-no-query-leak';
          }
        });

        const beforeCount = discoverRequests.length;
        await clickExpect(
          page.locator('#discoverModelsBtn'),
          async () => discoverRequests.length > beforeCount,
          { label: 'Click #discoverModelsBtn in Settings Studio', timeoutMs: 15000 },
        );

        const latest = discoverRequests[discoverRequests.length - 1];
        if (latest.url.includes('api_key=')) {
          throw new Error(`Model discovery leaked api_key in URL query string: ${latest.url}`);
        }
        const sentHeader = latest.headers['x-provider-api-key'] || '';
        if (sentHeader !== 'sk-card709-no-query-leak') {
          throw new Error(`Expected X-Provider-Api-Key header 'sk-card709-no-query-leak', got '${sentHeader}'`);
        }

        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
        );
        if (overflow > 2) {
          throw new Error(`Horizontal overflow on ${viewport.name}: ${overflow}px`);
        }
        j.note(`verified /api/models/discover header transport and zero overflow on ${viewport.name}`);
      });
    } finally {
      await request.delete(`${base}/api/projects/${encodeURIComponent(projSlug)}?confirm=true`).catch(() => {});
    }
  },
};
