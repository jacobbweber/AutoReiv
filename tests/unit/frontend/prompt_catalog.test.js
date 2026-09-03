import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('Prompt Catalog & Prompts Studio [CARD-147, CARD-152]', () => {
  let html;

  beforeEach(() => {
    html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  });

  it('includes quick prompt trigger button in chat options drawer [REQ-PROMPT-003, REQ-PROMPT-STUDIO-004]', () => {
    expect(html).toContain('id="chatPromptsBtn"');
    expect(html).toContain('Quick Prompts');
    expect(html).toContain('id="chatPromptsQuickPicker"');
  });

  it('provides accessible Prompts Studio structure in main layout [REQ-PROMPT-STUDIO-001, REQ-PROMPT-STUDIO-002]', () => {
    expect(html).toContain('id="view-prompts"');
    expect(html).toContain('id="promptsStudio"');
    expect(html).toContain('id="navPrompts"');
  });

  it('provides search input and category filter pills in Prompts Studio [REQ-PROMPT-STUDIO-002]', () => {
    expect(html).toContain('id="promptsStudioSearch"');
    expect(html).toContain('id="promptsStudioCategoryPills"');
    expect(html).toContain('data-category="all"');
    expect(html).toContain('data-category="system"');
    expect(html).toContain('data-category="productivity"');
    expect(html).toContain('data-category="coding"');
    expect(html).toContain('data-category="analysis"');
  });

  it('provides prompt editor form and catalog cards list in Prompts Studio [REQ-PROMPT-STUDIO-002, REQ-PROMPT-STUDIO-003]', () => {
    expect(html).toContain('id="promptsStudioList"');
    expect(html).toContain('id="promptsStudioNewBtn"');
    expect(html).toContain('id="promptsStudioForm"');
    expect(html).toContain('id="promptsEditorTitle"');
    expect(html).toContain('id="promptsEditorTemplate"');
  });
});
