import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('Dead UI Pruning Audit [CARD-369]', () => {
  let html;
  let chatJs;
  let appJs;
  let modalJs;

  beforeEach(() => {
    html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
    chatJs = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/chat.js'), 'utf-8');
    appJs = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/app.js'), 'utf-8');
    modalJs = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/ui/modal.js'), 'utf-8');
  });

  describe('Unimplemented Mermaid Zoom Inspector Pruned [REQ-PRUNE-001]', () => {
    it('does not contain #mermaidZoomModal or its controls in index.html', () => {
      expect(html).not.toContain('id="mermaidZoomModal"');
      expect(html).not.toContain('id="mermaidModalCard"');
      expect(html).not.toContain('id="mermaidModalTitle"');
      expect(html).not.toContain('id="mermaidZoomInBtn"');
      expect(html).not.toContain('id="mermaidZoomOutBtn"');
      expect(html).not.toContain('id="mermaidZoomResetBtn"');
      expect(html).not.toContain('id="mermaidFullscreenBtn"');
      expect(html).not.toContain('id="mermaidCloseModalBtn"');
      expect(html).not.toContain('id="mermaidViewport"');
      expect(html).not.toContain('id="mermaidCanvas"');
    });

    it('does not register mermaidZoomModal in app.js allModals', () => {
      expect(appJs).not.toContain("'mermaidZoomModal'");
    });

    it('does not reference #mermaidCloseModalBtn in modal.js', () => {
      expect(modalJs).not.toContain('#mermaidCloseModalBtn');
    });

    it('does not render dead mermaid-inspect-btn in chat.js', () => {
      expect(chatJs).not.toContain('mermaid-inspect-btn');
      expect(chatJs).not.toContain('openMermaidInspector');
    });
  });

  describe('Superseded Pre-Desktop Navigation Rail Pruned [REQ-PRUNE-002]', () => {
    it('does not contain #appRail or its rail buttons in index.html', () => {
      expect(html).not.toContain('id="appRail"');
      expect(html).not.toContain('id="railBtnChat"');
      expect(html).not.toContain('id="railBtnVault"');
      expect(html).not.toContain('id="railBtnFleet"');
      expect(html).not.toContain('id="railBtnFactory"');
      expect(html).not.toContain('id="railBtnSettings"');
    });

    it('does not maintain railBtns in app.js', () => {
      expect(appJs).not.toContain('railBtns');
      expect(appJs).not.toContain('updateRailSurfaces');
    });
  });

  describe('Preserves All 11 Active Studios and Functional Controls [REQ-PRUNE-004]', () => {
    it('preserves all 11 studio view sections', () => {
      const studios = [
        'view-chat',
        'view-wiki',
        'view-projects',
        'view-agents',
        'view-factory',
        'view-routines',
        'view-observability',
        'view-settings',
        'view-prompts',
        'view-education',
        'view-lumina',
      ];
      for (const studioId of studios) {
        expect(html).toContain(`id="${studioId}"`);
      }
    });

    it('preserves active form submit buttons and cross-studio bridges', () => {
      expect(html).toContain('id="promptsEditorSaveBtn"');
      expect(html).toContain('id="saveToneBtn"');
      expect(html).toContain('id="educationAmpWatchLuminaBtn"');
      expect(html).toContain('id="wikiMobileDrawerBtn"');
      expect(html).toContain('id="wikiDrawerCloseBtn"');
    });
  });
});
