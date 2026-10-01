/**
 * CARD-594: Agent Studio skill pills must not be repainted from a stale allowed set when an agent is picked
 * while the skills catalog is still loading (found by smoke TC-38 under full-suite load).
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const src = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/forge.js'), 'utf-8');

describe('CARD-594 forge pills repaint after the catalog load', () => {
  it('loadPlatformSkillsWrapper repaints with the current agent and allowed set after loading', () => {
    const start = src.indexOf('async function loadPlatformSkillsWrapper()');
    expect(start).toBeGreaterThan(-1);
    const end = src.indexOf('async function loadAgentForge(', start);
    const block = src.slice(start, end);
    expect(block).toMatch(/await loadPlatformSkills\([\s\S]*renderNestedHomesWrapper\(\);[\s\S]*return result;/);
  });

  it('renderNestedHomesWrapper reads the live lastAllowedSkills binding', () => {
    const start = src.indexOf('function renderNestedHomesWrapper()');
    const block = src.slice(start, src.indexOf('async function loadPlatformSkillsWrapper()'));
    expect(block).toContain('lastAllowedSkills,');
    expect(block).toContain('activeForgeAgent,');
  });
});
