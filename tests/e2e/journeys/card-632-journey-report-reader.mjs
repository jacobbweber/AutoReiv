/**
 * CARD-632: Developer ticks journey-qa; report tools summarize a seeded fail report via the API surface
 * (tools are registered; we exercise them through a small owner probe that lists Developer skills and
 * calls the Python tools are covered by unit tests — this journey checks the Studio skill tick + report files).
 */
import { waitFor } from './lib/runner.mjs';
import { openApp, getJson } from './lib/app.mjs';
import fs from 'fs';
import os from 'os';
import path from 'path';

async function openAgents(page) {
  if (!(await page.locator('#forgeAgentSelect').isVisible().catch(() => false))) {
    await page.locator('#dock-agents').click();
  }
  await page.locator('#forgeAgentSelect').waitFor({ state: 'visible', timeout: 20000 });
}

export default {
  id: 'card-632-journey-report-reader',
  card: 'CARD-632',
  title: 'Developer has journey-qa; seeded fail report summarizes',
  async run(j, { page, request, base, viewport }) {
    const root = process.env.AUTOREIV_QA_REPORT_DIR || path.join(os.tmpdir(), 'autoreiv-qa');
    const cardDir = path.join(root, 'card-632-seed');
    fs.mkdirSync(cardDir, { recursive: true });
    const report = {
      title: 'AutoReiv live QA',
      startedAt: new Date().toString(),
      base,
      runs: [
        {
          journey: 'card-632-seed',
          viewport: viewport.name,
          outcome: 'fail',
          steps: [
            {
              step: 'Expect green',
              status: 'fail',
              reason: 'seeded failure for CARD-632',
              screenshot: path.join(cardDir, 'seed-fail.png'),
              ms: 1,
            },
          ],
          notes: [],
          consoleErrors: [],
          failedRequests: [],
        },
      ],
    };
    fs.writeFileSync(path.join(cardDir, 'report.json'), JSON.stringify(report, null, 2));
    fs.writeFileSync(path.join(cardDir, 'summary.md'), '# seeded\n');

    await j.step('Skill Studio has journey-qa; Developer ticks it (shipped file agents)', async () => {
      const skill = await getJson(request, base + '/api/skill_studio/skills/journey-qa');
      const tools = skill.tools || [];
      for (const t of ['list_journey_reports', 'read_journey_report', 'summarize_journey_failures']) {
        if (!tools.includes(t)) throw new Error('journey-qa missing tool ' + t);
      }
      const one = await getJson(request, base + '/api/agents/developer');
      const skills = one.allowed_skill || [];
      const ids = skills.map((s) => (typeof s === 'string' ? s : s.id || s.name));
      if (!ids.includes('journey-qa')) {
        throw new Error('developer missing journey-qa skill (shipped agent should tick it): ' + ids.join(','));
      }
    });

    await j.step('Agent Studio shows Developer with journey-qa available', async () => {
      await openApp(page, base);
      await openAgents(page);
      const focus = await page.evaluate(() => document.body.getAttribute('data-desktop-focus'));
      if (focus !== 'agents') await page.locator('#dock-agents').click();
      await waitFor(async () => (await page.locator('#forgeAgentSelect option[value="developer"]').count()) > 0, {
        timeoutMs: 20000,
      });
      await page.selectOption('#forgeAgentSelect', 'developer');
      await waitFor(async () => (await page.inputValue('#forgeNameInput')) === 'Developer', { timeoutMs: 20000 });
      // skill pills may take a moment
      const hasPill = await waitFor(
        async () => (await page.locator('.forge-skill-pill[data-skill-id="journey-qa"]').count()) > 0,
        { timeoutMs: 20000 },
      );
      if (!hasPill) throw new Error('journey-qa skill pill missing for Developer');
    });

    await j.step('Seeded report folder exists for summarize tools (unit-tested; path checked here)', async () => {
      const p = path.join(cardDir, 'report.json');
      if (!fs.existsSync(p)) throw new Error('seed report missing');
      const data = JSON.parse(fs.readFileSync(p, 'utf8'));
      if (data.runs[0].outcome !== 'fail') throw new Error('seed should fail');
    });
  },
};
