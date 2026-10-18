/**
 * CARD-710: Retire dead frontend studio mounts in app.js, dead backend no-ops, toolsmith special case in allowed_tools, and duplicate phase session HITL tool rows.
 */
import { openApp } from './lib/app.mjs';

export default {
  id: 'card-710-retire-dead-studios-and-legacy-paths',
  card: 'CARD-710',
  title: 'Legacy skill-studio and tools-studio tab aliases route cleanly to Capabilities Studio (#view-capabilities)',
  allow: [],

  async run(j, { page, request, base }) {
    await j.step('1. Open app and verify legacy tab aliases route to #view-capabilities', async () => {
      await openApp(page, base);
      await page.evaluate(async () => {
        const { requestTabSwitch } = await import('/static/modules/state/store.js');
        requestTabSwitch('skill-studio');
      });
      await page.locator('#view-capabilities').waitFor({ state: 'visible', timeout: 10000 });
      const activeAfterSkillAlias = await page.evaluate(() => {
        const cap = document.getElementById('view-capabilities');
        return Boolean(cap && !cap.classList.contains('hidden'));
      });
      if (!activeAfterSkillAlias) {
        throw new Error('Expected switchTab("skill-studio") to activate #view-capabilities');
      }

      await page.evaluate(async () => {
        const { requestTabSwitch } = await import('/static/modules/state/store.js');
        requestTabSwitch('chat');
      });
      await page.evaluate(async () => {
        const { requestTabSwitch } = await import('/static/modules/state/store.js');
        requestTabSwitch('tools-studio');
      });
      await page.locator('#view-capabilities').waitFor({ state: 'visible', timeout: 10000 });
      const activeAfterToolsAlias = await page.evaluate(() => {
        const cap = document.getElementById('view-capabilities');
        return Boolean(cap && !cap.classList.contains('hidden'));
      });
      if (!activeAfterToolsAlias) {
        throw new Error('Expected switchTab("tools-studio") to activate #view-capabilities');
      }
      j.note('verified skill-studio and tools-studio tab aliases route to #view-capabilities');
    });

    await j.step('2. Return to Chat and verify pending approvals endpoint responds cleanly', async () => {
      await page.evaluate(async () => {
        const { requestTabSwitch } = await import('/static/modules/state/store.js');
        requestTabSwitch('chat');
      });
      const res = await request.get(`${base}/api/approvals/pending`);
      if (res.status() !== 200) {
        throw new Error(`Expected 200 from /api/approvals/pending, got ${res.status()}`);
      }
      j.note('verified /api/approvals/pending HTTP 200');
    });
  },
};
