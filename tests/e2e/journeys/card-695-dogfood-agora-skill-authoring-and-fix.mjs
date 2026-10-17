/**
 * CARD-695 journey: Dogfood Agora skill authoring and fix post-registration reply and resolver overhead.
 * 1) In Chat, ask AutoReiv to author the first user Agora skill folder `dogfood-unit-math`
 *    (`SKILL.md`, `references/formulas.md`, and pure read_only `tools/f_to_c.py`) via `write_skill_file`,
 *    and verify no "Reply failed: The model returned an empty reply" banner or error occurs.
 * 2) In Chat, ask AutoReiv to author the second user Agora skill folder `dogfood-net-probe`
 *    (`SKILL.md` and network-access `tools/probe_url.py`) via `write_skill_file`, and verify
 *    it saves disabled (`approval: "disabled"`, `access: ["network"]`) with a clean assistant reply.
 * 3) Open `#view-capabilities`, verify both `dogfood-unit-math` and `dogfood-net-probe` appear
 *    in the unified directory tree with their files and safety statuses (`f_to_c` Enabled,
 *    `probe_url` Disabled / needs approval), and enable `probe_url` via `#capabilitiesToggleToolBtn`.
 * 4) Return to Chat and ask AutoReiv to open `dogfood-unit-math` with `skill_view` and execute
 *    `f_to_c(fahrenheit=212)` (`celsius = 100`).
 * 5) Clean up both temporary user Agora skill folders.
 */
import fs from 'node:fs';
import path from 'node:path';
import { clickExpect, waitFor } from './lib/runner.mjs';
import { getJson, openApp, send, waitReplyIdle } from './lib/app.mjs';

const SKILL_PURE = 'dogfood-unit-math';
const TOOL_PURE = 'f_to_c';
const SKILL_NET = 'dogfood-net-probe';
const TOOL_NET = 'probe_url';
const AGENT_ID = 'autoreiv';

function resolveDataSkillsDir() {
  const dataDir = process.env.AUTOREIV_DATA_DIR || path.resolve(process.cwd(), 'scratch', 'live_qa_data');
  return path.join(dataDir, 'skills');
}

async function ensureChatOpen(page) {
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
}

