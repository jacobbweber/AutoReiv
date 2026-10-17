/**
 * CARD-688 journey: Auto-scoped agents (`*`) and session-mounted skill tools on demand.
 * 1) Open Agent Studio, toggle "Auto-discover all skills (*)" (`#forgeAutoDiscoverSkills`) on AutoReiv, and save.
 * 2) Drop a brand-new Agora skill folder (`agora-dice-roller`) with `tools/roll_weighted_dice.py` AFTER saving,
 *    enable the tool, and verify `/api/agents/autoreiv` automatically grants `roll_weighted_dice` without
 *    manually ticking `agora-dice-roller`.
 * 3) In Chat, ask AutoReiv to open `agora-dice-roller` with `skill_view` and call `roll_weighted_dice(sides=12, bonus=5)`,
 *    verifying that `skill_view` activates the skill for the session and `roll_weighted_dice` executes on the next step.
 * 4) Restore AutoReiv's original skill list and remove the temporary skill folder.
 */
import fs from 'node:fs';
import path from 'node:path';
import { waitFor, clickExpect } from './lib/runner.mjs';
import { getJson, openApp, send, waitReplyIdle } from './lib/app.mjs';

const SKILL_ID = 'agora-dice-roller';
const TOOL_NAME = 'roll_weighted_dice';
const AGENT_ID = 'autoreiv';

function resolveDataSkillsDir() {
  const dataDir = process.env.AUTOREIV_DATA_DIR || path.resolve(process.cwd(), 'scratch', 'live_qa_data');
  return path.join(dataDir, 'skills');
}

