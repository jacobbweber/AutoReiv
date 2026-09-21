import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('CARD-306 Train keep-one + Workbench honesty', () => {
  const html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  const forge = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/forge.js'), 'utf-8')
    + fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/forge/tools.js'), 'utf-8');
  const chat = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/chat.js'), 'utf-8');
  const factory = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/factory.js'), 'utf-8');

  it('hides Chat Options Train Agent control (Factory keep-one)', () => {
    expect(html).toContain('id="trainAgentToggle"');
    expect(html).toMatch(/id="trainAgentToggle"[^>]*class="[^"]*hidden/);
    expect(html).not.toMatch(/<span class="font-medium">Train Agent<\/span>/);
    expect(html).toContain('id="trainAgentHandshakeModal"');
    expect(factory).toContain('btn-train-gap');
  });

  it('removes Train in Lab from Forge; routes to Factory', () => {
    expect(forge).not.toContain('Train in Lab');
    expect(forge).toContain('Open Training Factory');
    expect(forge).toContain('btn-open-factory-gap');
  });

  it('keeps Workbench toggle and empty honesty', () => {
    expect(html).toContain('id="workbenchToggleBtn"');
    expect(chat).toContain('function openWorkbench');
    expect(chat).toContain('/api/sessions/');
    expect(chat).toContain('/api/artifacts/');
  });
});
