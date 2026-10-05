/**
 * CARD-633: journey-qa includes run_journey; Developer has it; tool refuses live :8000 (Python unit covers HITL).
 */
import { waitFor } from './lib/runner.mjs';
import { openApp, getJson } from './lib/app.mjs';

async function openAgents(page) {
  if (!(await page.locator('#forgeAgentSelect').isVisible().catch(() => false))) {
    await page.locator('#dock-agents').click();
  }
  await page.locator('#forgeAgentSelect').waitFor({ state: 'visible', timeout: 20000 });
}

export default {
  id: 'card-633-run-journey-tool',
  card: 'CARD-633',
  title: 'Developer journey-qa can run_journey (throwaway + HITL)',
  async run(j, { page, request, base }) {
    await j.step('Skill Studio journey-qa lists run_journey', async () => {
      const skill = await getJson(request, base + '/api/skill_studio/skills/journey-qa');
      const tools = skill.tools || [];
      for (const t of ['list_journey_reports', 'read_journey_report', 'summarize_journey_failures', 'run_journey']) {
        if (!tools.includes(t)) throw new Error('journey-qa missing tool ' + t + '; got ' + tools.join(','));
      }
    });

    await j.step('Developer ticks journey-qa (shipped agent)', async () => {
      const one = await getJson(request, base + '/api/agents/developer');
      const skills = one.allowed_skill || [];
      const ids = skills.map((s) => (typeof s === 'string' ? s : s.id || s.name));
      if (!ids.includes('journey-qa')) throw new Error('developer missing journey-qa: ' + ids.join(','));
    });

    await j.step('Agent Studio shows journey-qa on Developer', async () => {
      await openApp(page, base);
      await openAgents(page);
      const focus = await page.evaluate(() => document.body.getAttribute('data-desktop-focus'));
      if (focus !== 'agents') await page.locator('#dock-agents').click();
      await waitFor(async () => (await page.locator('#forgeAgentSelect option[value="developer"]').count()) > 0, {
        timeoutMs: 20000,
      });
      await page.selectOption('#forgeAgentSelect', 'developer');
      await waitFor(async () => (await page.inputValue('#forgeNameInput')) === 'Developer', { timeoutMs: 20000 });
      const hasPill = await waitFor(
        async () => (await page.locator('.forge-skill-pill[data-skill-id="journey-qa"]').count()) > 0,
        { timeoutMs: 20000 },
      );
      if (!hasPill) throw new Error('journey-qa skill pill missing');
    });
  },
};
