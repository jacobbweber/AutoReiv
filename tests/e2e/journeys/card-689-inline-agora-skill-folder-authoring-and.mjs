/**
 * CARD-689 journey: Inline Agora skill folder authoring & risk-tiered tool auto-enable.
 * 1) Via PUT /api/capabilities/skills/agora-self-built/file, write a pure read_only tool
 *    (`tools/calc_compound.py`) and verify ToolCheckService runs it, passes the sample call,
 *    auto-enables it (`auto_enabled: true`, `approval: "enabled"`), and mounts it immediately.
 * 2) Via PUT /api/capabilities/skills/agora-self-built/file, write an outside-access tool
 *    (`tools/fetch_remote.py` importing `urllib.request`) and verify ToolCheckService flags
 *    `access: ["network"]`, saves it disabled (`auto_enabled: false`, `approval: "disabled"`),
 *    and does not mount it.
 * 3) Toggle "Auto-discover all skills (*)" on AutoReiv in Agent Studio, then in Chat ask
 *    AutoReiv to open `capability-authoring` with `skill_view`, call `write_skill_file` to
 *    build `skills/agora-temp-converter/tools/celsius_to_kelvin.py`, and call
 *    `celsius_to_kelvin(celsius=100)` in the same turn (`kelvin = 373`).
 * 4) Clean up temporary skill folders and restore AutoReiv's skill list.
 */
import fs from 'node:fs';
import path from 'node:path';
import { waitFor, clickExpect } from './lib/runner.mjs';
import { getJson, openApp, send, waitReplyIdle } from './lib/app.mjs';

const HTTP_SKILL_ID = 'agora-self-built';
const CHAT_SKILL_ID = 'agora-temp-converter';
const CHAT_TOOL_NAME = 'celsius_to_kelvin';
const AGENT_ID = 'autoreiv';

function resolveDataSkillsDir() {
  const dataDir = process.env.AUTOREIV_DATA_DIR || path.resolve(process.cwd(), 'scratch', 'live_qa_data');
  return path.join(dataDir, 'skills');
}

