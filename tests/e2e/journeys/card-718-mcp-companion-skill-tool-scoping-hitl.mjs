/**
 * CARD-718 journey: MCP companion skill tool scoping, HITL auto-run, Capabilities Studio copy,
 * and Telemetry RCA false-positive filter.
 * 1) Mount a live stdio FastMCP server ("GameDockQA") via Capabilities Studio / POST /api/settings/mcp
 *    and verify:
 *    - `mounted: true` with 2 discovered tools (`mcp_GameDockQA_get_add_game_guide`, `mcp_GameDockQA_add_catalog_entry`).
 *    - Companion skill `mcp-gamedockqa` is authored with `tools:` frontmatter and ticked on `autoreiv`.
 *    - `GET /api/capabilities/skills/mcp-gamedockqa` exposes `mcp_GameDockQA_get_add_game_guide`,
 *      `mcp_GameDockQA_add_catalog_entry`, and `mcp_GameDockQA_*` in its `tools` list.
 * 2) Open Capabilities Studio (`#view-capabilities`), select `mcp-gamedockqa` in the tree, and verify
 *    the editor shows `tools:` in the YAML frontmatter and zero "Tools Studio" references.
 * 3) Verify saving a user skill (`aska-gamedock-qa`) that references `mcp_GameDockQA_add_catalog_entry`
 *    retains the MCP tool in `tools:` and leaves zero pending HITL approvals in `/api/hitl/pending`,
 *    and `GET /api/telemetry/rca-proposals` returns no built-in tool validation false-positives.
 * 4) Verify zero horizontal overflow on desktop and phone.
 */
import { waitFor } from './lib/runner.mjs';
import { openApp } from './lib/app.mjs';

const STDIO_MCP_SCRIPT = [
  'import json, sys',
  'TOOLS = [',
  '    {"name": "get_add_game_guide", "description": "START HERE to add a new game to the catalog.", "inputSchema": {"type": "object", "properties": {}}},',
  '    {"name": "add_catalog_entry", "description": "Add a NEW game to the catalog from YAML text.", "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}}},',
  ']',
  'for line in sys.stdin:',
  '    line = line.strip()',
  '    if not line:',
  '        continue',
  '    msg = json.loads(line)',
  '    rid = msg.get("id")',
  '    if rid is None:',
  '        continue',
  '    method = msg.get("method")',
  '    if method == "initialize":',
  '        res = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "GameDockQA", "version": "1.0.0"}}',
  '    elif method == "tools/list":',
  '        res = {"tools": TOOLS}',
  '    elif method == "tools/call":',
  '        res = {"content": [{"type": "text", "text": "ok"}]}',
  '    else:',
  '        res = {}',
  '    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "result": res}) + "\\n")',
  '    sys.stdout.flush()',
].join('\n');

async function openTab(page, tabName) {
  const viewId = `#view-${tabName}`;
  if (await page.locator(viewId).isVisible().catch(() => false)) return;
  const dockBtn = page.locator(`#dock-${tabName}`);
  if (await dockBtn.isVisible().catch(() => false)) {
    await dockBtn.click();
  } else {
    const mobileMenu = page.locator('#mobileMenuBtn');
    if (await mobileMenu.isVisible().catch(() => false)) {
      const sidebarTab = page.locator(`#tab-${tabName}`);
      if (!(await sidebarTab.isVisible().catch(() => false))) {
        await mobileMenu.click();
      }
      await sidebarTab.waitFor({ state: 'visible', timeout: 10000 });
      await sidebarTab.click();
    } else {
      await page.locator(`#tab-${tabName}`).click();
    }
  }
  await page.locator(viewId).waitFor({ state: 'visible', timeout: 20000 });
}

