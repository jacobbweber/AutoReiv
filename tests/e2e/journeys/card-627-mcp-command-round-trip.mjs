/**
 * CARD-627: MCP command arrays with spaced args survive Disable, Enable, Test, Edit→Save.
 */
import { clickExpect, waitFor } from './lib/runner.mjs';
import { getJson, openApp } from './lib/app.mjs';

const CODE_CMD = ['python', '-c', 'import sys; print(1)'];
const WIN_CMD = ['C:\\Program Files\\AutoReivQA\\python.exe', '-c', 'print(2)'];

async function openToolsStudio(page) {
  if (!(await page.locator('#view-tools-studio').isVisible().catch(() => false))) {
    await page.locator('#dock-tools-studio').click();
  }
  await page.locator('#view-tools-studio').waitFor({ state: 'visible', timeout: 20000 });
}

async function saveServer(request, base, name, command, enabled = true) {
  const res = await request.post(base + '/api/settings/mcp', {
    data: {
      name,
      transport: 'stdio',
      command,
      url: null,
      headers: null,
      env: {},
      enabled,
    },
  });
  if (!res.ok()) throw new Error('POST /api/settings/mcp -> ' + res.status());
  return res.json();
}

async function readServer(request, base, name) {
  const list = await getJson(request, base + '/api/settings/mcp');
  const rows = Array.isArray(list) ? list : [];
  return rows.find((s) => s && s.name === name) || null;
}

export default {
  id: 'card-627-mcp-command-round-trip',
  card: 'CARD-627',
  title: 'MCP commands with spaced args survive Test/Enable/Edit',
  allow: [
    { url: '/api/settings/mcp/test', status: [200, 400, 500] },
  ],
  async run(j, { page, request, base, viewport }) {
    const tag = viewport.name + '-' + String(Date.now() % 100000);
    const codeName = 'c627-code-' + tag;
    const winName = 'c627-win-' + tag;

    await j.step('Seed two platform MCP servers with spaced command args', async () => {
      await saveServer(request, base, codeName, CODE_CMD, true);
      await saveServer(request, base, winName, WIN_CMD, true);
      const a = await readServer(request, base, codeName);
      const b = await readServer(request, base, winName);
      if (!a || JSON.stringify(a.command) !== JSON.stringify(CODE_CMD)) {
        throw new Error('code server not stored as array: ' + JSON.stringify(a && a.command));
      }
      if (!b || JSON.stringify(b.command) !== JSON.stringify(WIN_CMD)) {
        throw new Error('win server not stored as array: ' + JSON.stringify(b && b.command));
      }
    });

    await j.step('Open Tools Studio and Disable then Enable the code server', async () => {
      await openApp(page, base);
      await openToolsStudio(page);
      const row = page.locator('#toolsStudioMcpList [data-testid="tools-studio-mcp-row"][data-server-name="' + codeName + '"]');
      await row.waitFor({ state: 'visible', timeout: 20000 });
      await row.locator('[data-action="toggle"]').click();
      await waitFor(async () => {
        const s = await readServer(request, base, codeName);
        return s && s.enabled === false;
      }, { timeoutMs: 15000 });
      let s = await readServer(request, base, codeName);
      if (JSON.stringify(s.command) !== JSON.stringify(CODE_CMD)) {
        throw new Error('Disable rewrote command: ' + JSON.stringify(s.command));
      }
      await row.locator('[data-action="toggle"]').click();
      await waitFor(async () => {
        const cur = await readServer(request, base, codeName);
        return cur && cur.enabled !== false;
      }, { timeoutMs: 15000 });
      s = await readServer(request, base, codeName);
      if (JSON.stringify(s.command) !== JSON.stringify(CODE_CMD)) {
        throw new Error('Enable rewrote command: ' + JSON.stringify(s.command));
      }
    });

    await j.step('Test keeps the stored command (probe may fail; array must match)', async () => {
      const row = page.locator('#toolsStudioMcpList [data-testid="tools-studio-mcp-row"][data-server-name="' + codeName + '"]');
      const posts = [];
      page.on('request', (req) => {
        if (req.method() === 'POST' && req.url().includes('/api/settings/mcp/test')) {
          try { posts.push(req.postDataJSON()); } catch { posts.push(null); }
        }
      });
      await row.locator('[data-action="test-saved"]').click();
      await waitFor(() => posts.length > 0, { timeoutMs: 15000 });
      if (JSON.stringify(posts[0] && posts[0].command) !== JSON.stringify(CODE_CMD)) {
        throw new Error('Test body re-split command: ' + JSON.stringify(posts[0]));
      }
    });

    await j.step('Edit → Save the Program Files server keeps the path argument intact', async () => {
      const row = page.locator('#toolsStudioMcpList [data-testid="tools-studio-mcp-row"][data-server-name="' + winName + '"]');
      await row.scrollIntoViewIfNeeded();
      await row.locator('[data-action="edit"]').click();
      const commandEl = page.locator('#toolsStudioMcpCommandInput');
      await commandEl.waitFor({ state: 'visible', timeout: 10000 });
      const shown = await commandEl.inputValue();
      if (!/Program Files/i.test(shown)) {
        throw new Error('Edit form lost Program Files quoting: ' + shown);
      }
      await page.locator('#toolsStudioMcpSaveBtn').click();
      await waitFor(async () => {
        const s = await readServer(request, base, winName);
        return s && JSON.stringify(s.command) === JSON.stringify(WIN_CMD);
      }, { timeoutMs: 15000 });
      const s = await readServer(request, base, winName);
      if (JSON.stringify(s.command) !== JSON.stringify(WIN_CMD)) {
        throw new Error('Edit/Save rewrote win command: ' + JSON.stringify(s.command));
      }
    });
  },
};
