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

  it('renders forgeAllowWikiAccessCheckbox in Agent Studio card [REQ-WIKI-012]', () => {
    expect(html).toContain('id="forgeAllowWikiAccessCheckbox"');
  });
});
