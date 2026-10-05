/**
 * CARD-621: after layout restore leaves Agents open, the first dock click focuses
 * Agents (does not minimize), and picking AutoReiv fills #forgeNameInput.
 */
import { waitFor } from './lib/runner.mjs';
import { openApp } from './lib/app.mjs';

async function seedRestoreAgents(page) {
  await page.addInitScript(() => {
    localStorage.setItem(
      'autoreiv.agentDesktop.v1',
      JSON.stringify({
        windows: { agents: { x: 40, y: 40, w: 720, h: 560 } },
        gridOverlay: false,
        autoRestore: true,
        openWindows: ['agents'],
        savedPresets: [],
      }),
    );
  });
}

async function pickAutoreiv(page) {
  const visible = await waitFor(async () => {
    const focus = await page.evaluate(() => document.body.getAttribute('data-desktop-focus'));
    const selectVisible = await page.locator('#forgeAgentSelect').isVisible().catch(() => false);
    if (focus !== 'agents' || !selectVisible) {
      await page.locator('#dock-agents').click();
    }
    const focus2 = await page.evaluate(() => document.body.getAttribute('data-desktop-focus'));
    return focus2 === 'agents' && (await page.locator('#forgeAgentSelect').isVisible().catch(() => false));
  }, { timeoutMs: 20000 });
  if (!visible) throw new Error('Agents studio (#forgeAgentSelect) never became visible/focused');
  const hasOpt = await waitFor(
    async () => (await page.locator('#forgeAgentSelect option[value="autoreiv"]').count()) > 0,
    { timeoutMs: 20000 },
  );
  if (!hasOpt) throw new Error('autoreiv option missing from #forgeAgentSelect');
  await page.selectOption('#forgeAgentSelect', 'autoreiv');
  const named = await waitFor(async () => (await page.inputValue('#forgeNameInput')) === 'AutoReiv', {
    timeoutMs: 20000,
  });
  if (!named) throw new Error('#forgeNameInput did not become AutoReiv');
}

export default {
  id: 'card-621-tc39-stable',
  card: 'CARD-621',
  title: 'Restored Agents stays open on first dock click; AutoReiv name fills',
  async run(j, { page, base, viewport }) {
    if (viewport.name === 'phone') {
      await j.step('Phone: open Agents and pick AutoReiv (no desktop restore race)', async () => {
        await openApp(page, base);
        await pickAutoreiv(page);
      });
      return;
    }

    await j.step('Seed prefs that restore Agents, load app, Agents visible and unfocused', async () => {
      await seedRestoreAgents(page);
      await openApp(page, base);
      await page.locator('#desktopWin-agents').waitFor({ state: 'visible', timeout: 20000 });
      const unfocused = await waitFor(
        async () =>
          (await page.evaluate(() => document.body.getAttribute('data-desktop-focus'))) !== 'agents',
        { timeoutMs: 5000 },
      );
      if (!unfocused) throw new Error('data-desktop-focus still agents after restore');
      const focused = await page.locator('#desktopWin-agents.is-focused').count();
      if (focused !== 0) throw new Error('restored Agents window should not stay focused');
    });

    await j.step('First dock-agents click focuses Agents (does not minimize)', async () => {
      await page.locator('#dock-agents').click();
      await page.locator('#forgeAgentSelect').waitFor({ state: 'visible', timeout: 10000 });
      const min = await page.locator('#desktopWin-agents.is-minimized').count();
      if (min !== 0) throw new Error('first dock click minimized restored Agents');
    });

    await j.step('Pick AutoReiv; name input reads AutoReiv', async () => {
      await pickAutoreiv(page);
    });

    await j.step('Reload with same restore prefs; pick again stays green', async () => {
      await page.reload({ waitUntil: 'domcontentloaded' });
      await page.locator('#desktopWin-agents').waitFor({ state: 'visible', timeout: 20000 });
      await pickAutoreiv(page);
    });
  },
};