export default {
  id: 'card-689-inline-agora-skill-folder-authoring-and',
  card: 'CARD-689',
  title: 'Inline Agora skill folder authoring and risk-tiered tool auto-enable',
  allow: [],
  async run(j, { page, request, base }) {
    const skillsRoot = resolveDataSkillsDir();
    let originalSkills = [];

    await j.step('Verify PUT /api/capabilities/skills/{id}/file auto-enables pure read_only tools and holds outside-access tools', async () => {
      await openApp(page, base);
      const beforeAgent = await getJson(request, `${base}/api/agents/${AGENT_ID}`);
      originalSkills = Array.isArray(beforeAgent.allowed_skill) ? [...beforeAgent.allowed_skill] : [];

      const pureRes = await request.put(`${base}/api/capabilities/skills/${HTTP_SKILL_ID}/file`, {
        data: {
          path: 'tools/calc_compound.py',
          content: [
            '"""Calculate base + bonus."""',
            'RISK = "read_only"',
            '',
            'def run(base: int = 10, bonus: int = 5) -> dict:',
            '    return {"compound": int(base) + int(bonus)}',
            '',
          ].join('\n'),
        },
      });
      if (!pureRes.ok()) throw new Error(`PUT pure tool failed: ${pureRes.status()}`);
      const pureBody = await pureRes.json();
      if (!pureBody.auto_enabled || pureBody.approval !== 'enabled' || !pureBody.mounted) {
        throw new Error(`Expected pure tool to auto-enable and mount, got: ${JSON.stringify(pureBody)}`);
      }

      const flaggedRes = await request.put(`${base}/api/capabilities/skills/${HTTP_SKILL_ID}/file`, {
        data: {
          path: 'tools/fetch_remote.py',
          content: [
            '"""Fetch remote URL over network."""',
            'import urllib.request',
            '',
            'def run(url: str = "https://example.com") -> dict:',
            '    return {"url": url}',
            '',
          ].join('\n'),
        },
      });
      if (!flaggedRes.ok()) throw new Error(`PUT flagged tool failed: ${flaggedRes.status()}`);
      const flaggedBody = await flaggedRes.json();
      if (flaggedBody.auto_enabled || flaggedBody.approval !== 'disabled' || flaggedBody.mounted) {
        throw new Error(`Expected network tool to save disabled, got: ${JSON.stringify(flaggedBody)}`);
      }
      if (!(flaggedBody.access || []).includes('network')) {
        throw new Error(`Expected network access flag, got: ${JSON.stringify(flaggedBody.access)}`);
      }
      j.note('Pure read_only tool calc_compound auto-enabled; network tool fetch_remote saved disabled');
    });

    await j.step('Enable Auto-discover all skills (*) on AutoReiv in Agent Studio', async () => {
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
    });

    await j.step('In Chat, AutoReiv builds celsius_to_kelvin via write_skill_file and calls it in the same turn', async () => {
      if (!(await page.locator('#promptInput').isVisible().catch(() => false))) {
        await page.locator('#dock-chat').click();
      }
      await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 20000 });
      if ((await page.locator('#agentSelect').inputValue().catch(() => '')) !== AGENT_ID) {
        await page.selectOption('#agentSelect', AGENT_ID);
        await page.waitForTimeout(600);
      }

      const pyCode = [
        '"""Convert Celsius to Kelvin."""',
        'RISK = "read_only"',
        'def run(celsius: int = 25) -> dict:',
        '    return {"kelvin": int(celsius) + 273}',
      ].join('\\n');

      await send(
        page,
        `Step 1: call skill_view with skill_id "capability-authoring" to mount write_skill_file. ` +
          `Step 2: call write_skill_file with skill_id "${CHAT_SKILL_ID}", path "tools/${CHAT_TOOL_NAME}.py", and content "${pyCode}". ` +
          `Step 3: call ${CHAT_TOOL_NAME} with celsius=100 and report the kelvin result.`
      );
      await waitReplyIdle(page, { timeoutMs: 240000 });

      const sessions = await getJson(request, `${base}/api/sessions?agent_id=${AGENT_ID}`);
      const latest = (sessions.sessions || sessions || [])[0];
      if (!latest || !latest.id) throw new Error('No chat session found for AutoReiv');
      const msgs = await getJson(request, `${base}/api/sessions/${encodeURIComponent(latest.id)}/messages`);
      const rows = Array.isArray(msgs) ? msgs : (msgs.messages || []);
      const toolNames = rows.filter((m) => m.role === 'tool').map((m) => m.name);
      if (!toolNames.includes('skill_view')) {
        throw new Error(`Expected skill_view in tool messages, got: ${JSON.stringify(toolNames)}`);
      }
      if (!toolNames.includes('write_skill_file')) {
        throw new Error(`Expected write_skill_file in tool messages, got: ${JSON.stringify(toolNames)}`);
      }
      if (!toolNames.includes(CHAT_TOOL_NAME)) {
        throw new Error(`Expected self-built ${CHAT_TOOL_NAME} to auto-enable and execute, got: ${JSON.stringify(toolNames)}`);
      }
      j.note(`AutoReiv self-built and executed tools in one turn: ${toolNames.join(' -> ')}`);
    }, { timeoutMs: 260000 });

    await j.step('Clean up: restore AutoReiv skills and remove temporary skill folders', async () => {
      const ag = await getJson(request, `${base}/api/agents/${AGENT_ID}`);
      await request.put(`${base}/api/agents/${AGENT_ID}`, {
        data: {
          name: ag.name,
          description: ag.description,
          system_prompt: ag.system_prompt,
          allowed_skill: originalSkills.filter((s) => s !== '*'),
        },
      });
      fs.rmSync(path.join(skillsRoot, HTTP_SKILL_ID), { recursive: true, force: true });
      fs.rmSync(path.join(skillsRoot, CHAT_SKILL_ID), { recursive: true, force: true });
    });
  },
};
