import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import { isMobile } from '../../../src/web/static/modules/dom.js';

describe('CARD-384: Single Lever Audit & Shadow Function Deduplication', () => {
  beforeEach(() => {
    globalThis.window = { innerWidth: 1024 };
  });

  afterEach(() => {
    delete globalThis.window;
  });

  describe('isMobile canonical helper', () => {
    it('returns true when window.innerWidth is less than 768', () => {
      window.innerWidth = 375;
      expect(isMobile()).toBe(true);

      window.innerWidth = 767;
      expect(isMobile()).toBe(true);
    });

    it('returns false when window.innerWidth is 768 or greater', () => {
      window.innerWidth = 768;
      expect(isMobile()).toBe(false);

      window.innerWidth = 1280;
      expect(isMobile()).toBe(false);
    });
  });

  describe('Negative Assertions (Dead Shadow Functions)', () => {
    it('agent-desktop.js has no escapeHtmlLite shadow function or callers', () => {
      const filePath = path.resolve('src/web/static/modules/ui/agent-desktop.js');
      const content = fs.readFileSync(filePath, 'utf-8');
      expect(content).not.toContain('function escapeHtmlLite');
      expect(content).not.toContain('escapeHtmlLite(');
    });

    it('agent-desktop.js has no duplicate local isMobile definition', () => {
      const filePath = path.resolve('src/web/static/modules/ui/agent-desktop.js');
      const content = fs.readFileSync(filePath, 'utf-8');
      expect(content).not.toContain('function isMobile');
    });

    it('projects.js has no duplicate local escapeHtml definition', () => {
      const filePath = path.resolve('src/web/static/modules/studios/projects.js');
      const content = fs.readFileSync(filePath, 'utf-8');
      expect(content).not.toContain('function escapeHtml');
    });

    it('prompts.js has no duplicate local isMobile definition', () => {
      const filePath = path.resolve('src/web/static/modules/studios/prompts.js');
      const content = fs.readFileSync(filePath, 'utf-8');
      expect(content).not.toContain('function isMobile');
    });

    it('capabilities_studio.js and forge.js do not declare raw document.execCommand copy fallbacks', () => {
      // CARD-496 / CARD-742: factory.js and skill_studio.js are deleted; Capabilities Studio owns skills.
      const capPath = path.resolve('src/web/static/modules/studios/capabilities_studio.js');
      const forgePath = path.resolve('src/web/static/modules/studios/forge.js');
      const capContent = fs.readFileSync(capPath, 'utf-8');
      const forgeContent = fs.readFileSync(forgePath, 'utf-8');
      expect(capContent).not.toContain("document.execCommand('copy')");
      expect(forgeContent).not.toContain("document.execCommand('copy')");
    });
  });
});
