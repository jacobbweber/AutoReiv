import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('CARD-306 Train keep-one + Workbench honesty (Factory retired in CARD-496)', () => {
  const html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  const forge = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/forge.js'), 'utf-8')
    + fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/forge/tools.js'), 'utf-8');
  const chat = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/chat.js'), 'utf-8');

  it('has no Train Agent control or training popup anywhere (CARD-496)', () => {
    expect(html).not.toContain('id="trainAgentToggle"');
    expect(html).not.toContain('id="trainAgentHandshakeModal"');
    expect(html).not.toMatch(/<span class="font-medium">Train Agent<\/span>/);
  });

  it('Agent Studio gap rows route to Skill Studio or the Developer, never a Factory (CARD-496)', () => {
    expect(forge).not.toContain('Train in Lab');
    expect(forge).not.toContain('Open Training Factory');
    expect(forge).not.toContain('btn-open-factory-gap');
    expect(forge).toContain('btn-gap-open-skill-studio');
    expect(forge).toContain('btn-gap-ask-developer');
  });

  it('keeps Workbench toggle and empty honesty', () => {
    expect(html).toContain('id="workbenchToggleBtn"');
    expect(chat).toContain('function openWorkbench');
    expect(chat).toContain('/api/sessions/');
    expect(chat).toContain('/api/artifacts/');
  });
});
