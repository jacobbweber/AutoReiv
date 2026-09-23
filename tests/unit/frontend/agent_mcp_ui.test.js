/**
 * CARD-183 / CARD-421: Agent Studio shows MCP status and opens Tools Studio.
 * The full attach form lives in Tools Studio (one writer).
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Agent Studio MCP status shell [CARD-183, CARD-421]', () => {
  const indexHtml = read('src/web/templates/index.html');
  const forgeJs = read('src/web/static/modules/studios/forge.js') + read('src/web/static/modules/studios/forge/tools.js');
  const toolsJs = read('src/web/static/modules/studios/tools_studio.js')
    + read('src/web/static/modules/studios/tools_studio_catalog.js');

  it('renders status and Open in Tools Studio, not a second attach form [REQ-421-005]', () => {
    expect(indexHtml).toContain('id="forgeMcpServersCard"');
    expect(indexHtml).toContain('id="forgeMcpServerCountBadge"');
    expect(indexHtml).toContain('id="forgeOpenToolsStudioBtn"');
    expect(indexHtml).toContain('id="forgeMcpServerList"');
    expect(indexHtml).not.toContain('id="forgeAddMcpServerBtn"');
    expect(indexHtml).not.toContain('id="forgeMcpServerForm"');
    expect(indexHtml).not.toContain('id="forgeMcpSaveBtn"');
    expect(indexHtml).not.toContain('id="forgeMcpTestBtn"');
  });

  it('loads agent MCP status and leaves writes to Tools Studio [REQ-421-003]', () => {
    expect(forgeJs).toContain('loadAgentMcpServers');
    expect(forgeJs).toContain('renderAgentMcpServers');
    expect(forgeJs).toContain('forgeOpenToolsStudioBtn');
    expect(forgeJs).toContain('/api/agents/${encodeURIComponent(agentId)}/mcp');
    expect(forgeJs).not.toContain('/mcp/test');
    expect(forgeJs).not.toContain('forgeMcpSaveBtn');
    expect(toolsJs).toContain('/api/agents/${id}/mcp');
    expect(toolsJs).toContain('mcpEndpoints');
  });
});
