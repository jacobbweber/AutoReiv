/**
 * CARD-509: an Agent Studio Save keeps every skill that has no pill exactly as loaded (D1).
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import * as pills from '../../../src/web/static/modules/studios/forge/skill_pills.js';

const repoRoot = path.resolve(__dirname, '../../..');

function fakePill(skillId, pressed) {
  const attrs = { 'aria-pressed': pressed ? 'true' : 'false' };
  return { dataset: { skillId }, getAttribute: (key) => attrs[key] ?? null };
}

describe('CARD-509 skillsForSave', () => {
  it('keeps a loaded skill that has no pill (AutoReiv coding)', () => {
    const out = pills.skillsForSave(['wiki-inbox', 'proposals', 'coding'], [fakePill('wiki-inbox', true), fakePill('proposals', false)]);
    expect(out).toEqual(['wiki-inbox', 'coding']);
  });

  it('a pill switched off removes the skill; a pill switched on adds it', () => {
    const out = pills.skillsForSave(['a', 'b'], [fakePill('a', false), fakePill('b', true), fakePill('c', true)]);
    expect(out).toEqual(['b', 'c']);
  });

  it('with no pills at all the loaded list is saved unchanged', () => {
    expect(pills.skillsForSave(['x', 'y', 'x'], [])).toEqual(['x', 'y']);
  });

  it('forge.js Save builds the list with skillsForSave (not pressed pills only)', () => {
    const src = fs.readFileSync(path.join(repoRoot, 'src/web/static/modules/studios/forge.js'), 'utf-8');
    expect(src).toContain('skillsForSave(');
    expect(src).not.toMatch(/pillNodes\.length \? pressedSkillIds\(pillNodes\)/);
  });
});
