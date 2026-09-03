import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('Prompts Studio & Lightweight Chat Quick-Picker [CARD-152]', () => {
  let html;

  beforeEach(() => {
    html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  });

  it('includes Prompts Studio tab in main sidebar navigation [REQ-PROMPT-STUDIO-001]', () => {
    expect(html).toContain('id="navPrompts"');
    expect(html).toContain('data-studio="prompts"');
  });

  it('provides Prompts Studio dual-pane container [REQ-PROMPT-STUDIO-002]', () => {
    expect(html).toContain('id="promptsStudio"');
    expect(html).toContain('id="promptsStudioList"');
    expect(html).toContain('id="promptsStudioSearch"');
    expect(html).toContain('id="promptsStudioCategoryPills"');
  });

  it('provides Prompts Studio editor pane with save, delete, and test in chat actions [REQ-PROMPT-STUDIO-002, REQ-PROMPT-STUDIO-003]', () => {
    expect(html).toContain('id="promptsStudioEditorPane"');
    expect(html).toContain('id="promptsEditorTitle"');
    expect(html).toContain('id="promptsEditorCategory"');
    expect(html).toContain('id="promptsEditorTemplate"');
    expect(html).toContain('id="promptsEditorSaveBtn"');
    expect(html).toContain('id="promptsEditorDeleteBtn"');
    expect(html).toContain('id="promptsEditorTestChatBtn"');
  });

  it('provides lightweight quick prompt picker in chat options drawer [REQ-PROMPT-STUDIO-004]', () => {
    expect(html).toContain('id="chatPromptsQuickPicker"');
    expect(html).toContain('id="chatPromptsQuickSearch"');
    expect(html).toContain('id="chatPromptsQuickList"');
  });
});
