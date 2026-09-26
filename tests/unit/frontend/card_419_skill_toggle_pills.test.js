/**
 * CARD-419: Agent Studio skill scoping is toggle pills.
 * REQ-419-001..004
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  allowlistForSave,
  applySkillPillToggle,
  pillsFromPersistedAgent,
  pressedSkillIds,
  skillPillPressed,
  toggleSkillInAllowlist,
} from '../../../src/web/static/modules/studios/forge/skill_pills.js';
import { operatorSkillPillModel, skillRowHtml } from '../../../src/web/static/modules/studios/forge/runbook.js';
import { factoryAssignedSkillChrome } from '../../../src/web/static/modules/studios/factory/skill_scope.js';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

function fakePill(skillId, pressed) {
  const attrs = { 'aria-pressed': pressed ? 'true' : 'false' };
  return {
    dataset: { skillId },
    getAttribute: (key) => attrs[key] ?? null,
    setAttribute: (key, value) => { attrs[key] = value; },
  };
}

describe('Agent Studio skill toggle pills [CARD-419]', () => {
  const html = read('src/web/templates/index.html');
  const runbook = read('src/web/static/modules/studios/forge/runbook.js');
  const forge = read('src/web/static/modules/studios/forge.js');
  const skillScope = read('src/web/static/modules/studios/factory/skill_scope.js');

  it('presents skill scoping as toggle pills, not a skill editor [REQ-419-001]', () => {
    const row = skillRowHtml({
      id: 'wiki-knowledge',
      name: 'Wiki Knowledge',
      description: 'Read and file wiki notes',
      tools: ['wiki_note_read'],
    }, 'platform', false);

    expect(row).toContain('forge-skill-pill');
    expect(row).toContain('role="switch"');
    expect(row).toContain('data-testid="forge-skill-pill"');
    expect(row).toContain('data-skill-id="wiki-knowledge"');
    expect(row).toContain('aria-pressed="false"');
    expect(row).not.toContain('forge-skill-checkbox');
    expect(row).not.toContain('type="checkbox"');
    expect(row).not.toContain('studio-runbook-open-btn');
    expect(row).not.toContain('>Inspect<');
    expect(row).toContain('forge-skill-open-studio');
    expect(row).toContain('Open in Skill Studio');
    expect(row).toContain('declared tool');

    const archived = skillRowHtml({ id: 'old-skill', name: 'Old' }, 'archived', true);
    expect(archived).not.toContain('role="switch"');
    expect(archived).not.toContain('forge-skill-pill');

    expect(html).toContain('id="forgeSkillsSection"');
    expect(html).toContain('data-testid="forge-skill-scope"');
    expect(html).not.toContain('id="studioRunbookEditor"');
    expect(html).not.toContain('studio-runbook-open-btn');
    expect(runbook).not.toContain('forge-skill-checkbox');
    expect(runbook).not.toContain('studio-runbook-open-btn');
    expect(runbook).not.toContain('openRunbookEditor');
    expect(runbook).toContain('Open in Skill Studio');
    expect(forge).not.toContain('forge-skill-checkbox');
    expect(forge).not.toContain('openRunbookEditor');
  });

  it('toggle updates the allowlist payload and does not open an editor [REQ-419-002, REQ-419-003]', () => {
    const turnedOn = toggleSkillInAllowlist(['wiki'], 'sandbox');
    expect(turnedOn.action).toBe('toggle-allowlist');
    expect(turnedOn.opensEditor).toBe(false);
    expect(turnedOn.opensSkillStudio).toBe(false);
    expect(turnedOn.opensRunbook).toBe(false);
    expect(turnedOn.pressed).toBe(true);
    expect(turnedOn.allowed_skill).toEqual(['wiki', 'sandbox']);

    const turnedOff = toggleSkillInAllowlist(turnedOn.allowed_skill, 'wiki');
    expect(turnedOff.pressed).toBe(false);
    expect(turnedOff.allowed_skill).toEqual(['sandbox']);
    expect(turnedOff.opensEditor).toBe(false);

    const opened = [];
    const toggled = [];
    const pill = fakePill('sandbox', false);
    const click = applySkillPillToggle(pill, {
      onToggleSkill: (id, on) => toggled.push([id, on]),
      onOpenRunbook: () => opened.push('runbook'),
      onOpenSkillStudio: () => opened.push('studio'),
    });
    expect(click.opensEditor).toBe(false);
    expect(click.opensSkillStudio).toBe(false);
    expect(click.opensRunbook).toBe(false);
    expect(opened).toEqual([]);
    expect(toggled).toEqual([['sandbox', true]]);
    expect(pill.getAttribute('aria-pressed')).toBe('true');

    const saved = allowlistForSave(
      pressedSkillIds([pill, fakePill('wiki', false)]),
      { storageEnabled: true },
    );
    expect(saved).toEqual(['sandbox', 'sqlite-storage']);
    expect(saved).not.toContain('wiki');

    const pillClick = runbook.slice(
      runbook.indexOf("querySelectorAll('.forge-skill-pill')"),
      runbook.indexOf("querySelectorAll('.forge-skill-open-studio')"),
    );
    expect(pillClick).toContain('applySkillPillToggle');
    expect(pillClick).not.toContain('onOpenRunbook');
    expect(pillClick).not.toContain('onOpenSkillStudio');
    expect(pillClick).not.toContain('openRunbookEditor');
    expect(forge).toContain('allowed_skill: checkedSkills');
    expect(forge).toContain('allowlistForSave');
    expect(forge).toContain('skillsForSave'); // CARD-509: wraps pressedSkillIds, keeps pill-less skills
  });

  it('refresh restores pill state from the persisted allowlist [REQ-419-004]', () => {
    const allowed = pillsFromPersistedAgent({
      allowed_skill: ['wiki', 'sandbox'],
      storage_enabled: true,
      allow_wiki_access: true,
    });
    expect(skillPillPressed(allowed, 'wiki')).toBe(true);
    expect(skillPillPressed(allowed, 'sandbox')).toBe(true);
    expect(skillPillPressed(allowed, 'sqlite-storage')).toBe(true);
    expect(skillPillPressed(allowed, 'coordination')).toBe(false);

    const wikiOff = pillsFromPersistedAgent({
      allowed_skill: ['wiki', 'sandbox'],
      allow_wiki_access: false,
    });
    expect(skillPillPressed(wikiOff, 'wiki')).toBe(false);
    expect(skillPillPressed(wikiOff, 'sandbox')).toBe(true);

    const wiki = fakePill('wiki', false);
    const sandbox = fakePill('sandbox', true);
    const ghost = fakePill('coordination', true);
    [wiki, sandbox, ghost].forEach((pill) => {
      pill.setAttribute('aria-pressed', skillPillPressed(allowed, pill.dataset.skillId) ? 'true' : 'false');
    });
    expect(pressedSkillIds([wiki, sandbox, ghost])).toEqual(['wiki', 'sandbox']);
    expect(forge).toContain('pillsFromPersistedAgent');
  });

  it('operator skill-store rows render as allowlist pills, not platform seeds', () => {
    const model = operatorSkillPillModel({
      id: 'dock-notes',
      name: 'Dock Notes',
      description: 'Notes saved from Skill Studio',
      requires_tools: ['wiki_note_read'],
    });
    expect(model.tools).toEqual(['wiki_note_read']);
    const row = skillRowHtml(model, 'operator', false);
    expect(row).toContain('forge-skill-pill');
    expect(row).toContain('data-home="operator"');
    expect(row).toContain('data-skill-id="dock-notes"');
    expect(row).toContain('Open in Skill Studio');
    expect(row).toContain('role="switch"');

    const turnedOn = toggleSkillInAllowlist(['wiki'], 'dock-notes');
    expect(turnedOn.allowed_skill).toEqual(['wiki', 'dock-notes']);
    expect(turnedOn.opensSkillStudio).toBe(false);
    const saved = allowlistForSave(turnedOn.allowed_skill, { storageEnabled: false });
    expect(saved).toContain('dock-notes');

    expect(html).toContain('id="forgeSkillsGrid"');
    expect(html).not.toContain('id="forgeOperatorBox"');
    expect(html).not.toContain('>Operator skills</h4>');

    expect(runbook).toContain('operator_skills');
    expect(runbook).toContain('renderAssignedSkills');
    expect(runbook).toContain("skillRowHtml(skill, 'operator', false)");
    expect(runbook).toContain('platformSkills = catData.platform_skills');
    expect(forge).toContain('cachedOperatorSkills');
    expect(forge).toContain('allowed_skill: checkedSkills');
  });

  it('Factory assigned skills stay display-only with a separate Skill Studio link', () => {
    const chrome = factoryAssignedSkillChrome('wiki-knowledge');
    expect(chrome.interactiveToggle).toBe(false);
    expect(chrome.linkLabel).toBe('Open in Skill Studio');
    expect(chrome.skillId).toBe('wiki-knowledge');

    expect(skillScope).toContain('interactiveToggle');
    expect(skillScope).toContain('factory-assigned-open-studio');
    expect(skillScope).not.toContain('role="switch"');
    expect(skillScope).not.toContain('forge-skill-pill');
    expect(skillScope).not.toContain('factory-skill-open-btn');
    expect(html).toContain('Turn skills on or off in Agent Studio');
    expect(html).not.toContain('Runtime scoping uses the assigned-skills list on the Factory agent brief.');
  });
});
