import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('CARD-304 Agents Constitution + Training Optimization + collapsed', () => {
  const html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  const js = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/forge.js'), 'utf-8') + fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/forge/scaffold.js'), 'utf-8');

  it('places Agent Constitution last under Identity', () => {
    expect(html).toContain('Agent Constitution');
    expect(html).toContain('System prompt and hard rules for this agent');
    expect(html).not.toContain('Operating Manual');
    const iden = html.indexOf('data-section="identity"');
    const pref = html.indexOf('data-section="preferences"');
    const cons = html.indexOf('Agent Constitution');
    expect(iden).toBeGreaterThan(-1);
    expect(cons).toBeGreaterThan(iden);
    expect(cons).toBeLessThan(pref);
  });

  it('defaults forge-section details collapsed', () => {
    expect(html).not.toMatch(/<details\s+open\s+class="forge-section"/);
    expect(html).toContain('class="forge-section"');
  });

  it('has no Agent Training Optimization panel or Factory button under Capabilities (CARD-496)', () => {
    expect(html).not.toContain('Agent Training Optimization');
    expect(html).not.toContain('Self-Scaffold Candidate Queue');
    expect(html).not.toContain('id="forgeScaffoldQueueCard"');
    expect(html).not.toContain('id="forgeScaffoldOpenFactoryBtn"');
    expect(js).not.toContain('forgeScaffoldOpenFactoryBtn');
    expect(html.indexOf('data-section="capabilities"')).toBeLessThan(html.indexOf('id="forgeSkillsSection"'));
  });
});
