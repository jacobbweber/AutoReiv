import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

/**
 * CARD-626: Recent Chats drawer must sit above the chat composer on desktop so
 * the last rows are clickable (composer was intercepting pointer events at z-20).
 */
const ROOT = path.resolve(__dirname, '../../..');
const html = fs.readFileSync(path.join(ROOT, 'src/web/templates/index.html'), 'utf-8');

function classOf(id) {
  const re = new RegExp(`id="${id}"[^>]*class="([^"]*)"`);
  const m = html.match(re);
  if (!m) throw new Error('missing #' + id);
  return m[1];
}

function zIndex(cls) {
  const m = cls.match(/\bz-(\d+)\b/);
  return m ? Number(m[1]) : null;
}

describe('CARD-626 Recent Chats drawer clears the composer', () => {
  it('chatSessionsDrawer z-index is above chatInputWrapper so last rows receive clicks', () => {
    const drawerZ = zIndex(classOf('chatSessionsDrawer'));
    const inputZ = zIndex(classOf('chatInputWrapper'));
    expect(drawerZ).not.toBeNull();
    expect(inputZ).not.toBeNull();
    expect(drawerZ).toBeGreaterThan(inputZ);
    expect(drawerZ).toBeGreaterThanOrEqual(50);
  });

  it('sessionList has bottom padding so the last row can scroll clear of the composer band', () => {
    const cls = classOf('sessionList');
    expect(cls.split(/\s+/)).toEqual(expect.arrayContaining(['pb-28']));
  });
});
