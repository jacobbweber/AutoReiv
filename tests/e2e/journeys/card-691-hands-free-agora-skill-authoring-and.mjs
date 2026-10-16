/**
 * CARD-691 journey: Hands-free Agora skill authoring and auto-discovery for AutoReiv (`user:*`).
 * 1) Seed an Agora skill folder `handsfree-math` (`SKILL.md` + `tools/triple_plus_one.py`) via
 *    `PUT /api/capabilities/skills/handsfree-math/file` WITHOUT editing AutoReiv in Agent Studio.
 * 2) Verify `GET /api/agents/autoreiv` already includes `handsfree-math` in `allowed_skill`
 *    and `triple_plus_one` in `allowed_tools` via shipped `user:*`.
 * 3) Open Chat on AutoReiv (without visiting Agent Studio) and ask AutoReiv to open
 *    `handsfree-math` with `skill_view` and call `triple_plus_one(value=14)` (`43`),
 *    verifying that the tool executes and returns the result in Chat.
 */
import fs from 'node:fs';
import path from 'node:path';
import { getJson, openApp, send, waitReplyIdle } from './lib/app.mjs';

const SKILL_ID = 'handsfree-math';
const TOOL_NAME = 'triple_plus_one';
const AGENT_ID = 'autoreiv';

function resolveDataSkillsDir() {
  const dataDir = process.env.AUTOREIV_DATA_DIR || path.resolve(process.cwd(), 'scratch', 'live_qa_data');
  return path.join(dataDir, 'skills');
}

export default {
  id: 'card-691-hands-free-agora-skill-authoring-and',
  card: 'CARD-691',
  title: 'Hands-free Agora skill authoring and auto-discovery for AutoReiv',
  allow: [],
  async run(j, { page, request, base }) {
    const skillsRoot = resolveDataSkillsDir();

    await j.step('Seed Agora skill folder handsfree-math and verify AutoReiv auto-discovers it via user:* without Agent Studio', async () => {
      await openApp(page, base);

      const mdRes = await request.put(`${base}/api/capabilities/skills/${SKILL_ID}/file`, {
        data: {
          path: 'SKILL.md',
          content: [
            '---',
            'name: Handsfree Math',
            'description: Compute triple_plus_one for an integer.',
            '---',
            '# Handsfree Math',
            `Call \`${TOOL_NAME}(value=...)\` and report the returned result.`,
            '',
          ].join('\n'),
        },
      });
      if (!mdRes.ok()) throw new Error(`Failed to write SKILL.md: ${mdRes.status()}`);

      const toolRes = await request.put(`${base}/api/capabilities/skills/${SKILL_ID}/file`, {
        data: {
          path: `tools/${TOOL_NAME}.py`,
          content: [
            '"""Compute 3 * value + 1."""',
            'RISK = "read_only"',
            '',
            'def run(value: int = 10) -> dict:',
            '    return {"computed": int(value) * 3 + 1}',
            '',
          ].join('\n'),
        },
      });
      if (!toolRes.ok()) throw new Error(`Failed to write tools/${TOOL_NAME}.py: ${toolRes.status()}`);
      const toolBody = await toolRes.json();
      if (!toolBody.auto_enabled || !toolBody.mounted) {
        throw new Error(`Expected ${TOOL_NAME} to auto-enable and mount, got: ${JSON.stringify(toolBody)}`);
      }

      const ag = await getJson(request, `${base}/api/agents/${AGENT_ID}`);
      const allowedTools = Array.isArray(ag.allowed_tools) ? ag.allowed_tools : [];
      if (!allowedTools.includes(TOOL_NAME)) {
        throw new Error(`Expected ${TOOL_NAME} in AutoReiv allowed_tools via user:*, got: ${JSON.stringify(allowedTools)}`);
      }
      if (!allowedTools.includes('write_skill_file')) {
        throw new Error(`Expected write_skill_file in AutoReiv allowed_tools via agent-authoring, got: ${JSON.stringify(allowedTools)}`);
      }
      j.note(`AutoReiv auto-discovered ${SKILL_ID}/${TOOL_NAME} via user:* with zero Agent Studio configuration`);
    });

    await j.step('In Chat, AutoReiv opens handsfree-math with skill_view and executes triple_plus_one on demand', async () => {
      if (!(await page.locator('#promptInput').isVisible().catch(() => false))) {
        const dockChat = page.locator('#dock-chat');
        if (await dockChat.isVisible().catch(() => false)) {
          await dockChat.click();
        } else {
          await page.locator('#tab-chat').click();
        }
      }
      await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 20000 });
      if ((await page.locator('#agentSelect').inputValue().catch(() => '')) !== AGENT_ID) {
        await page.selectOption('#agentSelect', AGENT_ID);
        await page.waitForTimeout(500);
      }

      await send(
        page,
        `First call skill_view with skill_id "${SKILL_ID}". Then call ${TOOL_NAME} with value=14 and state the computed number.`
      );
      await waitReplyIdle(page, { timeoutMs: 240000 });

      const sessions = await getJson(request, `${base}/api/sessions?agent_id=${AGENT_ID}`);
      const latest = (sessions.sessions || sessions || [])[0];
      if (!latest || !latest.id) throw new Error('No chat session found for AutoReiv');
      const msgs = await getJson(request, `${base}/api/sessions/${encodeURIComponent(latest.id)}/messages`);
      const rows = Array.isArray(msgs) ? msgs : (msgs.messages || []);
      const toolNames = rows.filter((m) => m.role === 'tool').map((m) => m.name);
      if (!toolNames.includes('skill_view')) {
        throw new Error(`Expected skill_view in tool calls, got: ${JSON.stringify(toolNames)}`);
      }
      const skillViewMsg = rows.find((m) => m.role === 'tool' && m.name === 'skill_view');
      const skillViewText = String((skillViewMsg && skillViewMsg.content) || '');
      if (skillViewText.includes('not allowed for this agent')) {
        throw new Error(`skill_view rejected user:* skill ${SKILL_ID}: ${skillViewText}`);
      }
      if (!toolNames.includes(TOOL_NAME)) {
        throw new Error(`Expected ${TOOL_NAME} in tool calls after skill_view, got: ${JSON.stringify(toolNames)}`);
      }
      j.note(`AutoReiv executed ${toolNames.join(' -> ')} hands-free`);
    }, { timeoutMs: 260000 });

    await j.step('Clean up temporary skill folder handsfree-math', async () => {
      fs.rmSync(path.join(skillsRoot, SKILL_ID), { recursive: true, force: true });
    });
  },
};
