/**
 * CARD-727: Branch Switch Fast-Forward and Resilient Dependency Sync on Updates.
 *
 * Verifies:
 * 1. Settings -> Preferences -> System & Software Updates renders version info,
 *    branch selector (#updateBranchSelect), Check for Updates (#checkForUpdatesBtn),
 *    Update now (#applyUpdateBtn), and Switch (#switchBranchBtn).
 * 2. Clicking Check for Updates executes /api/system/updates/check and updates the
 *    status banner (#updateStatusBanner) and branch list cleanly without uv errors.
 * 3. Zero horizontal overflow occurs on desktop and phone viewports.
 */
import { openApp } from './lib/app.mjs';

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
  id: 'card-727-branch-switch-fast-forward-and-resilient',
  card: 'CARD-727',
  title: 'System & Software Updates checks updates and populates branch selector without uv dependency errors',
  allow: [],
  async run(j, { page, base }) {
    await j.step('1. Open Settings -> Preferences -> System & Software Updates and verify version and branch controls', async () => {
      await openApp(page, base);
      await openSettingsUpdates(page);

      const state = await page.evaluate(() => {
        const versionPill = document.getElementById('systemVersionPill');
        const checkBtn = document.getElementById('checkForUpdatesBtn');
        const applyBtn = document.getElementById('applyUpdateBtn');
        const branchSelect = document.getElementById('updateBranchSelect');
        const switchBtn = document.getElementById('switchBranchBtn');
        return {
          versionText: versionPill ? versionPill.textContent.trim() : '',
          hasCheckBtn: Boolean(checkBtn && !checkBtn.disabled),
          hasApplyBtn: Boolean(applyBtn && !applyBtn.classList.contains('hidden')),
          optionCount: branchSelect ? branchSelect.options.length : 0,
          hasSwitchBtn: Boolean(switchBtn && !switchBtn.disabled),
        };
      });

      if (!state.versionText || state.versionText === '-') {
        throw new Error(`Expected populated #systemVersionPill, got ${JSON.stringify(state)}`);
      }
      if (!state.hasCheckBtn || !state.hasApplyBtn || !state.hasSwitchBtn || state.optionCount < 1) {
        throw new Error(`Expected enabled update/branch controls, got ${JSON.stringify(state)}`);
      }
    });

    await j.step('2. Trigger Check for Updates and verify status banner and branch list refresh cleanly with zero overflow', async () => {
      await page.locator('#checkForUpdatesBtn').click();
      await page.locator('#updateStatusBanner').waitFor({ state: 'visible', timeout: 20000 });
      await page.waitForTimeout(300);

      const banner = await page.evaluate(() => {
        const msgEl = document.getElementById('updateStatusMessage');
        const select = document.getElementById('updateBranchSelect');
        const overflow = document.documentElement.scrollWidth - document.documentElement.clientWidth;
        return {
          message: msgEl ? msgEl.textContent.trim() : '',
          branches: select ? Array.from(select.options).map((o) => o.value) : [],
          overflow,
        };
      });

      if (!banner.message || banner.message.includes("No such file or directory: 'uv'")) {
        throw new Error(`Unexpected update banner message: ${JSON.stringify(banner)}`);
      }
      if (banner.branches.length < 1) {
        throw new Error(`Expected branches in selector, got ${JSON.stringify(banner)}`);
      }
      if (banner.overflow > 2) {
        throw new Error(`Horizontal overflow detected (${banner.overflow}px)`);
      }
    });
  },
};
