/**
 * CARD-692: Consolidate MCP servers & deep-links into Capabilities Studio and retire Skill/Tools Studio tabs.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { DOCK_LAUNCHERS, VIEW_BY_TAB, resolveDesktopStudioTab } from '../../../src/web/static/modules/ui/agent-desktop.js';
import {
  MCP_TREE_NODE_ID,
  renderCapabilitiesTreeHtml,
} from '../../../src/web/static/modules/studios/capabilities_tree_model.js';
import {
  CAPABILITIES_STUDIO_TAB,
  planCapabilitiesStudioDeepLink,
} from '../../../src/web/static/modules/studios/capabilities_studio.js';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Capabilities Studio consolidation [CARD-692, CARD-742]', () => {
  it('retires dock-skill-studio and dock-tools-studio from DOCK_LAUNCHERS and VIEW_BY_TAB while keeping dock-capabilities', () => {
    const ids = DOCK_LAUNCHERS.map((d) => d.id);
    expect(ids).toContain('dock-capabilities');
    expect(ids).not.toContain('dock-skill-studio');
    expect(ids).not.toContain('dock-tools-studio');
    expect(VIEW_BY_TAB.capabilities).toBe('view-capabilities');
    expect(VIEW_BY_TAB['skill-studio']).toBeUndefined();
    expect(VIEW_BY_TAB['tools-studio']).toBeUndefined();
    expect(resolveDesktopStudioTab('skill-studio')).toBe('capabilities');
    expect(resolveDesktopStudioTab('tools-studio')).toBe('capabilities');
  });

  it('renders the top-level mcp/ (MCP Servers) node in the Capabilities tree', () => {
    const html = renderCapabilitiesTreeHtml(
      [
        {
          id: 'demo-skill',
          name: 'Demo Skill',
          description: 'Demo',
          source: 'user',
          references: [],
          colocated_tools: [],
          declared_tools: [],
        },
      ],
      {
        expandedSkills: new Set(),
        selectedSkillId: MCP_TREE_NODE_ID,
        selectedFilePath: '',
      },
    );
    expect(html).toContain('data-action="select-mcp-node"');
    expect(html).toContain('mcp/');
    expect(html).toContain('MCP Servers');
    expect(html).toContain('demo-skill/');
  });

  it('plans deep links for skill folders, capability gaps, and MCP servers into capabilities tab', () => {
    const skillPlan = planCapabilitiesStudioDeepLink({
      agentId: 'autoreiv',
      skillId: 'wiki-knowledge',
      filePath: 'SKILL.md',
    });
    expect(skillPlan.tab).toBe(CAPABILITIES_STUDIO_TAB);
    expect(skillPlan.mode).toBe('skill');
    expect(skillPlan.skillId).toBe('wiki-knowledge');
    expect(skillPlan.filePath).toBe('SKILL.md');

    const mcpPlan = planCapabilitiesStudioDeepLink({
      mode: 'mcp',
      scope: 'agent',
      agentId: 'developer',
    });
    expect(mcpPlan.tab).toBe(CAPABILITIES_STUDIO_TAB);
    expect(mcpPlan.mode).toBe('mcp');
    expect(mcpPlan.scope).toBe('agent');
    expect(mcpPlan.agentId).toBe('developer');

    const gapPlan = planCapabilitiesStudioDeepLink({
      agentId: 'autoreiv',
      gap: {
        missing_capability: 'convert_units',
        suggested_tool_name: 'convert_units',
        turn_text: 'Convert 10 kg to lb',
      },
    });
    expect(gapPlan.tab).toBe(CAPABILITIES_STUDIO_TAB);
    expect(gapPlan.mode).toBe('gap');
    expect(gapPlan.gap.suggested_tool_name).toBe('convert_units');
  });

  it('embeds #capabilitiesMcpPane inside #view-capabilities and deletes legacy #view-skill-studio / #view-tools-studio DOM & JS', () => {
    const html = read('src/web/templates/index.html');
    expect(html).not.toContain('id="view-skill-studio"');
    expect(html).not.toContain('id="view-tools-studio"');
    expect(fs.existsSync(path.join(repoRoot, 'src/web/static/modules/studios/skill_studio.js'))).toBe(false);
    expect(fs.existsSync(path.join(repoRoot, 'src/web/static/modules/studios/tools_studio.js'))).toBe(false);
    const start = html.indexOf('id="view-capabilities"');
    expect(start).toBeGreaterThan(-1);
    const viewHtml = html.slice(start);
    expect(viewHtml).toContain('id="capabilitiesMcpPane"');
    expect(viewHtml).toContain('id="capabilitiesMcpScopeSelect"');
    expect(viewHtml).toContain('id="capabilitiesMcpAgentSelect"');
    expect(viewHtml).toContain('id="capabilitiesMcpAddBtn"');
    expect(viewHtml).toContain('id="capabilitiesMcpSaveBtn"');
    expect(viewHtml).toContain('id="capabilitiesMcpList"');
  });
});
