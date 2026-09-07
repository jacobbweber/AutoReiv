import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('Wiki Structured Templates & Optional Directive UI [CARD-178]', () => {
  let jsContent;
  let htmlContent;

  beforeEach(() => {
    jsContent = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/wiki.js'), 'utf-8');
    htmlContent = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  });

  it('renders newNoteTemplateSelect dropdown in wikiNewNoteModal [REQ-WIKI-035]', () => {
    expect(htmlContent).toContain('id="newNoteTemplateSelect"');
    expect(htmlContent).toContain('None (Freeform Topic Synthesis)');
  });

  it('queries newNoteTemplateSelect in wiki.js module scope [REQ-WIKI-035]', () => {
    expect(jsContent).toContain("const newNoteTemplateSelect = $('newNoteTemplateSelect');");
  });

  it('implements loadWikiTemplates fetching /api/wiki/templates [REQ-WIKI-035]', () => {
    expect(jsContent).toContain('async function loadWikiTemplates()');
    expect(jsContent).toContain("fetch('/api/wiki/templates')");
    expect(jsContent).toContain('cachedWikiTemplates');
  });

  it('attaches change listener on newNoteTemplateSelect to prefill newNoteBodyInput [REQ-WIKI-036]', () => {
    expect(jsContent).toContain("newNoteTemplateSelect.addEventListener('change'");
    expect(jsContent).toContain("newNoteBodyInput.value = (tmpl.content || '').replace(/\\${TITLE}/g, title)");
  });

  it('forwards optional template directive in POST /api/wiki/note payload [REQ-WIKI-034]', () => {
    expect(jsContent).toContain('const template = newNoteTemplateSelect?.value || undefined;');
    expect(jsContent).toMatch(/body:\s*JSON\.stringify\(\{[^}]*template[^}]*\}\)/);
  });
});
