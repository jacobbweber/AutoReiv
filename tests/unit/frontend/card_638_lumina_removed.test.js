/**
 * CARD-638: Lumina Studio is removed. No dock launcher, header tab, view, studio module, styles or
 * route calls remain, and a saved desktop layout that still names the Lumina window restores cleanly.
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { loadPageHtml } from './template_helper.js';
import { DOCK_LAUNCHERS, VIEW_BY_TAB } from '../../../src/web/static/modules/ui/agent-desktop.js';

const ROOT = path.resolve(__dirname, '../../..');
const STATIC = path.join(ROOT, 'src/web/static');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf8');
// "luminance" in the theme engine is a colour term, not the studio.
const LUMINA = /lumina(?!nce)/i;

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) return e.name === 'vendor' ? [] : walk(p);
    return /\.(js|mjs|css|html)$/.test(e.name) ? [p] : [];
  });
}

describe('CARD-638 Lumina Studio removed', () => {
  it('has no Lumina dock launcher or desktop view', () => {
    expect(DOCK_LAUNCHERS.map((d) => d.tab)).not.toContain('lumina');
    expect(DOCK_LAUNCHERS.map((d) => d.id)).not.toContain('dock-lumina');
    expect(Object.keys(VIEW_BY_TAB)).not.toContain('lumina');
    expect(DOCK_LAUNCHERS.map((d) => d.tab)).toContain('education');
  });

  it('page markup has no Lumina tab, view or controls', () => {
    const html = loadPageHtml();
    expect(html).not.toMatch(LUMINA);
    expect(html).toContain('id="view-education"');
  });

  it('studio module files are deleted', () => {
    expect(fs.existsSync(path.join(STATIC, 'modules/studios/lumina.js'))).toBe(false);
    expect(fs.existsSync(path.join(STATIC, 'modules/lumina'))).toBe(false);
  });

  it('no front-end file mentions Lumina or calls /api/lumina', () => {
    const hits = walk(STATIC).filter((f) => LUMINA.test(fs.readFileSync(f, 'utf8'))).map((f) => path.relative(ROOT, f));
    expect(hits).toEqual([]);
    expect(read('src/web/templates/index.html')).not.toContain('/api/lumina');
  });

  it('a saved layout naming the Lumina window is skipped on restore', () => {
    const src = read('src/web/static/modules/ui/agent-desktop.js');
    // Auto-restore only reopens tabs that still have a dock launcher.
    expect(src).toMatch(/prefs\.openWindows\.forEach\(\(tab\) => \{\s*if \(tab !== 'sessions' && launcherForTab\(tab\)\)/);
  });
});
