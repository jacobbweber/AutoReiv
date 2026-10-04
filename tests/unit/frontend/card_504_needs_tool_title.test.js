import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';

import { proposalCardTitle } from '../../../src/web/static/modules/studios/tool_escalation.js';

/**
 * CARD-504 - a needs-tool Teach proposal card names the missing tool instead of "Synthesized Skill"
 * and hides the empty runbook section (REQ-504-001..003).
 */

const ROOT = path.resolve(__dirname, '../../..');
const RENDER = path.join(ROOT, 'src/web/static/modules/studios/chat/render.js');

function fakeEl(tag = 'div') {
  const kids = {};
  const e = {
    tagName: tag.toUpperCase(), innerHTML: '', className: '', dataset: {}, style: {},
    classList: { add() {}, remove() {}, contains: () => false },
    setAttribute() {}, getAttribute: () => null, addEventListener() {},
    querySelector(sel) {
      const m = /^\.([\w-]+)$/.exec(sel);
      if (!m || !e.innerHTML.includes(m[1])) return null;
      if (!kids[sel]) { kids[sel] = fakeEl(); kids[sel].innerHTML = e.innerHTML; }
      return kids[sel];
    },
    querySelectorAll: () => [],
    appendChild(c) { (e.children = e.children || []).push(c); return c; },
  };
  return e;
}

const NEEDS_TOOL = {
  status: 'ok', needs_tool: true, target_agent_id: 'autoreiv', name: null, skill_id: null,
  plain_summary: { observed_slip: 'No live weather.', remedy: 'Add a weather tool.' },
  tool_escalation: { target_agent_id: 'autoreiv', seed_intent: 'Look up live weather', suggested_tool_name: 'get_city_weather', starter_objectives: [] },
};
const SKILL = {
  status: 'ok', needs_tool: false, target_agent_id: 'autoreiv', skill_id: 'cite-sources', name: 'Cite Sources',
  plain_summary: { observed_slip: 's', remedy: 'r' }, runbook_markdown: '---\nname: cite-sources\n---\n# Cite Sources',
};

let saved;
beforeEach(() => {
  saved = globalThis.document;
  globalThis.document = { createElement: (t) => fakeEl(t), getElementById: () => null, querySelector: () => null };
});
afterEach(() => {
  if (saved === undefined) delete globalThis.document; else globalThis.document = saved;
});

async function render(proposal) {
  const { renderSkillProposalCard } = await import('../../../src/web/static/modules/studios/chat/render.js');
  return renderSkillProposalCard(proposal, { container: fakeEl() }).innerHTML;
}

describe('CARD-504 proposalCardTitle', () => {
  it('names the missing tool on a needs-tool proposal', () => {
    expect(proposalCardTitle(NEEDS_TOOL, 'Synthesized Skill')).toBe('Needs a tool: get_city_weather');
  });
  it('says "Needs a new tool" when no tool name was given', () => {
    expect(proposalCardTitle({ ...NEEDS_TOOL, tool_escalation: { suggested_tool_name: '  ' } }, 'x')).toBe('Needs a new tool');
    expect(proposalCardTitle({ needs_tool: true }, 'x')).toBe('Needs a new tool');
  });
  it('keeps "Skill Proposal: <name>" for skill cards', () => {
    expect(proposalCardTitle(SKILL, 'Cite Sources')).toBe('Skill Proposal: Cite Sources');
  });
});

describe('CARD-504 rendered card', () => {
  it('REQ-504-001: a needs-tool card reads "Needs a tool: get_city_weather", never "Synthesized Skill"', async () => {
    const html = await render(NEEDS_TOOL);
    expect(html).toContain('Needs a tool: get_city_weather');
    expect(html).not.toContain('Synthesized Skill');
    expect(html).not.toContain('Skill Proposal:');
    expect(html).toContain('Ask Developer to build this tool');
  });

  it('escapes the tool name', async () => {
    const html = await render({ ...NEEDS_TOOL, tool_escalation: { suggested_tool_name: '<img src=x>' } });
    expect(html).toContain('Needs a tool: &lt;img src=x&gt;');
    expect(html).not.toContain('<img src=x>');
  });

  it('REQ-504-002: no runbook means no "View Raw Runbook" section', async () => {
    const html = await render(NEEDS_TOOL);
    expect(html).not.toContain('View Raw Runbook');
    expect(html).not.toContain('<details');
  });

  it('skill cards are unchanged: title and runbook section stay', async () => {
    const html = await render(SKILL);
    expect(html).toContain('Skill Proposal: Cite Sources');
    expect(html).toContain('View Raw Runbook (SKILL.md)');
    expect(html).toContain('# Cite Sources');
    expect(html).toContain('btn-adopt-skill');
  });

  it('REQ-504-003: render.js does not grow (768 split lines before CARD-504)', () => {
    expect(fs.readFileSync(RENDER, 'utf-8').split('\n').length).toBeLessThanOrEqual(768);
  });
});
