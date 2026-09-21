import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('CARD-298 Wiki Studio tighten labels / Meta / Curate honesty', () => {
  const indexHtml = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/templates/index.html'),
    'utf-8',
  );
  const wikiJs =
    fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/studios/wiki.js'),
      'utf-8',
    ) +
    fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/studios/wiki/templates.js'),
      'utf-8',
    ) +
    fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/studios/wiki/note.js'),
      'utf-8',
    );

  it('names Wiki Studio as Wiki-based Document Repository', () => {
    expect(indexHtml).toMatch(/id="view-wiki"[\s\S]*?Wiki-based Document Repository/);
    expect(indexHtml).not.toMatch(/id="view-wiki"[\s\S]*?Knowledge Vault/);
  });

  it('keeps Meta toggle and drops Expand indicator chrome', () => {
    expect(indexHtml).toContain('id="wikiToggleFmBtn"');
    expect(indexHtml).toContain('id="wikiToggleFmLabel"');
    expect(indexHtml).toMatch(/id="wikiToggleFmLabel"[^>]*>Meta</);
    expect(indexHtml).not.toContain('id="fmExpandIndicator"');
    expect(wikiJs).not.toContain('fmExpandIndicator');
    expect(wikiJs).not.toMatch(/Expand ▾|Collapse ▴/);
  });

  it('labels Curate as honest rule-based graduate (not agent review theatre)', () => {
    expect(indexHtml).toContain('id="wikiCurateInboxBtn"');
    expect(indexHtml).toContain('id="wikiCurateInboxBtn"');
    expect(indexHtml).toMatch(/Graduate Inbox/);
    expect(indexHtml).toMatch(/wikiCurateInboxBtn[\s\S]{0,800}(rule-based|pass\/fail|graduate_errors|Failures stay)/i);
    expect(wikiJs).toMatch(/Graduate|rule-based|held_count|graduate_errors/i);
  });
});
