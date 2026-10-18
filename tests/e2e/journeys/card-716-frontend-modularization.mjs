/**
 * CARD-716: Modularize frontend studios, stylesheets, and templates under 800 lines and retire unused store/window globals.
 */
import { openApp } from './lib/app.mjs';

export default {
  id: 'card-716-frontend-modularization',
  card: 'CARD-716',
  title: 'Modular HTML partials and studio sub-modules render Chat, Settings, Observability, and Projects without window studio globals',
  allow: [],

  async run(j, { page, base }) {
    await j.step('1. Open app, verify partial-expanded views exist, and verify retired window studio globals are undefined', async () => {
      await openApp(page, base);
      const check = await page.evaluate(() => {
        const requiredIds = [
          'view-chat',
          'view-settings',
          'view-observability',
          'view-projects',
          'view-education',
          'view-capabilities',
          'toastContainer',
        ];
        const missing = requiredIds.filter((id) => !document.getElementById(id));
        return {
          missing,
          hasSwitchTabGlobal: typeof window.__autoreivSwitchTab !== 'undefined',
          hasOpenSkillStudioGlobal: typeof window.openSkillStudioForSkill !== 'undefined',
          hasOpenToolsStudioGlobal: typeof window.openToolsStudio !== 'undefined',
        };
      });
      if (check.missing.length > 0) {
        throw new Error(`Missing partial-expanded DOM elements: ${check.missing.join(', ')}`);
      }
      if (check.hasSwitchTabGlobal || check.hasOpenSkillStudioGlobal || check.hasOpenToolsStudioGlobal) {
        throw new Error(`Expected retired window studio globals to be undefined: ${JSON.stringify(check)}`);
      }
      j.note('verified all partial-expanded studio views exist and retired window globals are undefined');
    });

    await j.step('2. Navigate to Settings Studio and verify modular settings controls render', async () => {
      await page.evaluate(() => {
        document.getElementById('tab-settings')?.click();
      });
      await page.locator('#view-settings').waitFor({ state: 'visible', timeout: 10000 });
      await page.locator('#approvalModeSelect').waitFor({ state: 'visible', timeout: 10000 });
      j.note('verified #view-settings and #approvalModeSelect visible');
    });

    await j.step('3. Navigate across Observability, Projects, and back to Chat', async () => {
      await page.evaluate(() => {
        document.getElementById('tab-observability')?.click();
      });
      await page.locator('#view-observability').waitFor({ state: 'visible', timeout: 10000 });

      await page.evaluate(() => {
        document.getElementById('tab-projects')?.click();
      });
      await page.locator('#view-projects').waitFor({ state: 'visible', timeout: 10000 });

      await page.evaluate(() => {
        document.getElementById('tab-chat')?.click();
      });
      await page.locator('#view-chat').waitFor({ state: 'visible', timeout: 10000 });
      await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 10000 });
      j.note('verified navigation across Observability, Projects, and Chat');
    });
  },
};
