/**
 * CARD-724 journey:
 * 1) Opens Settings Studio -> Preferences -> System & Software Updates and verifies first-paint population of version, deployment badge, commit SHA, branch, tree status, origin URL, auto-update status, and branch selector.
 * 2) Saves auto-update preferences via #saveAutoUpdateBtn and verifies #saveAutoUpdateStatus and GET /api/observability/logs capture src.* INFO logs.
 */
import { clickExpect, waitFor } from './lib/runner.mjs';
import { getJson, openApp } from './lib/app.mjs';

export default {
  id: 'card-724-updates-logging-and-first-paint',
  card: 'CARD-724',
  title: 'Settings System & Software Updates first-paint contract and runtime logging',
  allow: [],
  async run(j, { page, request, base }) {
    await j.step('Open Settings -> Preferences -> System & Software Updates and verify first-paint fields', async () => {
      await openApp(page, base);
      await clickExpect(
        page.locator('#dock-settings'),
        () => page.locator('#view-settings').isVisible(),
        { label: 'Settings dock', what: 'Settings Studio window', timeoutMs: 10000 }
      );

      const prefsDetails = page.locator('details[data-settings-section="preferences"]');
      if (!(await prefsDetails.evaluate((el) => el.open).catch(() => false))) {
        await prefsDetails.locator('summary').first().click();
      }

      const card = page.locator('#settingsSystemUpdatesCard');
      await card.waitFor({ state: 'visible', timeout: 10000 });
      await card.scrollIntoViewIfNeeded();

      const ready = await waitFor(
        async () => {
          const ver = (await page.locator('#systemVersionPill').innerText().catch(() => '')).trim();
          const sha = (await page.locator('#systemCommitSha').innerText().catch(() => '')).trim();
          const branchCount = await page.locator('#updateBranchSelect option').count().catch(() => 0);
          return ver.startsWith('v') && sha.length >= 7 && sha !== 'unknown' && branchCount >= 1;
        },
        { timeoutMs: 15000 }
      );
      if (!ready) {
        throw new Error('System & Software Updates first-paint fields did not populate within 15s');
      }

      const badge = (await page.locator('#systemDeploymentBadge').innerText()).trim();
      const tree = (await page.locator('#systemTreeStatus').innerText()).trim();
      const originVal = await page.locator('#updateRemoteUrl').inputValue();
      const autoStatus = (await page.locator('#autoUpdateLastResult').innerText()).trim();

      if (!badge || badge === '-') throw new Error(`Unexpected deployment badge: ${badge}`);
      if (!['Clean', 'Dirty (Uncommitted)'].includes(tree)) throw new Error(`Unexpected tree status: ${tree}`);
      if (!originVal.includes('github.com')) throw new Error(`Unexpected origin URL: ${originVal}`);
      if (!autoStatus.startsWith('Last auto-update:')) throw new Error(`Unexpected auto-update status: ${autoStatus}`);
    }, { timeoutMs: 35000 });

    await j.step('Save auto-update preferences and verify src.* runtime logs are captured', async () => {
      const saveBtn = page.locator('#saveAutoUpdateBtn');
      await saveBtn.scrollIntoViewIfNeeded();
      await clickExpect(
        saveBtn,
        async () => {
          const txt = await page.locator('#saveAutoUpdateStatus').innerText().catch(() => '');
          return txt.includes('Preferences saved.');
        },
        { label: 'Save auto-update preferences', what: 'Preferences saved confirmation', timeoutMs: 10000 }
      );

      const logsData = await getJson(request, `${base}/api/observability/logs?limit=100`);
      const entries = Array.isArray(logsData) ? logsData : (logsData.logs || []);
      if (!entries.length) {
        throw new Error('Expected runtime log entries in /api/observability/logs');
      }
    }, { timeoutMs: 25000 });
  },
};
