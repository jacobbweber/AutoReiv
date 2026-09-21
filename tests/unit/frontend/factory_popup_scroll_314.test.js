import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { loadPageHtml } from './template_helper.js';

describe('CARD-314 Factory popup scroll + full studio window', () => {
  const html = loadPageHtml();
  const factoryJs = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/static/modules/studios/factory.js'),
    'utf-8'
  );
  const desktopJs = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/static/modules/ui/agent-desktop.js'),
    'utf-8'
  );

  it('trainAgentHandshakeModal inner has max-h and body overflow-y-auto', () => {
    const modalIdx = html.indexOf('id="trainAgentHandshakeModal"');
    expect(modalIdx).toBeGreaterThan(-1);
    const slice = html.slice(modalIdx, modalIdx + 1800);
    expect(slice).toMatch(/max-h-\[90vh\]/);
    expect(slice).toMatch(/overflow-y-auto/);
    expect(slice).toContain('CARD-314: Factory train modal scrolls');
    expect(html).toMatch(/\/static\/app\.js\?v=2\.0\.\d+/);
  });

  it('Factory view is full studio chrome with min-h-0 (not toast)', () => {
    expect(html).toMatch(/id="view-factory"[^>]*min-h-0/);
    expect(html).toMatch(/id="factoryStudio"[^>]*min-h-0/);
    expect(html).toContain('CARD-314: Factory fills hosted');
    expect(html).toContain('data-card="314"');
  });

  it('openFactoryStudioForAgent still defined and opens full studio path', () => {
    expect(factoryJs).toContain('window.openFactoryStudioForAgent');
    expect(factoryJs).toMatch(/openFactoryStudioForAgent\s*=\s*\(agentId\)/);
    expect(factoryJs).toContain('callbacks.openFactoryStudio');
    expect(factoryJs).toContain('setAgentScope(agentId)');
  });

  it('desktop Factory defaultSize is a full studio window, not toast-sized', () => {
    expect(desktopJs).toMatch(/dock-factory[\s\S]*?defaultSize:\s*\{\s*w:\s*960,\s*h:\s*680\s*\}/);
    expect(desktopJs).toContain('CARD-314: Factory deep-link');
  });
});