export default {
  id: 'card-688-auto-scoped-session-skills',
  card: 'CARD-688',
  title: 'Auto-scoped agents (*) and session-mounted skill tools via skill_view',
  allow: [],
  async run(j, { page, request, base }) {
    const skillsRoot = resolveDataSkillsDir();
    const skillDir = path.join(skillsRoot, SKILL_ID);
    const toolsDir = path.join(skillDir, 'tools');
    let originalSkills = [];

    await j.step('Toggle Auto-discover all skills (*) on AutoReiv in Agent Studio and save', async () => {
      await openApp(page, base);
      const beforeAgent = await getJson(request, `${base}/api/agents/${AGENT_ID}`);
      originalSkills = Array.isArray(beforeAgent.allowed_skill) ? [...beforeAgent.allowed_skill] : [];

      if (!(await page.locator('#forgeAgentSelect').isVisible().catch(() => false))) {
        await page.locator('#dock-agents').click();
      }
      await page.locator('#forgeAgentSelect').waitFor({ state: 'visible', timeout: 20000 });
      await waitFor(
        async () => (await page.locator(`#forgeAgentSelect option[value="${AGENT_ID}"]`).count()) > 0,
        { timeoutMs: 20000 }
      );
      await page.selectOption('#forgeAgentSelect', AGENT_ID);
      await waitFor(
        async () => /autoreiv/i.test(await page.inputValue('#forgeNameInput').catch(() => '')),
        { timeoutMs: 20000 }
      );

      const caps = page.locator('details[data-section="capabilities"]');
      await waitFor(async () => (await caps.getAttribute('aria-busy').catch(() => 'true')) !== 'true', { timeoutMs: 20000 });
      if (!(await caps.evaluate((el) => el.open).catch(() => true))) {
        await caps.locator('summary').first().click();
      }

      const autoBtn = page.locator('#forgeAutoDiscoverSkills');
      await autoBtn.waitFor({ state: 'visible', timeout: 20000 });
      await autoBtn.scrollIntoViewIfNeeded();
      if ((await autoBtn.getAttribute('aria-pressed')) !== 'true') {
        await autoBtn.click();
      }
      await waitFor(async () => (await autoBtn.getAttribute('aria-pressed')) === 'true', { timeoutMs: 5000 });

      await page.locator('#saveAgentBtn').scrollIntoViewIfNeeded().catch(() => {});
      await clickExpect(
        page.locator('#saveAgentBtn'),
        async () => {
          const ag = await getJson(request, `${base}/api/agents/${AGENT_ID}`);
          return Array.isArray(ag.allowed_skill) && ag.allowed_skill.includes('*');
        },
        { label: 'Save Profile', what: 'Auto-discover (*) saved on AutoReiv', timeoutMs: 20000 }
      );
      j.note('AutoReiv saved with Auto-discover all skills (*)');
    });

    await j.step('Drop a new Agora skill folder AFTER saving and verify AutoReiv discovers it without manual ticking', async () => {
      fs.mkdirSync(toolsDir, { recursive: true });
      fs.writeFileSync(
        path.join(skillDir, 'SKILL.md'),
        [
          '---',
          'name: Agora Dice Roller',
          'description: Roll weighted dice with deterministic bonus calculation.',
          '---',
          '# Agora Dice Roller',
          `Call \`${TOOL_NAME}(sides, bonus)\` after opening this skill.`,
          '',
        ].join('\n'),
        'utf-8'
      );
      fs.writeFileSync(
        path.join(toolsDir, `${TOOL_NAME}.py`),
        [
          '"""Compute a deterministic weighted roll result (sides + bonus)."""',
          'RISK = "read_only"',
          '',
          'def run(sides: int = 6, bonus: int = 0) -> dict:',
          '    return {"roll_total": int(sides) + int(bonus), "sides": int(sides), "bonus": int(bonus)}',
          '',
        ].join('\n'),
        'utf-8'
      );

      const toggleRes = await request.post(
        `${base}/api/capabilities/skills/${SKILL_ID}/tools/${TOOL_NAME}/toggle`,
        { data: { enabled: true } }
      );
      if (!toggleRes.ok()) throw new Error(`Toggle enable failed: ${toggleRes.status()}`);

      const ag = await getJson(request, `${base}/api/agents/${AGENT_ID}`);
      if ((ag.allowed_skill || []).includes(SKILL_ID)) {
        throw new Error(`${SKILL_ID} should not be manually listed in allowed_skill`);
      }
      if (!(ag.allowed_tools || []).includes(TOOL_NAME)) {
        throw new Error(`Expected ${TOOL_NAME} to be auto-granted via '*', got: ${JSON.stringify(ag.allowed_tools)}`);
      }
      j.note(`Unticked skill ${SKILL_ID} auto-granted ${TOOL_NAME} via '*'`);
    });

    await j.step('Open Chat and verify AutoReiv activates agora-dice-roller via skill_view and calls roll_weighted_dice', async () => {
      if (!(await page.locator('#promptInput').isVisible().catch(() => false))) {
        await page.locator('#dock-chat').click();
      }
      await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 20000 });
      if ((await page.locator('#agentSelect').inputValue().catch(() => '')) !== AGENT_ID) {
        await page.selectOption('#agentSelect', AGENT_ID);
        await page.waitForTimeout(600);
      }

      await send(
        page,
        `First call skill_view with skill_id "${SKILL_ID}" to load the skill and mount its tools, then call ${TOOL_NAME} with sides=12 and bonus=5 and report roll_total.`
      );
      await waitReplyIdle(page, { timeoutMs: 180000 });

      const sessions = await getJson(request, `${base}/api/sessions?agent_id=${AGENT_ID}`);
      const latest = (sessions.sessions || sessions || [])[0];
      if (!latest || !latest.id) throw new Error('No chat session found for AutoReiv');
      const msgs = await getJson(request, `${base}/api/sessions/${encodeURIComponent(latest.id)}/messages`);
      const rows = Array.isArray(msgs) ? msgs : (msgs.messages || []);
      const toolNames = rows.filter((m) => m.role === 'tool').map((m) => m.name);
      if (!toolNames.includes('skill_view')) {
        throw new Error(`Expected skill_view in tool messages, got: ${JSON.stringify(toolNames)}`);
      }
      if (!toolNames.includes(TOOL_NAME)) {
        throw new Error(`Expected ${TOOL_NAME} to be mounted and called after skill_view, got: ${JSON.stringify(toolNames)}`);
      }
      j.note(`Session ${latest.id} executed tools in order: ${toolNames.join(' -> ')}`);
    }, { timeoutMs: 240000 });

    await j.step('Clean up: restore AutoReiv skills and remove temporary Agora skill folder', async () => {
      const ag = await getJson(request, `${base}/api/agents/${AGENT_ID}`);
      await request.put(`${base}/api/agents/${AGENT_ID}`, {
        data: {
          name: ag.name,
          description: ag.description,
          system_prompt: ag.system_prompt,
          allowed_skill: originalSkills.filter((s) => s !== '*'),
        },
      });
      await request.post(
        `${base}/api/capabilities/skills/${SKILL_ID}/tools/${TOOL_NAME}/toggle`,
        { data: { enabled: false } }
      );
      fs.rmSync(skillDir, { recursive: true, force: true });
    });
  },
};
