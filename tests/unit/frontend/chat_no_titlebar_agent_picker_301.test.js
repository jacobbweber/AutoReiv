import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('CARD-301 Chat has no desktop titlebar agent picker', () => {
  const desktopJs = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/static/modules/ui/agent-desktop.js'),
    'utf-8',
  );
  const indexHtml = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/templates/index.html'),
    'utf-8',
  );

  it('keeps a single #agentSelect in Chat markup', () => {
    const matches = indexHtml.match(/id="agentSelect"/g) || [];
    expect(matches).toHaveLength(1);
    expect(indexHtml).not.toContain('id="chatTopBarAgentSelect"');
  });

  it('does not create desktop-win-agent-select elements', () => {
    expect(desktopJs).not.toMatch(/createElement\(['"]select['"]\)/);
    expect(desktopJs).not.toMatch(/className\s*=\s*['"]desktop-win-agent-select['"]/);
    expect(desktopJs).toMatch(/never inject a second Chat agent picker/);
  });
});
