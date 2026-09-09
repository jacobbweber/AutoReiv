import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('Wiki Curation & Agent Access Control UI [CARD-173]', () => {
  let html;

  beforeEach(() => {
    html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  });

  it('renders wikiCurateInboxBtn in Wiki Studio toolbar [REQ-WIKI-011]', () => {
    expect(html).toContain('id="wikiCurateInboxBtn"');
  });

  it('governs Wiki access via platform skills grid rather than redundant single checkbox [REQ-WIKI-012]', () => {
    expect(html).not.toContain('id="forgeAllowWikiAccessCheckbox"');
    expect(html).toContain('id="forgeSkillsGrid"');
  });
});
