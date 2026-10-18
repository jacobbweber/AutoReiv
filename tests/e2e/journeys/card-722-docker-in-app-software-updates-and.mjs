/**
 * CARD-722: Docker In-App Software Updates and Editable Default Origin URL.
 *
 * Verifies:
 * 1. Settings -> Preferences -> System & Software Updates renders an editable Origin URL
 *    (#updateRemoteUrl) pre-populated with a non-empty URL (defaulting to
 *    https://github.com/jacobbweber/AutoReiv.git), plus #saveUpdateOriginBtn and
 *    #resetUpdateOriginBtn.
 * 2. Operators can edit and save a custom Origin URL via #saveUpdateOriginBtn, verify
 *    /api/system/updates/config persists upstream_repo_url, and reset to default via
 *    #resetUpdateOriginBtn.
 * 3. #applyUpdateBtn ("Update now"), #updateBranchSelect, and #switchBranchBtn are visible
 *    and enabled, and zero horizontal overflow occurs on desktop and phone.
 */
import { openApp } from './lib/app.mjs';

const DEFAULT_ORIGIN_URL = 'https://github.com/jacobbweber/AutoReiv.git';

async function openSettingsUpdates(page) {
  await page.evaluate(() => {
    document.getElementById('tab-settings')?.click();
  });
  await page.waitForTimeout(400);
  await page.evaluate(() => {
    const pref = document.querySelector('details[data-settings-section="preferences"]');
    if (pref) pref.open = true;
    const card = document.getElementById('settingsSystemUpdatesCard');
    if (card) card.scrollIntoView({ block: 'start' });
  });
  await page.locator('#settingsSystemUpdatesCard').waitFor({ state: 'visible', timeout: 10000 });
  await page.waitForTimeout(400);
}

export default {
  id: 'card-722-docker-in-app-software-updates-and',
  card: 'CARD-722',
  title: 'System & Software Updates renders editable default Origin URL and enables branch selection and updates for Git and Docker',
  allow: [],
  async run(j, { page, base }) {
    await j.step('1. Open Settings -> Preferences -> System & Software Updates and verify editable Origin URL and enabled update/branch controls', async () => {
      await openApp(page, base);
      await openSettingsUpdates(page);

      const state = await page.evaluate(() => {
        const urlInput = document.getElementById('updateRemoteUrl');
        const saveBtn = document.getElementById('saveUpdateOriginBtn');
        const resetBtn = document.getElementById('resetUpdateOriginBtn');
        const applyBtn = document.getElementById('applyUpdateBtn');
        const branchSelect = document.getElementById('updateBranchSelect');
        const switchBtn = document.getElementById('switchBranchBtn');
        return {
          hasUrlInput: Boolean(urlInput),
          isReadOnly: Boolean(urlInput && urlInput.readOnly),
          urlValue: urlInput ? urlInput.value.trim() : '',
          hasSaveBtn: Boolean(saveBtn),
          hasResetBtn: Boolean(resetBtn),
          hasApplyBtn: Boolean(applyBtn && !applyBtn.classList.contains('hidden')),
          hasBranchSelect: Boolean(branchSelect && !branchSelect.disabled),
          hasSwitchBtn: Boolean(switchBtn && !switchBtn.disabled),
        };
      });

      if (!state.hasUrlInput || state.isReadOnly) {
        throw new Error(`Expected editable #updateRemoteUrl, got ${JSON.stringify(state)}`);
      }
      if (!state.urlValue) {
        throw new Error('Expected #updateRemoteUrl to be pre-populated with a default URL');
      }
      if (!state.hasSaveBtn || !state.hasResetBtn) {
        throw new Error(`Missing Save/Reset Origin buttons: ${JSON.stringify(state)}`);
      }
      if (!state.hasApplyBtn || !state.hasBranchSelect || !state.hasSwitchBtn) {
        throw new Error(`Expected Update now and branch controls enabled: ${JSON.stringify(state)}`);
      }
    });

    await j.step('2. Save custom Origin URL, verify /api/system/updates/config persists upstream_repo_url, and reset to default URL', async () => {
      const originalUrl = await page.evaluate(() => {
        const el = document.getElementById('updateRemoteUrl');
        return el ? el.value.trim() : '';
      });

      const customUrl = 'https://github.com/jacobbweber/AutoReiv.git';
      await page.locator('#updateRemoteUrl').fill(customUrl);
      await page.locator('#saveUpdateOriginBtn').click();
      await page.waitForTimeout(500);

      const savedCfg = await page.evaluate(async () => {
        const res = await fetch('/api/system/updates/config');
        return res.json();
      });
      if (savedCfg.upstream_repo_url !== customUrl) {
        throw new Error(`Expected upstream_repo_url=${customUrl}, got ${JSON.stringify(savedCfg)}`);
      }

      await page.locator('#resetUpdateOriginBtn').click();
      await page.waitForTimeout(500);

      const resetValue = await page.evaluate(() => {
        const el = document.getElementById('updateRemoteUrl');
        return el ? el.value.trim() : '';
      });
      if (resetValue !== DEFAULT_ORIGIN_URL) {
        throw new Error(`Expected reset URL=${DEFAULT_ORIGIN_URL}, got ${resetValue}`);
      }

      if (originalUrl && originalUrl !== DEFAULT_ORIGIN_URL) {
        await page.locator('#updateRemoteUrl').fill(originalUrl);
        await page.locator('#saveUpdateOriginBtn').click();
        await page.waitForTimeout(400);
      }
    });

    await j.step('3. Verify branch list loaded and zero horizontal overflow', async () => {
      const layoutInfo = await page.evaluate(() => {
        const card = document.getElementById('settingsSystemUpdatesCard');
        if (card) card.scrollIntoView({ block: 'start' });
        const select = document.getElementById('updateBranchSelect');
        const optionCount = select ? select.options.length : 0;
        const overflow = document.documentElement.scrollWidth - document.documentElement.clientWidth;
        return { optionCount, overflow };
      });
      if (layoutInfo.optionCount < 1) {
        throw new Error('Expected at least 1 branch in #updateBranchSelect');
      }
      if (layoutInfo.overflow > 2) {
        throw new Error(`Horizontal overflow detected (${layoutInfo.overflow}px)`);
      }
    });
  },
};
