import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('App Shell Slim Rail and Dual-Pane Workbench Canvas [CARD-138]', () => {
  const htmlPath = path.resolve(__dirname, '../../../src/web/templates/index.html');
  const htmlContent = fs.readFileSync(htmlPath, 'utf-8');

  it('declares 52px Slim Icon Rail and surface triggers in index.html [REQ-SHELL-001]', () => {
    expect(htmlContent).toContain('id="appRail"');
    expect(htmlContent).toContain('id="railBtnChat"');
    expect(htmlContent).toContain('id="railBtnVault"');
    expect(htmlContent).toContain('id="railBtnFleet"');
    expect(htmlContent).toContain('id="railBtnSettings"');
  });

  it('declares Dual-Pane Workbench Canvas elements in index.html [REQ-SHELL-003, REQ-SHELL-004]', () => {
    expect(htmlContent).toContain('id="chatWorkbenchPane"');
    expect(htmlContent).toContain('id="workbenchArtifactTitle"');
    expect(htmlContent).toContain('id="workbenchTabPreview"');
    expect(htmlContent).toContain('id="workbenchTabRaw"');
    expect(htmlContent).toContain('id="workbenchCopyBtn"');
    expect(htmlContent).toContain('id="workbenchSaveWikiBtn"');
    expect(htmlContent).toContain('id="workbenchCloseBtn"');
    expect(htmlContent).toContain('id="workbenchContentPreview"');
    expect(htmlContent).toContain('id="workbenchContentRaw"');
  });

  it('preserves all 7 studio navigation IDs to prevent regressions [REQ-SHELL-005]', () => {
    expect(htmlContent).toContain('id="tab-chat"');
    expect(htmlContent).toContain('id="tab-routines"');
    expect(htmlContent).toContain('id="tab-observability"');
    expect(htmlContent).toContain('id="tab-agents"');
    expect(htmlContent).toContain('id="tab-settings"');
    expect(htmlContent).toContain('id="tab-wiki"');
    expect(htmlContent).toContain('id="tab-projects"');
    expect(htmlContent).toContain('id="sessionList"');
  });
});
