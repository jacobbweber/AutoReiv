/**
 * CARD-745: Proof journey for Docker- and host-aware MCP engineering, container deployment, and immediate session mounting.
 *
 * Verifies on desktop and phone that:
 * 1. AutoReiv opens mcp-engineering via skill_view, scaffolds a FastMCP server (host_fs_mcp) into
 *    $AUTOREIV_PROJECTS_DIR/host_fs_mcp with custom tool code, and validates it with test_mcp_server.
 * 2. AutoReiv deploys host_fs_mcp as a Docker container with a host bind-mount volume via deploy_mcp_container,
 *    registers it with register_mcp_service (which auto-activates mcp-host_fs_mcp in the session), and calls
 *    mcp_host_fs_mcp_list_host_dir in the same turn.
 * 3. host_fs_mcp is persisted in /api/settings/mcp and its companion skill is visible in Capabilities Studio.
 */

import fs from 'node:fs';
import path from 'node:path';
import { askAndApprove, getJson, openApp, openTab, trackStreams } from './lib/app.mjs';

const AGENT_ID = 'autoreiv';

function resolveProjectsRoot() {
  const dataDir = process.env.AUTOREIV_DATA_DIR || path.resolve(process.cwd(), 'scratch', 'live_qa_data');
  return path.join(dataDir, 'projects');
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
  id: 'card-745-docker-aware-mcp-engineering-and-host',
  card: 'CARD-745',
  title: 'Make MCP engineering Docker-aware and support host/Docker MCP container deployment',
  allow: [],
  async run(j, { page, request, base }) {
    const projectDir = path.join(resolveProjectsRoot(), 'host_fs_mcp');

    await j.step('In Chat, AutoReiv opens mcp-engineering, scaffolds host_fs_mcp into projects dir, and tests it', async () => {
      await openApp(page, base);
      await ensureChatOpen(page);
      const putMode = await request.put(`${base}/api/settings/approval-mode`, {
        data: { approval_mode: 'hands_off' },
      });
      if (!putMode.ok()) {
        throw new Error(`PUT /api/settings/approval-mode HTTP ${putMode.status()}`);
      }

      const streams = trackStreams(page);
      const prompt1 = [
        'Keep thinking minimal and execute these 3 tool calls in order.',
        'Notes for this work (not separate asks):',
        '- Call skill_view with skill_id="mcp-engineering".',
        '- Call scaffold_mcp_server with name="host_fs_mcp", description="Host directory inspector", and tools_spec=[{"name": "list_host_dir", "description": "List files in the mounted host directory", "parameters": {"type": "object", "properties": {"subdir": {"type": "string", "description": "Optional subdirectory"}}, "required": []}, "code": "target = Path(\'/host_platform\') if Path(\'/host_platform\').is_dir() else Path(\'/app\')\\nreturn \', \'.join(sorted(p.name for p in target.iterdir()))"}].',
        '- Call test_mcp_server with project_path set to the project_path returned by scaffold_mcp_server and test_tool="list_host_dir", then reply with the project_path.',
      ].join('\n');

      await askAndApprove(
        page,
        streams,
        prompt1,
        async () => fs.existsSync(path.join(projectDir, 'server.py')),
        220000,
        { onApprove: (lbl) => j.note(`Approved HITL card: ${lbl}`) },
      );

      if (!fs.existsSync(path.join(projectDir, 'server.py'))) {
        throw new Error(`Expected scaffolded server.py at ${path.join(projectDir, 'server.py')}`);
      }
      j.note(`Scaffolded and verified host_fs_mcp at ${projectDir}`);
    }, { timeoutMs: 240000 });

    await j.step('In Chat, AutoReiv deploys host_fs_mcp in Docker with host volume, registers it, and calls list_host_dir', async () => {
      await ensureChatOpen(page);
      const streams = trackStreams(page);

      const prompt2 = [
        `Keep thinking minimal and execute these 3 tool calls in order for project_path="${projectDir}".`,
        'Notes for this work (not separate asks):',
        `- Call deploy_mcp_container with project_path="${projectDir}", port=8766, and volumes=["/home/spark/autoreiv/platform:/host_platform:ro"].`,
        '- Call register_mcp_service with name="host_fs_mcp", transport="sse" (or the transport returned by deploy_mcp_container), url_or_command set to the url (or command) returned by deploy_mcp_container, sample_tool="list_host_dir", and sample_arguments={}.',
        '- Call mcp_host_fs_mcp_list_host_dir with {} and state the directory entries it returned.',
      ].join('\n');

      await askAndApprove(
        page,
        streams,
        prompt2,
        async () => {
          const mcpData = await getJson(request, `${base}/api/settings/mcp`).catch(() => ({}));
          const servers = mcpData?.servers || mcpData || [];
          const registered = Array.isArray(servers) && servers.some((s) => s.name === 'host_fs_mcp');
          if (!registered) return false;
          const sessions = await getJson(request, `${base}/api/sessions?agent_id=${AGENT_ID}`).catch(() => ({}));
          const latest = (sessions.sessions || sessions || [])[0];
          if (!latest?.id) return false;
          const msgs = await getJson(request, `${base}/api/sessions/${encodeURIComponent(latest.id)}/messages`).catch(() => []);
          const rows = Array.isArray(msgs) ? msgs : (msgs.messages || []);
          return rows.some((m) => m.role === 'tool' && m.name === 'mcp_host_fs_mcp_list_host_dir');
        },
        240000,
        { onApprove: (lbl) => j.note(`Approved HITL card: ${lbl}`) },
      );

      const sessions = await getJson(request, `${base}/api/sessions?agent_id=${AGENT_ID}`);
      const latest = (sessions.sessions || sessions || [])[0];
      if (!latest?.id) throw new Error('No chat session found for AutoReiv');
      const msgs = await getJson(request, `${base}/api/sessions/${encodeURIComponent(latest.id)}/messages`);
      const rows = Array.isArray(msgs) ? msgs : (msgs.messages || []);
      const toolRow = rows.find((m) => m.role === 'tool' && m.name === 'mcp_host_fs_mcp_list_host_dir');
      if (!toolRow) {
        const names = rows.filter((m) => m.role === 'tool').map((m) => m.name);
        throw new Error(`Expected mcp_host_fs_mcp_list_host_dir tool call in session, got: ${JSON.stringify(names)}`);
      }
      const toolOut = String(toolRow.content || '');
      if (!toolOut.includes('agents') || !toolOut.includes('skills')) {
        throw new Error(`Expected mcp_host_fs_mcp_list_host_dir output to include 'agents' and 'skills', got: ${toolOut}`);
      }
      j.note('Deployed mcp-host_fs_mcp container, registered service, and listed host directory entries (agents, skills)');
    }, { timeoutMs: 260000 });

    await j.step('Verify host_fs_mcp is registered in canonical MCP store and visible in Capabilities Studio', async () => {
      const mcpData = await getJson(request, `${base}/api/settings/mcp`);
      const servers = mcpData?.servers || mcpData || [];
      const found = Array.isArray(servers) && servers.some((s) => s.name === 'host_fs_mcp');
      if (!found) {
        throw new Error(`Expected host_fs_mcp in /api/settings/mcp, got ${JSON.stringify(servers)}`);
      }

      await openTab(page, 'capabilities');
      await page.locator('#view-capabilities').waitFor({ state: 'visible', timeout: 15000 });
      await page.waitForTimeout(800);
      const capText = await page.locator('#view-capabilities').innerText();
      if (!capText.toLowerCase().includes('host_fs_mcp') && !capText.toLowerCase().includes('host fs mcp')) {
        throw new Error('Expected host_fs_mcp capability in Capabilities Studio');
      }
      j.note('Verified host_fs_mcp in /api/settings/mcp and Capabilities Studio');
    });
  },
};
