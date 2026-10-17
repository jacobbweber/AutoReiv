/**
 * CARD-690: Unified Capabilities directory tree studio (ADR-0065 Slice 4).
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { DOCK_LAUNCHERS, VIEW_BY_TAB } from '../../../src/web/static/modules/ui/agent-desktop.js';
import {
  CAPABILITIES_STUDIO_LABEL,
  CAPABILITIES_STUDIO_TAB,
  planCapabilitiesStudioDeepLink,
} from '../../../src/web/static/modules/studios/capabilities_studio.js';
import {
  defaultReferenceMarkdown,
  defaultSkillMarkdown,
  defaultToolPython,
  filterCapabilitiesTree,
  normalizeSkillEntry,
  renderCapabilitiesTreeHtml,
  renderToolStatusCardHtml,
} from '../../../src/web/static/modules/studios/capabilities_tree_model.js';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

const SAMPLE_SKILLS = [
  {
    id: 'agora-checksum',
    name: 'Agora Checksum',
    description: 'Compute deterministic checksums and inspect docs.',
    source: 'user',
    hidden: false,
    files: ['SKILL.md', 'references/guide.md', 'tools/calc_checksum.py', 'tools/sync_webhook.py'],
    references: [{ name: 'guide.md', path: 'references/guide.md' }],
    colocated_tools: [
      {
        name: 'calc_checksum',
        relative_path: 'tools/calc_checksum.py',
        description: 'Compute a deterministic checksum.',
        risk: 'read_only',
        access: [],
        check_status: 'passed',
        approval: 'enabled',
        enabled: true,
        parameters: {
          type: 'object',
          properties: { text: { type: 'string' } },
          required: ['text'],
        },
      },
      {
        name: 'sync_webhook',
        relative_path: 'tools/sync_webhook.py',
        description: 'Post checksum to webhook.',
        risk: 'network',
        access: ['network'],
        check_status: 'passed',
        approval: 'disabled',
        enabled: false,
        parameters: {
          type: 'object',
          properties: { url: { type: 'string' } },
          required: ['url'],
        },
      },
    ],
    declared_tools: ['read_file'],
  },
  {
    id: 'wiki-knowledge',
    name: 'Wiki Knowledge',
    description: 'Read and file wiki notes.',
    source: 'shipped',
    hidden: false,
    files: ['SKILL.md'],
    references: [],
    colocated_tools: [],
    declared_tools: ['wiki_note_read'],
  },
];

describe('Capabilities directory tree studio [CARD-690]', () => {
  it('registers Capabilities in DOCK_LAUNCHERS, VIEW_BY_TAB, and index.html', () => {
    const launcher = DOCK_LAUNCHERS.find((item) => item.tab === CAPABILITIES_STUDIO_TAB);
    expect(launcher).toBeTruthy();
    expect(launcher.id).toBe('dock-capabilities');
    expect(launcher.label).toBe(CAPABILITIES_STUDIO_LABEL);
    expect(launcher.label).toBe('Capabilities');
    expect(VIEW_BY_TAB[CAPABILITIES_STUDIO_TAB]).toBe('view-capabilities');

    const html = read('src/web/templates/index.html');
    expect(html).toContain('id="tab-capabilities"');
    expect(html).toContain('id="view-capabilities"');
    expect(html).toContain('id="capabilitiesTreePane"');
    expect(html).toContain('id="capabilitiesInspectorPane"');
    expect(html).toContain('id="capabilitiesFileEditor"');
    expect(html).toContain('id="capabilitiesSaveFileBtn"');
  });

  it('normalizes backend build_capabilities_tree skill entries', () => {
    const norm = normalizeSkillEntry(SAMPLE_SKILLS[0]);
    expect(norm.skill_id).toBe('agora-checksum');
    expect(norm.references).toEqual(['references/guide.md']);
    expect(norm.tools.map((t) => t.path)).toEqual([
      'tools/calc_checksum.py',
      'tools/sync_webhook.py',
    ]);
    expect(norm.bound_tools).toEqual(['read_file']);
  });

  it('plans deep links into a skill folder and relative file path', () => {
    const plan = planCapabilitiesStudioDeepLink({
      skillId: 'agora-checksum',
      filePath: 'tools/calc_checksum.py',
    });
    expect(plan).toMatchObject({
      tab: 'capabilities',
      label: 'Capabilities',
      skillId: 'agora-checksum',
      filePath: 'tools/calc_checksum.py',
    });
  });

  it('filters the Agora skill tree by skill id, tool name, or reference path', () => {
    expect(filterCapabilitiesTree(SAMPLE_SKILLS, '')).toHaveLength(2);
    expect(filterCapabilitiesTree(SAMPLE_SKILLS, 'checksum').map((s) => s.skill_id)).toEqual([
      'agora-checksum',
    ]);
    expect(filterCapabilitiesTree(SAMPLE_SKILLS, 'sync_webhook').map((s) => s.skill_id)).toEqual([
      'agora-checksum',
    ]);
    expect(filterCapabilitiesTree(SAMPLE_SKILLS, 'guide.md').map((s) => s.skill_id)).toEqual([
      'agora-checksum',
    ]);
    expect(filterCapabilitiesTree(SAMPLE_SKILLS, 'nonexistent')).toEqual([]);
  });

  it('renders expandable Agora folder nodes with SKILL.md, references/, and tools/', () => {
    const expanded = new Set(['agora-checksum']);
    const html = renderCapabilitiesTreeHtml(SAMPLE_SKILLS, {
      expandedSkills: expanded,
      selectedSkillId: 'agora-checksum',
      selectedFilePath: 'tools/sync_webhook.py',
    });
    expect(html).toContain('data-skill-folder="agora-checksum"');
    expect(html).toContain('data-skill-file="SKILL.md"');
    expect(html).toContain('data-skill-file="references/guide.md"');
    expect(html).toContain('data-skill-file="tools/calc_checksum.py"');
    expect(html).toContain('data-skill-file="tools/sync_webhook.py"');
    expect(html).toContain('Needs approval');
  });

  it('renders tool status card with inferred schema, access report, and enable/disable toggle', () => {
    const norm = normalizeSkillEntry(SAMPLE_SKILLS[0]);
    const disabledCard = renderToolStatusCardHtml('agora-checksum', norm.tools[1]);
    expect(disabledCard).toContain('sync_webhook');
    expect(disabledCard).toContain('network');
    expect(disabledCard).toContain('Disabled (needs approval)');
    expect(disabledCard).toContain('id="capabilitiesToggleToolBtn"');
    expect(disabledCard).toContain('Enable Tool');

    const enabledCard = renderToolStatusCardHtml('agora-checksum', norm.tools[0]);
    expect(enabledCard).toContain('calc_checksum');
    expect(enabledCard).toContain('read_only');
    expect(enabledCard).toContain('Enabled');
    expect(enabledCard).toContain('Disable Tool');
  });

  it('provides clean starter templates for new SKILL.md, reference docs, and Python tools', () => {
    expect(defaultSkillMarkdown('my-skill', 'My Skill')).toContain('name: My Skill');
    expect(defaultReferenceMarkdown('notes')).toContain('# Notes');
    expect(defaultToolPython('fetch_items')).toContain('def run(');
  });
});
