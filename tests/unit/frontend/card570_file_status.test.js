import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { skillFileStatusText } from '../../../src/web/static/modules/studios/skill_studio/skill_file_status.js';
import { agentFileStatusText, skillWarningText } from '../../../src/web/static/modules/studios/forge/agent_file_status.js';

const repoRoot = path.resolve(__dirname, '../../..');

describe('CARD-570 agent and skill file status', () => {
  it('agent status says Edited only for an edited shipped agent', () => {
    expect(agentFileStatusText({ shipped: true, edited: false })).toContain('Shipped agent');
    expect(agentFileStatusText({ shipped: true, edited: true })).toContain('Edited');
    expect(agentFileStatusText({ shipped: false })).toBe('');
  });

  it('unknown tools show as a warning that grants nothing', () => {
    expect(skillWarningText({ odd: ['no_such_tool'] })).toBe('Unknown tools (they grant nothing): odd: no_such_tool');
    expect(skillWarningText({})).toBe('');
  });

  it('skill status covers shipped, edited, changed and hidden', () => {
    expect(skillFileStatusText({ shipped: true })).toBe('Shipped skill.');
    expect(skillFileStatusText({ shipped: true, edited: true })).toBe('Edited copy of a shipped skill.');
    expect(skillFileStatusText({ shipped: true, edited: true, shipped_changed: true })).toContain('shipped version changed');
    expect(skillFileStatusText({ shipped: true, hidden: true })).toContain('grants no tools');
    expect(skillFileStatusText({ shipped: false })).toBe('Your skill.');
  });

  it('Skill Studio and Agent Studio have the status hosts', () => {
    const html = fs.readFileSync(path.join(repoRoot, 'src/web/templates/index.html'), 'utf-8');
    expect(html).toContain('id="skillStudioFileStatus"');
    expect(html).toContain('id="forgeUseShippedBtn"');
  });
});
