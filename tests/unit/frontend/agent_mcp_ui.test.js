/**
 * CARD-183: Agent Studio Remote MCP Server Inspector and Configuration [REQ-MCP-AGENT-003].
 * Verifies UI controls and bindings in index.html and forge.js.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Agent Studio Remote MCP Servers UI [CARD-183]', () => {
  const indexHtml = read('src/web/templates/index.html');
  const forgeJs = read('src/web/static/modules/studios/forge.js');

  it('renders Remote MCP Servers card and modal form in index.html [REQ-MCP-AGENT-003]', () => {
    expect(indexHtml).toContain('id="forgeMcpServersCard"');
    expect(indexHtml).toContain('id="forgeMcpServerCountBadge"');
    expect(indexHtml).toContain('id="forgeAddMcpServerBtn"');
    expect(indexHtml).toContain('id="forgeMcpServerForm"');
    expect(indexHtml).toContain('id="forgeMcpNameInput"');
    expect(indexHtml).toContain('id="forgeMcpTransportSelect"');
    expect(indexHtml).toContain('id="forgeMcpUrlInput"');
    expect(indexHtml).toContain('id="forgeMcpCommandInput"');
    expect(indexHtml).toContain('id="forgeMcpHeadersInput"');
    expect(indexHtml).toContain('id="forgeMcpEnabledCheckbox"');
    expect(indexHtml).toContain('id="forgeMcpTestBtn"');
    expect(indexHtml).toContain('id="forgeMcpSaveBtn"');
    expect(indexHtml).toContain('id="forgeMcpTestResult"');
    expect(indexHtml).toContain('id="forgeMcpServerList"');
  });

  it('binds MCP elements and includes loadAgentMcpServers in forge.js [REQ-MCP-AGENT-003]', () => {
    expect(forgeJs).toContain("forgeMcpServersCard");
    expect(forgeJs).toContain("forgeMcpServerCountBadge");
    expect(forgeJs).toContain("forgeAddMcpServerBtn");
    expect(forgeJs).toContain("forgeMcpServerForm");
    expect(forgeJs).toContain("forgeMcpNameInput");
    expect(forgeJs).toContain("forgeMcpTransportSelect");
    expect(forgeJs).toContain("forgeMcpUrlInput");
    expect(forgeJs).toContain("forgeMcpSaveBtn");
    expect(forgeJs).toContain("forgeMcpTestBtn");
    expect(forgeJs).toContain("loadAgentMcpServers");
    expect(forgeJs).toContain("renderAgentMcpServers");
    expect(forgeJs).toContain("mcp_servers");
  });

  it('probes remote MCP server via API endpoint [REQ-MCP-AGENT-003]', () => {
    expect(forgeJs).toContain("/api/agents/${encodeURIComponent(agentId)}/mcp/test");
    expect(forgeJs).toContain("/api/agents/${encodeURIComponent(agentId)}/mcp");
  });
});
