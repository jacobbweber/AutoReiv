import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { getOrCreateToastContainer } from '../../../src/web/static/modules/ui/toast.js';

/**
 * CARD-624: toasts must sit above the desktop dock (z-index 10000) and clear its band.
 */

const ROOT = path.resolve(__dirname, '../../..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf-8');

describe('CARD-624 toast stack above dock', () => {
  it('toast.js creates a container with z-[11000] and a bottom offset above the dock', () => {
    class FakeEl {
      constructor() { this.id = ''; this.className = ''; this.attributes = {}; this.children = []; this.parentNode = null; }
      setAttribute(k, v) { this.attributes[k] = String(v); }
      getAttribute(k) { return this.attributes[k] ?? null; }
      appendChild(c) { c.parentNode = this; this.children.push(c); return c; }
    }
    const body = new FakeEl();
    const doc = {
      body,
      getElementById: (id) => body.children.find((c) => c.id === id) || null,
      createElement: () => new FakeEl(),
    };
    globalThis.document = doc;
    const c = getOrCreateToastContainer();
    expect(c.className).toContain('z-[11000]');
    expect(c.className).toMatch(/bottom-\[calc\(6rem/);
    expect(c.className).not.toMatch(/\bz-50\b/);
    expect(c.className).not.toMatch(/\bbottom-4\b/);
  });

  it('index.html #toastContainer and desktop.css keep the same above-dock contract', () => {
    const html = read('src/web/templates/index.html');
    const css = read('src/web/static/css/desktop.css');
    expect(html).toMatch(/id="toastContainer"[^>]*z-\[11000\]/);
    expect(html).toMatch(/bottom-\[calc\(6rem/);
    expect(css).toMatch(/#toastContainer\s*\{[^}]*z-index:\s*11000/s);
    expect(css).toMatch(/#toastContainer\s*\{[^}]*bottom:\s*calc\(6rem/s);
    const dock = css.match(/\.desktop-dock\s*\{[^}]*z-index:\s*(\d+)/s);
    expect(dock).not.toBeNull();
    expect(Number(dock[1])).toBeLessThan(11000);
  });
});
