/**
 * CARD-342 — Mobile Chat Sessions Drawer Button Portrait Visibility (TDD)
 */
import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');
const indexPath = path.join(repoRoot, 'src/web/templates/index.html');

function read(p) {
  return fs.readFileSync(p, 'utf-8');
}

describe('CARD-342 DOM contract — Mobile Chat Sessions Drawer Button Portrait Visibility', () => {
  let html;

  beforeEach(() => {
    html = read(indexPath);
  });

  it('ensures toggleSidebarBtn is visible on mobile portrait view without hidden or hidden md:flex', () => {
    expect(html).toContain('id="toggleSidebarBtn"');

    // Extract the toggleSidebarBtn element tag
    const btnMatch = html.match(/<button[^>]*id=["']toggleSidebarBtn["'][^>]*>/);
    expect(btnMatch).not.toBeNull();
    const btnTag = btnMatch[0];

    // Must NOT have 'hidden' or 'hidden md:flex' in its class list
    expect(btnTag).not.toMatch(/class=["'][^"']*\bhidden\b[^"']*["']/);
    expect(btnTag).not.toMatch(/hidden\s+md:flex/);

    // Must have 'flex' for portrait view and touch-accessible styling
    expect(btnTag).toMatch(/class=["'][^"']*\bflex\b[^"']*["']/);
    expect(btnTag).toMatch(/class=["'][^"']*\bflex-shrink-0\b[^"']*["']/);
    expect(btnTag).toMatch(/aria-label=["'][^"']*sessions[^"']*["']/i);
  });
});
