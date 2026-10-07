/**
 * CARD-656: Agent Studio > Capabilities skill list is simple: each row is the skill name, a one-line
 * description and an on/off switch. Two headed groups (Enabled, Available), each sorted by name, with
 * an "N of M enabled" count, a search box and one quiet "Manage skills" link in the header.
 * Toggling still only flips the allowlist that Save sends (no behaviour change).
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  assignedSkillListHtml,
  skillListModel,
  skillCountText,
  skillMatchesSearch,
  skillRowHtml,
} from '../../../src/web/static/modules/studios/forge/runbook.js';
import { baselineSummaryHtml } from '../../../src/web/static/modules/studios/forge/tools.js';
import { toggleSkillInAllowlist, skillsForSave } from '../../../src/web/static/modules/studios/forge/skill_pills.js';

const repoRoot = path.resolve(__dirname, '../../..');
const read = (rel) => fs.readFileSync(path.join(repoRoot, rel), 'utf-8');

const PLATFORM = [
  { id: 'wiki', name: 'Wiki', description: 'Read and write the vault.', tools: [{ name: 'wiki_note_create', tier: 'required_platform' }, 'wiki_search'] },
  { id: 'clock', name: 'Clock', description: 'Time and dates.', tools: ['get_time'] },
];
const OPERATOR = [{ id: 'dock-notes', name: 'Dock Notes', description: 'Store notes.', tools: [{ name: 'dock_put' }] }];
const OWN = [{ id: 'arch-review', name: 'Architecture Review', description: 'Review designs.\nSecond line.' }];
const ARCHIVED = [{ id: 'old-skill', name: 'Old', description: 'Retired' }];

describe('Agent Studio simple skill list [CARD-656]', () => {
  it('splits skills into Enabled and Available, each sorted by name', () => {
    const model = skillListModel({
      platformSkills: PLATFORM, operatorSkills: OPERATOR, ownSkillRows: OWN, archivedSkills: ARCHIVED,
      allowed: ['wiki', 'dock-notes'],
    });
    expect(model.enabled.map((s) => s.id)).toEqual(['dock-notes', 'wiki']);
    expect(model.available.map((s) => s.id)).toEqual(['arch-review', 'clock']);
    expect(model.enabledCount).toBe(2);
    expect(model.total).toBe(4);
    expect(model.archived.map((s) => s.id)).toEqual(['old-skill']);
    expect(skillCountText(2, 4)).toBe('2 of 4 enabled');
  });

  it('a row is only name, one-line description and a switch on the right', () => {
    const row = skillRowHtml(PLATFORM[0], 'platform');
    expect(row).toContain('data-testid="forge-skill-name">Wiki<');
    expect(row).toContain('data-testid="forge-skill-desc"');
    expect(row).toContain('Read and write the vault.');
    expect(row).toContain('class="forge-skill-pill');
    expect(row).toContain('role="switch"');
    expect(row).toContain('data-skill-id="wiki"');
    // the switch comes after the text (right side)
    expect(row.indexOf('forge-skill-name')).toBeLessThan(row.indexOf('forge-skill-pill'));
    for (const noise of ['declared tool', 'wiki_note_create', 'REQUIRED', 'Open in Skill Studio', 'forge-skill-open-studio', 'forge-skill-home-label', 'Platform<', 'PLATFORM']) {
      expect(row).not.toContain(noise);
    }
    // multi-line description is one line
    const own = skillRowHtml(OWN[0], 'agent');
    expect(own).toContain('Review designs.');
    expect(own).not.toContain('Second line.');
  });

  it('the list renders headed groups with enabled first', () => {
    const html = assignedSkillListHtml({
      platformSkills: PLATFORM, operatorSkills: OPERATOR, ownSkillRows: OWN, archivedSkills: ARCHIVED,
      allowed: new Set(['clock']),
    });
    const enabledAt = html.indexOf('data-testid="forge-skill-group-enabled"');
    const availableAt = html.indexOf('data-testid="forge-skill-group-available"');
    expect(enabledAt).toBeGreaterThan(-1);
    expect(availableAt).toBeGreaterThan(enabledAt);
    expect(html).toContain('>Enabled<');
    expect(html).toContain('>Available<');
    expect(html.indexOf('data-skill-id="clock"')).toBeLessThan(availableAt);
    expect(html.indexOf('data-skill-id="arch-review"')).toBeGreaterThan(availableAt);
    expect(html).toContain('aria-pressed="true" data-skill-id="clock"');
    expect(html).not.toContain('Open in Skill Studio');
    expect(html).not.toContain('declared tool');
  });

  it('search matches name or description, case-insensitively', () => {
    expect(skillMatchesSearch(PLATFORM[0], 'VAULT')).toBe(true);
    expect(skillMatchesSearch(PLATFORM[0], 'wik')).toBe(true);
    expect(skillMatchesSearch(PLATFORM[0], 'notes')).toBe(false);
    expect(skillMatchesSearch(PLATFORM[0], '  ')).toBe(true);
  });

  it('toggles still save exactly the same allowlist', () => {
    const off = toggleSkillInAllowlist(['wiki', 'dock-notes'], 'wiki');
    expect(off.allowed_skill).toEqual(['dock-notes']);
    const pill = (id, on) => ({ dataset: { skillId: id }, getAttribute: () => (on ? 'true' : 'false') });
    expect(skillsForSave(['wiki', 'hidden-skill'], [pill('wiki', false), pill('clock', true)])).toEqual(['hidden-skill', 'clock']);
  });

  it('section header has a count, search box and one quiet Manage skills link', () => {
    const html = read('src/web/templates/index.html');
    const start = html.indexOf('id="forgeSkillsSection"');
    const section = html.slice(start, html.indexOf('forgeMcpServersCard', start));
    expect(section).toContain('data-testid="forge-skill-count"');
    expect(section).toContain('data-testid="forge-skill-search"');
    expect(section).toContain('data-testid="forge-open-skill-studio"');
    expect(section).toContain('Manage skills');
    expect(section).not.toContain('Author skill in Skill Studio');
    expect(section).not.toContain('OS BASELINE');
    expect(section).not.toContain('>SKILLS<');
  });

  it('the always-on baseline is one quiet line, not tool chips', () => {
    const line = baselineSummaryHtml();
    expect(line).toContain('Always on');
    expect(line).not.toContain('OS BASELINE');
    expect(line).not.toContain('lucide="lock"');
    expect((line.match(/<span/g) || []).length).toBeLessThanOrEqual(2);
  });
});