export default {
  id: 'card-695-dogfood-agora-skill-authoring-and-fix',
  card: 'CARD-695',
  title: 'Dogfood Agora skill authoring and fix post-registration reply and resolver overhead',
  allow: [],
  async run(j, { page, request, base }) {
    const skillsRoot = resolveDataSkillsDir();
    fs.rmSync(path.join(skillsRoot, SKILL_PURE), { recursive: true, force: true });
    fs.rmSync(path.join(skillsRoot, SKILL_NET), { recursive: true, force: true });

    await j.step('In Chat, AutoReiv authors Agora skill folder dogfood-unit-math (SKILL.md, references/formulas.md, tools/f_to_c.py) with no empty-reply error', async () => {
      await openApp(page, base);
      await ensureChatOpen(page);

      const skillMd = [
        '---',
        'name: Dogfood Unit Math',
        'description: Convert Fahrenheit to Celsius with f_to_c.',
        '---',
        '# Dogfood Unit Math',
        'Use f_to_c(fahrenheit=...) to convert temperatures.',
      ].join('\\n');
      const refMd = '# Formulas\\nCelsius = (Fahrenheit - 32) * 5 // 9\\n';
      const pyCode = [
        '"""Convert Fahrenheit to Celsius."""',
        'RISK = "read_only"',
        'def run(fahrenheit: int = 212) -> dict:',
        '    return {"celsius": (int(fahrenheit) - 32) * 5 // 9}',
      ].join('\\n');

      await send(
        page,
        `Step 1: call skill_view with skill_id "capability-authoring". ` +
          `Step 2: call write_skill_file with skill_id "${SKILL_PURE}", path "SKILL.md", and content "${skillMd}". ` +
          `Step 3: call write_skill_file with skill_id "${SKILL_PURE}", path "references/formulas.md", and content "${refMd}". ` +
          `Step 4: call write_skill_file with skill_id "${SKILL_PURE}", path "tools/${TOOL_PURE}.py", and content "${pyCode}". ` +
          `Confirm when all three files are written.`
      );
      await waitReplyIdle(page, { timeoutMs: 240000 });

      const threadText = await page.locator('#chatMessages').innerText().catch(() => '');
      if (threadText.includes('The model returned an empty reply')) {
        throw new Error(`Chat showed empty reply error after authoring ${SKILL_PURE}`);
      }

      const tree = await getJson(request, `${base}/api/capabilities/tree`);
      const pureSkill = (tree.skills || []).find((s) => (s.id || s.skill_id) === SKILL_PURE);
      if (!pureSkill) {
        throw new Error(`Expected ${SKILL_PURE} in /api/capabilities/tree after write_skill_file`);
      }
      const tools = pureSkill.colocated_tools || (pureSkill.files && pureSkill.files.tools) || [];
      const pureTool = tools.find((t) => t.name === TOOL_PURE);
      if (!pureTool || !pureTool.enabled) {
        throw new Error(`Expected ${TOOL_PURE} to be auto-enabled in ${SKILL_PURE}, got: ${JSON.stringify(tools)}`);
      }
      j.note(`AutoReiv authored ${SKILL_PURE} (SKILL.md + references/formulas.md + tools/${TOOL_PURE}.py) and auto-enabled ${TOOL_PURE}`);
    }, { timeoutMs: 260000 });

    await j.step('In Chat, AutoReiv authors second Agora skill folder dogfood-net-probe (SKILL.md, network tools/probe_url.py) saved disabled for approval', async () => {
      await ensureChatOpen(page);

      const netSkillMd = [
        '---',
        'name: Dogfood Net Probe',
        'description: Probe remote URLs over the network.',
        '---',
        '# Dogfood Net Probe',
        'Use probe_url(url=...) after operator approval.',
      ].join('\\n');
      const netPyCode = [
        '"""Probe a URL over network."""',
        'import urllib.request',
        'def run(url: str = "https://example.com") -> dict:',
        '    return {"probed": url}',
      ].join('\\n');

      await send(
        page,
        `Call write_skill_file twice for skill_id "${SKILL_NET}": ` +
          `first with path "SKILL.md" and content "${netSkillMd}", ` +
          `second with path "tools/${TOOL_NET}.py" and content "${netPyCode}". ` +
          `Then summarize the tool status.`
      );
      await waitReplyIdle(page, { timeoutMs: 240000 });

      const threadText = await page.locator('#chatMessages').innerText().catch(() => '');
      if (threadText.includes('The model returned an empty reply')) {
        throw new Error(`Chat showed empty reply error after authoring ${SKILL_NET}`);
      }

      const tree = await getJson(request, `${base}/api/capabilities/tree`);
      const netSkill = (tree.skills || []).find((s) => (s.id || s.skill_id) === SKILL_NET);
      if (!netSkill) {
        throw new Error(`Expected ${SKILL_NET} in /api/capabilities/tree after write_skill_file`);
      }
      const tools = netSkill.colocated_tools || (netSkill.files && netSkill.files.tools) || [];
      const netTool = tools.find((t) => t.name === TOOL_NET);
      if (!netTool || netTool.enabled) {
        throw new Error(`Expected network tool ${TOOL_NET} to be saved disabled, got: ${JSON.stringify(tools)}`);
      }
      j.note(`AutoReiv authored ${SKILL_NET}/tools/${TOOL_NET}.py; saved disabled pending approval with no empty-reply error`);
    }, { timeoutMs: 260000 });

    await j.step('Inspect both Agora skill folders in #view-capabilities and enable probe_url', async () => {
      if (!(await page.locator('#view-capabilities').isVisible().catch(() => false))) {
        const dockBtn = page.locator('#dock-capabilities');
        if (await dockBtn.isVisible().catch(() => false)) {
          await dockBtn.click();
        } else {
          await page.locator('#tab-capabilities').click();
        }
      }
      await page.locator('#view-capabilities').waitFor({ state: 'visible', timeout: 20000 });
      await page.locator('#capabilitiesRefreshBtn').click();

      const search = page.locator('#capabilitiesTreeSearch');
      await search.waitFor({ state: 'visible', timeout: 15000 });
      await search.fill('dogfood-');
      await search.dispatchEvent('input');

      const bothVisible = await waitFor(
        async () => {
          const text = await page.locator('#capabilitiesTreeList').innerText().catch(() => '');
          return (
            text.includes(`${SKILL_PURE}/`) &&
            text.includes('formulas.md') &&
            text.includes(`${TOOL_PURE}.py`) &&
            text.includes(`${SKILL_NET}/`) &&
            text.includes(`${TOOL_NET}.py`)
          );
        },
        { timeoutMs: 15000 }
      );
      if (!bothVisible) {
        const actual = await page.locator('#capabilitiesTreeList').innerText().catch(() => '');
        throw new Error(`Expected both ${SKILL_PURE} and ${SKILL_NET} in #capabilitiesTreeList, got: ${actual}`);
      }

      const netToolBtn = page.locator(
        `#capabilitiesTreeList [data-skill-id="${SKILL_NET}"][data-skill-file="tools/${TOOL_NET}.py"]`
      );
      await netToolBtn.scrollIntoViewIfNeeded();
      await netToolBtn.click();

      const statusCard = page.locator('#capabilitiesToolStatusCard');
      await statusCard.waitFor({ state: 'visible', timeout: 10000 });
      const cardReady = await waitFor(
        async () => {
          const txt = await statusCard.innerText().catch(() => '');
          return txt.includes('Disabled (needs approval)') && txt.includes('network');
        },
        { timeoutMs: 10000 }
      );
      if (!cardReady) {
        throw new Error(`Expected ${TOOL_NET} status card to show Disabled (needs approval) and network`);
      }

      const toggleBtn = page.locator('#capabilitiesToggleToolBtn');
      await toggleBtn.scrollIntoViewIfNeeded();
      await clickExpect(
        toggleBtn,
        async () => {
          const tree = await getJson(request, `${base}/api/capabilities/tree`);
          const entry = (tree.skills || []).find((s) => (s.id || s.skill_id) === SKILL_NET);
          const tools = (entry && (entry.colocated_tools || (entry.files && entry.files.tools))) || [];
          const tool = tools.find((t) => t.name === TOOL_NET);
          return Boolean(tool && tool.enabled);
        },
        { label: 'Enable Tool', what: `${TOOL_NET} enabled in Capabilities Studio`, timeoutMs: 15000 }
      );
      j.note(`Verified ${SKILL_PURE} and ${SKILL_NET} in #view-capabilities and approved ${TOOL_NET}`);
    });

    await j.step('In Chat, AutoReiv mounts dogfood-unit-math via skill_view and executes f_to_c(fahrenheit=212)', async () => {
      await ensureChatOpen(page);

      await send(
        page,
        `First call skill_view with skill_id "${SKILL_PURE}". Then call ${TOOL_PURE} with fahrenheit=212 and report the celsius value.`
      );
      await waitReplyIdle(page, { timeoutMs: 240000 });

      const sessions = await getJson(request, `${base}/api/sessions?agent_id=${AGENT_ID}`);
      const latest = (sessions.sessions || sessions || [])[0];
      if (!latest || !latest.id) throw new Error('No chat session found for AutoReiv');
      const msgs = await getJson(request, `${base}/api/sessions/${encodeURIComponent(latest.id)}/messages`);
      const rows = Array.isArray(msgs) ? msgs : (msgs.messages || []);
      const toolNames = rows.filter((m) => m.role === 'tool').map((m) => m.name);
      if (!toolNames.includes(TOOL_PURE)) {
        throw new Error(`Expected ${TOOL_PURE} in executed session tools, got: ${JSON.stringify(toolNames)}`);
      }
      j.note(`AutoReiv mounted ${SKILL_PURE} and executed ${TOOL_PURE}(fahrenheit=212) -> 100C`);
    }, { timeoutMs: 260000 });

    await j.step('Clean up temporary dogfood Agora skill folders', async () => {
      fs.rmSync(path.join(skillsRoot, SKILL_PURE), { recursive: true, force: true });
      fs.rmSync(path.join(skillsRoot, SKILL_NET), { recursive: true, force: true });
    });
  },
};
