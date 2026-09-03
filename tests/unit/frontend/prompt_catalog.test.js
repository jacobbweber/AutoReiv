import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('Prompt Catalog & Saved Prompts Manager [CARD-147]', () => {
  let html;

  beforeEach(() => {
    html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  });

  it('includes prompt catalog trigger button in chat options drawer [REQ-PROMPT-003]', () => {
    expect(html).toContain('id="chatPromptsBtn"');
    expect(html).toContain('Prompt Catalog');
  });

  it('provides accessible prompt catalog modal structure [REQ-PROMPT-003]', () => {
    expect(html).toContain('id="promptCatalogModal"');
    expect(html).toContain('id="promptCatalogModalTitle"');
    expect(html).toContain('id="closePromptCatalogModalBtn"');
  });

  it('provides search input and category filter pills [REQ-PROMPT-003]', () => {
    expect(html).toContain('id="promptCatalogSearch"');
    expect(html).toContain('id="promptCategoryFilterPills"');
    expect(html).toContain('data-category="all"');
    expect(html).toContain('data-category="system"');
    expect(html).toContain('data-category="productivity"');
    expect(html).toContain('data-category="coding"');
    expect(html).toContain('data-category="analysis"');
  });

  it('provides prompt creation form and catalog cards list [REQ-PROMPT-003, REQ-PROMPT-004]', () => {
    expect(html).toContain('id="promptCatalogList"');
    expect(html).toContain('id="promptCatalogNewBtn"');
    expect(html).toContain('id="promptCatalogForm"');
    expect(html).toContain('id="promptFormTitle"');
    expect(html).toContain('id="promptFormTemplateText"');
  });
});
