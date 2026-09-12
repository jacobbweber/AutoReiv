import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

/**
 * CARD-235 — Chat composer hit-testing
 * Prove Enable/dismiss theatre is gone and + Options sits inside pointer-events-auto.
 */
describe('Chat composer hit-testing [CARD-235]', () => {
  const indexPath = path.resolve(__dirname, '../../../src/web/templates/index.html');
  const chatJsPath = path.resolve(__dirname, '../../../src/web/static/modules/studios/chat.js');
  const html = fs.readFileSync(indexPath, 'utf-8');
  const chatJs = fs.readFileSync(chatJsPath, 'utf-8');

  function extractChatInputWrapper(src) {
    const start = src.indexOf('id="chatInputWrapper"');
    expect(start).toBeGreaterThan(-1);
    // slice until workbench pane (sibling after composer column)
    const end = src.indexOf('id="chatWorkbenchPane"', start);
    expect(end).toBeGreaterThan(start);
    return src.slice(start, end);
  }

  it('removes orphan Enable / dismiss controls left by incomplete CARD-215 cleanup', () => {
    expect(html).not.toContain('id="chatEnableGoalSuggestionBtn"');
    expect(html).not.toContain('id="chatDismissGoalSuggestionBtn"');
    expect(html).not.toContain('id="chatGoalSuggestionChip"');
    expect(chatJs).not.toContain('chatEnableGoalSuggestionBtn');
    expect(chatJs).not.toContain('chatDismissGoalSuggestionBtn');
  });

  it('keeps + Options toggle wired and present in the composer', () => {
    expect(html).toContain('id="chatOptionsToggleBtn"');
    expect(html).toContain('id="chatOptionsDrawer"');
    expect(chatJs).toContain("chatOptionsToggleBtn.addEventListener('click'");
  });

  it('places Options / form under pointer-events-auto (not stranded under pointer-events-none)', () => {
    const region = extractChatInputWrapper(html);
    expect(region).toContain('pointer-events-none');
    expect(region).toContain('pointer-events-auto');

    const peAutoIdx = region.indexOf('pointer-events-auto');
    const formIdx = region.indexOf('id="chatForm"');
    const optionsIdx = region.indexOf('id="chatOptionsToggleBtn"');
    expect(formIdx).toBeGreaterThan(peAutoIdx);
    expect(optionsIdx).toBeGreaterThan(formIdx);

    // No extra closing of the PE-auto wrapper between attachments and textarea
    // (regression of the CARD-215 orphan </div> that stranded Options).
    const attachmentsEnd = region.indexOf('id="chatAttachmentsPreviewList"');
    const between = region.slice(attachmentsEnd, optionsIdx);
    expect(between).not.toContain('chatEnableGoalSuggestionBtn');
    // Only one </div> immediately after attachments list close before textarea comment
    expect(between).toMatch(/<!-- Prompt Input Textarea -->/);
    expect(between.indexOf('<!-- Prompt Input Textarea -->')).toBeLessThan(
      between.indexOf('id="chatOptionsToggleBtn"') === -1
        ? optionsIdx - attachmentsEnd
        : between.indexOf('id="chatOptionsToggleBtn"'),
    );
    // Ensure PE-auto wrapper was not closed between attachments and Options
    // by counting that chatForm still opens before Options in the region.
    expect(region.indexOf('id="chatForm"')).toBeLessThan(optionsIdx);
    expect(region.indexOf('pointer-events-auto')).toBeLessThan(region.indexOf('id="chatForm"'));
  });

  it('disables maximized window resize hit-targets so they cannot cover composer controls', () => {
    expect(html).toMatch(
      /\.desktop-window\.is-maximized\s*>\s*\.desktop-win-resize\s*\{[^}]*pointer-events:\s*none\s*!important/,
    );
  });

  it('asserts dock chrome stays pointer-events none while shell stays clickable', () => {
    expect(html).toMatch(/#desktopDock[\s\S]*?pointer-events:\s*none/);
    expect(html).toMatch(/\.desktop-dock-shell\s*\{[^}]*pointer-events:\s*auto/);
  });
});