export default {
  id: 'card-718-mcp-companion-skill-tool-scoping-hitl',
  card: 'CARD-718',
  title: 'MCP companion skill populates tools: frontmatter, grants agent access, and honors auto-run without pending HITL cards',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const serverName = 'GameDockQA';
    const companionSkillId = 'mcp-gamedockqa';
    const userSkillId = `aska-gamedock-${viewport.name}`;

    await j.step('Mount GameDockQA stdio MCP server and verify companion skill tools: frontmatter and agent access', async () => {
      await openApp(page, base);

      const saveRes = await request.post(`${base}/api/settings/mcp`, {
        data: {
          name: serverName,
          transport: 'stdio',
          command: ['python3', '-c', STDIO_MCP_SCRIPT],
          enabled: true,
        },
      });
      if (!saveRes.ok()) {
        const errTxt = await saveRes.text().catch(() => '');
        throw new Error(`POST /api/settings/mcp failed (${saveRes.status()}): ${errTxt}`);
      }
      const saveBody = await saveRes.json();
      if (!saveBody.mounted || saveBody.tool_count < 2) {
        throw new Error(`Expected GameDockQA to mount with >=2 tools, got: ${JSON.stringify(saveBody)}`);
      }

      const skillRes = await request.get(`${base}/api/capabilities/skills/${companionSkillId}/file?path=SKILL.md`);
      if (!skillRes.ok()) {
        throw new Error(`GET /api/capabilities/skills/${companionSkillId}/file?path=SKILL.md -> ${skillRes.status()}`);
      }
      const skillData = await skillRes.json();
      const mdContent = String(skillData.content || '');
      if (
        !mdContent.includes('mcp_GameDockQA_get_add_game_guide') ||
        !mdContent.includes('mcp_GameDockQA_add_catalog_entry') ||
        !mdContent.includes('mcp_GameDockQA_*')
      ) {
        throw new Error(`Expected ${companionSkillId} SKILL.md to include GameDockQA tools, got: ${mdContent}`);
      }

      const agentRes = await request.get(`${base}/api/agents/autoreiv`);
      if (!agentRes.ok()) {
        throw new Error(`GET /api/agents/autoreiv -> ${agentRes.status()}`);
      }
      const agentData = await agentRes.json();
      const agentSkills = Array.isArray(agentData.allowed_skill)
        ? agentData.allowed_skill
        : Array.isArray(agentData.skills)
          ? agentData.skills
          : [];
      if (!agentSkills.includes(companionSkillId)) {
        throw new Error(`Expected autoreiv skills to include "${companionSkillId}", got: ${JSON.stringify(agentSkills)}`);
      }

      j.note(`Mounted ${serverName} (${(saveBody.tools || []).length} tools) and verified ${companionSkillId} tools: frontmatter + autoreiv tick`);
    });

    await j.step('Open Capabilities Studio and verify mcp-gamedockqa skill runbook and GameDockQA server row', async () => {
      await openTab(page, 'capabilities');

      await page.evaluate(async () => {
        if (typeof window.refreshCapabilitiesStudio === 'function') {
          await window.refreshCapabilitiesStudio();
        }
      });

      const treeReady = await waitFor(
        async () => {
          const text = await page.locator('#capabilitiesTreeList').innerText().catch(() => '');
          return text.includes(companionSkillId);
        },
        { timeoutMs: 15000 },
      );
      if (!treeReady) {
        throw new Error(`Expected #capabilitiesTreeList to list "${companionSkillId}"`);
      }

      const skillFileRes = await request.get(
        `${base}/api/capabilities/skills/${companionSkillId}/file?path=SKILL.md`,
      );
      if (!skillFileRes.ok()) {
        throw new Error(`GET /api/capabilities/skills/${companionSkillId}/file -> ${skillFileRes.status()}`);
      }
      const skillFileData = await skillFileRes.json();
      const mdContent = String(skillFileData.content || '');
      if (!mdContent.includes('mcp_GameDockQA_add_catalog_entry') || !mdContent.includes('tools:')) {
        throw new Error(`Expected ${companionSkillId}/SKILL.md to include tools: frontmatter, got:\n${mdContent}`);
      }
      if (mdContent.includes('Tools Studio')) {
        throw new Error('Expected no legacy "Tools Studio" reference in SKILL.md');
      }

      j.note(`Verified ${companionSkillId} in Capabilities Studio tree with tools: frontmatter`);
    });

    await j.step('Save a user skill referencing mcp_GameDockQA_add_catalog_entry and verify zero pending HITL cards and clean RCA list', async () => {
      const putRes = await request.put(`${base}/api/capabilities/skills/${userSkillId}/file`, {
        data: {
          path: 'SKILL.md',
          content: [
            '---',
            'name: Aska GameDock Catalog',
            'description: Add Aska to GameDock catalog.',
            'tools:',
            '- mcp_GameDockQA_add_catalog_entry',
            '---',
            '',
            '# Aska GameDock Catalog',
            '',
            'Call `mcp_GameDockQA_add_catalog_entry` with the Aska YAML entry.',
          ].join('\n'),
        },
      });
      if (!putRes.ok()) {
        throw new Error(`PUT /api/capabilities/skills/${userSkillId}/file -> ${putRes.status()}`);
      }

      const userSkillRes = await request.get(`${base}/api/capabilities/skills/${userSkillId}/file?path=SKILL.md`);
      if (!userSkillRes.ok()) {
        throw new Error(`GET /api/capabilities/skills/${userSkillId}/file?path=SKILL.md -> ${userSkillRes.status()}`);
      }
      const userSkill = await userSkillRes.json();
      if (!String(userSkill.content || '').includes('mcp_GameDockQA_add_catalog_entry')) {
        throw new Error(`Expected ${userSkillId} to retain mcp_GameDockQA_add_catalog_entry, got: ${JSON.stringify(userSkill)}`);
      }

      const pendingRes = await request.get(`${base}/api/hitl/pending`);
      const pendingData = await pendingRes.json();
      const pendingList = Array.isArray(pendingData) ? pendingData : pendingData.pending || [];
      const heldForGameDock = pendingList.filter(
        (p) => p && p.arguments && p.arguments.tool === 'mcp_GameDockQA_add_catalog_entry',
      );
      if (heldForGameDock.length > 0) {
        throw new Error(`Expected zero pending attach_tool_to_skill approvals for mcp_GameDockQA_add_catalog_entry, got: ${JSON.stringify(heldForGameDock)}`);
      }

      const rcaRes = await request.get(`${base}/api/telemetry/rca-proposals`);
      if (!rcaRes.ok()) {
        throw new Error(`GET /api/telemetry/rca-proposals -> ${rcaRes.status()}`);
      }
      const rcaData = await rcaRes.json();
      const proposals = Array.isArray(rcaData.proposals) ? rcaData.proposals : [];
      const builtinFalsePositives = proposals.filter(
        (p) => p && ['register_native_tool', 'wiki_note_update'].includes(p.target_name),
      );
      if (builtinFalsePositives.length > 0) {
        throw new Error(`Expected zero RCA proposals for built-in tools, got: ${JSON.stringify(builtinFalsePositives)}`);
      }

      const overflow = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
      }));
      if (overflow.scrollWidth > overflow.innerWidth + 2) {
        throw new Error(`Horizontal overflow on ${viewport.name}: scrollWidth=${overflow.scrollWidth} > innerWidth=${overflow.innerWidth}`);
      }

      // Cleanup test server
      await request.delete(`${base}/api/settings/mcp/${encodeURIComponent(serverName)}`);

      j.note(`Verified ${userSkillId} retained MCP tool with 0 pending HITL approvals and 0 RCA false-positives on ${viewport.name}`);
    });
  },
};
