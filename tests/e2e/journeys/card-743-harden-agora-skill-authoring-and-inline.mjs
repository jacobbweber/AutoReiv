/**
 * CARD-743 journey: Harden Agora skill and tool self-authoring with on-demand mounting,
 * AST import/signature validation, and inline chat approval.
 * 1) Verifies capability-authoring and mcp-engineering are ticked on AutoReiv, and
 *    PUT /api/capabilities/skills/<id>/file rejects untyped def run(**kwargs) and
 *    hallucinated `from functions import ...` imports at the static check stage.
 * 2) In Chat, asks AutoReiv to open capability-authoring (and authoring-guide.md) via skill_view
 *    and author a file-access colocated tool (`card743-file-probe/tools/check_wiki_root.py`).
 * 3) Verifies an inline `enable_skill_tool` HITL approval card appears in Chat (#pendingHitlHost),
 *    clicks Approve inline without leaving Chat, and verifies `check_wiki_root` is enabled, mounted,
 *    and executes on the next turn.
 */
import fs from 'node:fs';
import path from 'node:path';
import { waitFor } from './lib/runner.mjs';
import { getJson, openApp, send, waitReplyIdle } from './lib/app.mjs';

const SKILL_ID = 'card743-file-probe';
const TOOL_NAME = 'check_wiki_root';
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
  id: 'card-743-harden-agora-skill-authoring-and-inline',
  card: 'CARD-743',
  title: 'Harden Agora skill and tool self-authoring with on-demand mounting, AST import/signature validation, and inline chat approval',
  allow: [],
  async run(j, { page, request, base }) {
    const skillsRoot = resolveDataSkillsDir();
    fs.rmSync(path.join(skillsRoot, SKILL_ID), { recursive: true, force: true });

    await j.step('Verify capability-authoring and mcp-engineering on AutoReiv and static rejection of untyped **kwargs and hallucinated imports', async () => {
      const ag = await getJson(request, `${base}/api/agents/${AGENT_ID}`);
      const skills = Array.isArray(ag.allowed_skill) ? ag.allowed_skill : [];
      for (const reqSkill of ['capability-authoring', 'mcp-engineering']) {
        if (!skills.includes(reqSkill)) {
          throw new Error(`Expected ${reqSkill} in AutoReiv allowed_skill, got: ${JSON.stringify(skills)}`);
        }
      }

      const kwargsRes = await request.put(`${base}/api/capabilities/skills/${SKILL_ID}/file`, {
        data: {
          path: `tools/${TOOL_NAME}.py`,
          content: '"""Bad kwargs tool."""\nfrom pathlib import Path\ndef run(**kwargs) -> dict:\n    return {"ok": True}\n',
        },
      });
      if (kwargsRes.status() !== 422) {
        throw new Error(`Expected 422 for untyped def run(**kwargs), got ${kwargsRes.status()}`);
      }
      const kwargsBody = await kwargsRes.json();
      const kwargsMsg = JSON.stringify(kwargsBody);
      if (!kwargsMsg.includes('explicit typed parameters')) {
        throw new Error(`Expected explicit typed parameters error, got: ${kwargsMsg}`);
      }

      const badImportRes = await request.put(`${base}/api/capabilities/skills/${SKILL_ID}/file`, {
        data: {
          path: `tools/${TOOL_NAME}.py`,
          content: '"""Bad import tool."""\nfrom pathlib import Path\nfrom functions import wiki_note_update\ndef run(p: str = "a") -> dict:\n    return {"ok": Path(p).name}\n',
        },
      });
      if (badImportRes.status() !== 422) {
        throw new Error(`Expected 422 for hallucinated functions import, got ${badImportRes.status()}`);
      }
      const badImportMsg = JSON.stringify(await badImportRes.json());
      if (!badImportMsg.includes("No module named 'functions'")) {
        throw new Error(`Expected No module named 'functions' error, got: ${badImportMsg}`);
      }
      j.note('Static check rejected untyped def run(**kwargs) and hallucinated `from functions import ...`');
    });

    await j.step('In Chat, AutoReiv opens capability-authoring via skill_view and authors file-access tool check_wiki_root, emitting inline enable_skill_tool approval card', async () => {
      await openApp(page, base);
      await ensureChatOpen(page);

      const skillMd = [
        '---',
        'name: Card 743 File Probe',
        'description: Check whether a wiki subdirectory exists using AUTOREIV_WIKI_PATH.',
        '---',
        '# Card 743 File Probe',
        'Use check_wiki_root(subdir=...) after operator approval.',
      ].join('\\n');

      const pyCode = [
        '"""Check wiki subdirectory existence."""',
        'import os',
        'from pathlib import Path',
        'RISK = "read_only"',
        'def run(subdir: str = "01_Notes") -> dict:',
        '    root = Path(os.environ.get("AUTOREIV_WIKI_PATH", "."))',
        '    target = root / subdir',
        '    return {"subdir": subdir, "exists": target.is_dir()}',
      ].join('\\n');

      await send(
        page,
        `Step 1: call skill_view with skill_id "capability-authoring" and reference "authoring-guide.md". ` +
          `Step 2: call write_skill_file with skill_id "${SKILL_ID}", path "SKILL.md", and content "${skillMd}". ` +
          `Step 3: call write_skill_file with skill_id "${SKILL_ID}", path "tools/${TOOL_NAME}.py", and content "${pyCode}". ` +
          `Summarize the status once both files are saved.`
      );
      await waitReplyIdle(page, { timeoutMs: 240000 });

      const enableCard = page.locator('#pendingHitlHost .hitl-approval-card', { hasText: 'enable_skill_tool' }).first();
      await waitFor(
        async () => (await enableCard.count()) > 0,
        { label: 'inline enable_skill_tool approval card', what: 'enable_skill_tool card in #pendingHitlHost', timeoutMs: 20000 }
      );

      const cardText = await enableCard.innerText();
      if (!cardText.includes('enable_skill_tool') || !cardText.includes(TOOL_NAME)) {
        throw new Error(`Expected enable_skill_tool card for ${TOOL_NAME}, got: ${cardText}`);
      }
      j.note(`Inline approval card rendered in Chat for ${SKILL_ID}/${TOOL_NAME}`);
    }, { timeoutMs: 260000 });

    await j.step('Approve enable_skill_tool inline in Chat and execute check_wiki_root on the next message', async () => {
      const enableCard = page.locator('#pendingHitlHost .hitl-approval-card', { hasText: 'enable_skill_tool' }).first();
      const approveBtn = enableCard.locator('[data-hitl-decision="APPROVED"]').first();
      await approveBtn.click();

      await waitFor(
        async () => {
          const tree = await getJson(request, `${base}/api/capabilities/tree`);
          const skill = (tree.skills || []).find((s) => (s.id || s.skill_id) === SKILL_ID);
          const tools = (skill && (skill.colocated_tools || (skill.files && skill.files.tools))) || [];
          const tool = tools.find((t) => t.name === TOOL_NAME);
          return Boolean(tool && tool.enabled && tool.mounted);
        },
        { label: 'Approve enable_skill_tool', what: `${TOOL_NAME} enabled and mounted`, timeoutMs: 20000 }
      );

      await send(
        page,
        `Now call ${TOOL_NAME} with subdir="01_Notes" and state whether it exists.`
      );
      await waitReplyIdle(page, { timeoutMs: 240000 });

      const sessions = await getJson(request, `${base}/api/sessions?agent_id=${AGENT_ID}`);
      const latest = (sessions.sessions || sessions || [])[0];
      if (!latest || !latest.id) throw new Error('No chat session found for AutoReiv');
      const msgs = await getJson(request, `${base}/api/sessions/${encodeURIComponent(latest.id)}/messages`);
      const rows = Array.isArray(msgs) ? msgs : (msgs.messages || []);
      const toolNames = rows.filter((m) => m.role === 'tool').map((m) => m.name);
      if (!toolNames.includes(TOOL_NAME)) {
        throw new Error(`Expected ${TOOL_NAME} to be called after inline approval, got: ${JSON.stringify(toolNames)}`);
      }
      j.note(`Approved ${TOOL_NAME} inline in Chat and executed ${toolNames.join(' -> ')}`);
    }, { timeoutMs: 260000 });

    await j.step('Clean up temporary skill folder', async () => {
      fs.rmSync(path.join(skillsRoot, SKILL_ID), { recursive: true, force: true });
    });
  },
};
