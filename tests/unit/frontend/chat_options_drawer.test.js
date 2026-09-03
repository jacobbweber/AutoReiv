import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('Collapsible Chat Actions Drawer [CARD-142]', () => {
  let html;

  beforeEach(() => {
    html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  });

  it('provides compact input dock with options toggle button [REQ-CHAT-DRAWER-001]', () => {
    expect(html).toContain('id="chatOptionsToggleBtn"');
    expect(html).toContain('id="chatActiveModesIndicator"');
  });

  it('includes collapsible options drawer with close button [REQ-CHAT-DRAWER-002]', () => {
    expect(html).toContain('id="chatOptionsDrawer"');
    expect(html).toContain('id="chatOptionsCloseBtn"');
  });

  it('preserves all mode toggles and workflow selector IDs [REQ-CHAT-DRAWER-004]', () => {
    expect(html).toContain('id="verifyToggle"');
    expect(html).toContain('id="goalToggle"');
    expect(html).toContain('id="approvalToggle"');
    expect(html).toContain('id="workflowPicker"');
    expect(html).toContain('id="saveAsWorkflowBtn"');
  });

  it('provides action placeholders for file attachments and prompt catalog [REQ-CHAT-DRAWER-003]', () => {
    expect(html).toContain('id="chatAttachBtnPlaceholder"');
    expect(html).toContain('id="chatPromptCatalogBtnPlaceholder"');
  });
});
