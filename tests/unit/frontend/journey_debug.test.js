import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('Journey Timeline & Debug Inspector DOM Contract [CARD-135, CARD-136]', () => {
  const htmlPath = path.resolve(__dirname, '../../../src/web/templates/index.html');
  const htmlContent = fs.readFileSync(htmlPath, 'utf-8');

  it('declares Journey button and drawer in index.html [CARD-135]', () => {
    expect(htmlContent).toContain('id="chatShowJourneyBtn"');
    expect(htmlContent).toContain('id="chatJourneyDrawer"');
    expect(htmlContent).toContain('id="chatJourneyContent"');
    expect(htmlContent).toContain('id="chatJourneyCloseBtn"');
  });

  it('declares Debug button, pane, and tabs in index.html [CARD-136]', () => {
    expect(htmlContent).toContain('id="chatDebugToggleBtn"');
    expect(htmlContent).toContain('id="chatDebugPane"');
    expect(htmlContent).toContain('id="chatDebugCloseBtn"');
    expect(htmlContent).toContain('id="chatDebugCopyBtn"');
    expect(htmlContent).toContain('id="chatDebugContent"');
    expect(htmlContent).toContain('id="chatDebugTabMessages"');
    expect(htmlContent).toContain('id="chatDebugTabTools"');
    expect(htmlContent).toContain('id="chatDebugTabMetrics"');
    expect(htmlContent).toContain('id="chatDebugTabSystem"');
  });
});
