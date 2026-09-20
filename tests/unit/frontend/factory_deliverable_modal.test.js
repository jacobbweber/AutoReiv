import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('Retirement of Tabbed HITL Promotion Deliverable Inspector [CARD-197, CARD-386]', () => {
  let html;

  beforeEach(() => {
    html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  });

  it('excises obsolete deliverable inspection modal from DOM in favor of in-place Scaffolder editor [CARD-386]', () => {
    expect(html).not.toContain('id="factoryDeliverableModal"');
    expect(html).not.toContain('id="factoryDeliverableModalTitle"');
    expect(html).not.toContain('id="closeFactoryDeliverableModalBtn"');
    expect(html).not.toContain('id="closeFactoryDeliverableFooterBtn"');
  });

  it('excises obsolete 3 deliverable inspection tabs in favor of live SKILL.md editor [CARD-386]', () => {
    expect(html).not.toContain('id="factoryTabRunbookBtn"');
    expect(html).not.toContain('id="factoryTabToolBtn"');
    expect(html).not.toContain('id="factoryTabDiffBtn"');

    expect(html).not.toContain('id="factoryTabContentRunbook"');
    expect(html).not.toContain('id="factoryTabContentTool"');
    expect(html).not.toContain('id="factoryTabContentDiff"');

    // Replaced by live in-place editor in Column 2
    expect(html).toContain('id="factorySkillMarkdownEditor"');
  });

  it('prunes Inspect Deliverables trigger with retired HITL card [CARD-386]', () => {
    expect(html).not.toContain('id="factoryInspectDeliverablesBtn"');
  });
});
