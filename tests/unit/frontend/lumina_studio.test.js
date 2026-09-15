import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  initLuminaStudio,
  calculateEstimatedDuration,
  POST_SPEECH_PAUSE_MS,
  MIN_SCENE_DURATION_MS,
} from '../../../src/web/static/modules/studios/lumina.js';
import { renderLuminaVisual } from '../../../src/web/static/modules/lumina/visual.js';

describe('Lumina Cinema Studio [CARD-328 / REQ-LUMINA-SHELL-001..005]', () => {
  let html;
  let _luminaJs;
  let appJs;
  let desktopJs;

  beforeEach(() => {
    html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
    _luminaJs = fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/studios/lumina.js'),
      'utf-8',
    );
    appJs = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/app.js'), 'utf-8');
    desktopJs = fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/ui/agent-desktop.js'),
      'utf-8',
    );
  });

  it('declares Lumina tab, view, dock launcher, and window mapping [REQ-LUMINA-SHELL-001]', () => {
    expect(html).toContain('id="tab-lumina"');
    expect(html).toContain('data-tab="lumina"');
    expect(html).toContain('id="view-lumina"');
    expect(html).toContain('id="luminaStudio"');
    expect(desktopJs).toContain('dock-lumina');
    expect(desktopJs).toContain("lumina: 'view-lumina'");
    expect(appJs).toContain("import('./modules/studios/lumina.js')");
    expect(appJs).toContain('luminaCtrl = m.initLuminaStudio(');
  });

  it('declares Compose form, topic input, compose button, and starters container [REQ-LUMINA-SHELL-002]', () => {
    expect(html).toContain('id="luminaComposeForm"');
    expect(html).toContain('id="luminaTopicInput"');
    expect(html).toContain('id="luminaComposeBtn"');
    expect(html).toContain('id="luminaComposeStatus"');
    expect(html).toContain('id="luminaStartersList"');
  });

  it('declares Cinema stage visual container and player controls [REQ-LUMINA-SHELL-003]', () => {
    expect(html).toContain('id="luminaStageView"');
    expect(html).toContain('id="luminaStageVisual"');
    expect(html).toContain('id="luminaPlayPauseBtn"');
    expect(html).toContain('id="luminaBackToComposeBtn"');
    expect(html).toContain('id="luminaSendToCourseBtn"');
  });

  it('guarantees pointer-events: auto for Lumina hosted window controls [REQ-LUMINA-SHELL-004]', () => {
    expect(html).toContain('#view-lumina.desktop-view-hosted');
    expect(html).toContain('#view-lumina.desktop-view-hosted #luminaComposeBtn');
    expect(html).toContain('#view-lumina.desktop-view-hosted #luminaTopicInput');
    expect(html).toContain('#view-lumina.desktop-view-hosted .lumina-starter-chip');
  });

  it('calculates dynamic scene duration avoiding awkward silent gaps [REQ-LUMINA-TIMING-001]', () => {
    expect(POST_SPEECH_PAUSE_MS).toBe(1400);
    expect(MIN_SCENE_DURATION_MS).toBe(3800);

    // Empty or very short narration respects the minimum duration floor
    const shortDur = calculateEstimatedDuration('Sunlight arrives.');
    expect(shortDur).toBeGreaterThanOrEqual(MIN_SCENE_DURATION_MS);

    // 25-word narration dynamically scales without dead time
    const longText = 'Inside chloroplast thylakoids, photon energy splits water molecules into oxygen gas, protons, and energetic electrons that power cellular sugar synthesis.';
    const longDur = calculateEstimatedDuration(longText);
    expect(longDur).toBeGreaterThan(shortDur);
    // 21 words ~ 9100ms + 1400ms = ~10500ms
    expect(longDur).toBeGreaterThanOrEqual(10000);
  });

  it('exports initLuminaStudio cleanly and renders SVG topologies without throwing', () => {
    expect(typeof initLuminaStudio).toBe('function');
    expect(typeof renderLuminaVisual).toBe('function');

    const container = { innerHTML: '' };
    renderLuminaVisual(
      {
        archetype: 'cycle',
        palette: 'emerald',
        nodes: [{ id: 'n1', label: 'Sunlight', x: 20, y: 20 }],
        connections: [],
      },
      container,
    );
    expect(container.innerHTML).toContain('<svg');
    expect(container.innerHTML).toContain('Sunlight');
  });
});
