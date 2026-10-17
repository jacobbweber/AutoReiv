/**
 * CARD-693 / ADR-0066: Retire Architect, Developer, and Toolsmith agents and consolidate
 * their 18 micro-skills into 3 Agora skill folders on AutoReiv.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { bindStudioAgentPickers } from '../../../src/web/static/modules/studios/agent_picker.js';

const repoRoot = path.resolve(__dirname, '../../..');

function createSelect(id, initialValue = '') {
  const options = [];
  const el = {
    id,
    dataset: {},
    options,
    _value: initialValue,
    appendChild(opt) { options.push(opt); },
    addEventListener() {},
    get value() { return this._value; },
    set value(v) { this._value = v == null ? '' : String(v); },
  };
  Object.defineProperty(el, 'innerHTML', { configurable: true, get: () => '', set: () => { options.length = 0; } });
  return el;
}

describe('CARD-693 Three-Agent Roster & Agora Skill Consolidation', () => {
  it('ships only autoreiv.md, tutor.md, and direct.md in platform/agents/', () => {
    const agentsDir = path.join(repoRoot, 'platform', 'agents');
    const files = fs.readdirSync(agentsDir).filter((f) => f.endsWith('.md')).sort();
    expect(files).toEqual(['autoreiv.md', 'direct.md', 'tutor.md']);
  });

  it('populates Chat and Agent Studio pickers with the 3-agent shipped roster', () => {
    const selects = {
      agentSelect: createSelect('agentSelect', ''),
      forgeAgentSelect: createSelect('forgeAgentSelect', ''),
    };
    const fakeDoc = {
      getElementById: (id) => selects[id] || null,
      createElement: () => ({ value: '', textContent: '' }),
    };
    const prevDoc = globalThis.document;
    globalThis.document = fakeDoc;
    try {
      const shippedRoster = [
        { id: 'autoreiv', name: 'AutoReiv', show_in_chat: true },
        { id: 'tutor', name: 'Tutor', show_in_chat: true },
        { id: 'direct', name: 'Direct', show_in_chat: true },
      ];
      const state = { selectedAgentId: 'autoreiv' };
      bindStudioAgentPickers(shippedRoster, { state, root: fakeDoc });

      const chatOpts = selects.agentSelect.options.map((o) => o.value);
      const forgeOpts = selects.forgeAgentSelect.options.map((o) => o.value);

      expect(chatOpts).toEqual(['autoreiv', 'tutor', 'direct']);
      expect(forgeOpts).toEqual(['autoreiv', 'direct', 'tutor']);
      expect(chatOpts).not.toContain('architect');
      expect(chatOpts).not.toContain('developer');
      expect(chatOpts).not.toContain('toolsmith');
    } finally {
      globalThis.document = prevDoc;
    }
  });

  it('consolidates the 18 micro-skills into 3 Agora skill folders with references/', () => {
    const skillsDir = path.join(repoRoot, 'platform', 'skills');
    const expectedFolders = [
      ['capability-authoring', 'authoring-guide.md'],
      ['project-cards', 'card-rubric.md'],
      ['software-development', 'workflow.md'],
    ];
    for (const [folder, refFile] of expectedFolders) {
      expect(fs.existsSync(path.join(skillsDir, folder, 'SKILL.md'))).toBe(true);
      expect(fs.existsSync(path.join(skillsDir, folder, 'references', refFile))).toBe(true);
    }

    const retiredFolders = [
      'agent-authoring',
      'native-tool-engineering',
      'project-orientation',
      'brainstorm',
      'card-intake',
      'card-writing',
      'plan-change',
      'hand-off',
      'review',
      'implement-change',
      'write-tests',
      'debug',
      'run-checks',
      'git-workflow',
      'code-review',
      'codebase-audit',
      'journey-qa',
    ];
    for (const retired of retiredFolders) {
      expect(fs.existsSync(path.join(skillsDir, retired))).toBe(false);
    }
  });
});
