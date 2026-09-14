import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('CARD-299 Agents Studio create flow and collapsible sections', () => {
  const html = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/templates/index.html'),
    'utf-8',
  );
  const forgeJs = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/static/modules/studios/forge.js'),
    'utf-8',
  );

  it('keeps one New Agent path and ditches Quick Scaffold toolbar button', () => {
    expect(html).toContain('id="newAgentBtn"');
    expect(html).not.toContain('id="forgeQuickScaffoldBtn"');
    expect(html).not.toMatch(/>\s*Quick Scaffold\s*</);
  });

  it('exposes Identity / Agent Preferences / Overrides / Capabilities collapsibles', () => {
    for (const section of ['identity', 'preferences', 'overrides', 'capabilities']) {
      expect(html).toContain(`data-section="${section}"`);
    }
    expect(html).toMatch(/<summary>Identity<\/summary>/);
    expect(html).toMatch(/<summary>Agent Preferences<\/summary>/);
    expect(html).toMatch(/<summary>Overrides<\/summary>/);
    expect(html).toMatch(/<summary>Capabilities<\/summary>/);
  });

  it('labels Platform and Custom Agent Pack Skills & Tools', () => {
    expect(html).toContain('Platform Skills & Tools');
    expect(html).toContain('Custom Agent Pack Skills & Tools');
    expect(forgeJs).toContain("Custom Agent Pack Skills & Tools");
  });
});
