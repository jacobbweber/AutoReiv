import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('CARD-304 Agents Constitution + Training Optimization + collapsed', () => {
  const html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  const js = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/forge.js'), 'utf-8');

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

  it('puts Agent Training Optimization above Platform Skills with Factory button', () => {
    expect(html).toContain('Agent Training Optimization');
    expect(html).toContain('Proposed skills and tools from capability gaps');
    expect(html).not.toContain('Self-Scaffold Candidate Queue');
    const train = html.indexOf('Agent Training Optimization');
    const plat = html.indexOf('id="forgePlatformBox"');
    const caps = html.indexOf('data-section="capabilities"');
    expect(train).toBeGreaterThan(caps);
    expect(train).toBeLessThan(plat);
    expect(html).toContain('id="forgeScaffoldOpenFactoryBtn"');
    expect(js).toContain('forgeScaffoldOpenFactoryBtn');
  });
});
