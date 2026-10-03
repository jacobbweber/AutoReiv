/**
 * CARD-607: Agent Studio no longer advertises tools agents do not get.
 * - The OS baseline grid is exactly REQUIRED_PLATFORM_TOOLS (src/application/agent_skills/schema.py).
 * - A new agent's scaffold prompt no longer tells it to call lookup_agents / handoff_to_agent (gone since CARD-596).
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');
const read = (rel) => fs.readFileSync(path.join(repoRoot, rel), 'utf-8');


describe('CARD-607 baseline and scaffold', () => {
  it('the baseline grid lists exactly the required platform tools', async () => {
    const schema = read('src/application/agent_skills/schema.py');
    const block = schema.match(/REQUIRED_PLATFORM_TOOLS[^=]*=\s*\(([\s\S]*?)\)/)[1];
    const required = [...block.matchAll(/"([a-z_]+)"/g)].map((m) => m[1]).sort();
    const toolsJs = read('src/web/static/modules/studios/forge/tools.js');
    const grid = toolsJs.match(/const requiredPrimitives = \[([\s\S]*?)\];/)[1];
    const shown = [...grid.matchAll(/name: '([a-z_]+)'/g)].map((m) => m[1]).sort();
    expect(shown).toEqual(required);
  });

  it('the scaffold prompt names no tool the agent may not have', async () => {
    const { buildQuickScaffoldPayload } = await import('../../../src/web/static/modules/studios/forge/scaffold.js');
    const prompt = buildQuickScaffoldPayload({ id: 'garden', name: 'Garden', role: 'gardening' }).system_prompt;
    expect(prompt).not.toContain('lookup_agents');
    expect(prompt).not.toContain('handoff_to_agent');
    expect(prompt).not.toContain('Ask Developer'); // CARD-615: the kernel adds that line when a tool is missing
    expect(prompt).toContain('Call only the tools you are given');
  });
});
