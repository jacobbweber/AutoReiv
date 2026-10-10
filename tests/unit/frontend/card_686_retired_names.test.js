/**
 * CARD-686: retired studio and feature names must not reach the page.
 * The sidebar calls the telemetry studio "Metrics"; the Purpose Matrix (CARD-153),
 * Agent Forge, Lumina, platform packs and the Docs studio are gone.
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(__dirname, '../../..');
const RETIRED = [
  /Purpose Matrix/i,
  /Observe Studio/i,
  /Open Observe/,
  /Agent Forge/i,
  /Forge Studio/i,
  /Lumina\b/,
  /platform[- ]packs/i,
  /Docs Studio/i,
];

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) return e.name === 'vendor' ? [] : walk(p);
    return /\.(js|mjs|html)$/.test(e.name) && !e.name.endsWith('.min.js') ? [p] : [];
  });
}

describe('CARD-686 retired names stay out of the UI', () => {
  const files = [
    path.join(root, 'src/web/templates/index.html'),
    ...walk(path.join(root, 'src/web/static')),
  ];

  it('[CARD-686] no retired name appears in the page or the UI scripts', () => {
    const hits = [];
    for (const f of files) {
      const lines = fs.readFileSync(f, 'utf-8').split('\n');
      lines.forEach((line, i) => {
        for (const re of RETIRED) {
          if (re.test(line)) hits.push(`${path.relative(root, f)}:${i + 1} ${re}`);
        }
      });
    }
    expect(hits).toEqual([]);
  });

  it('[CARD-686] the desktop dock names the telemetry studio Metrics, like the sidebar', () => {
    const desktopJs = fs.readFileSync(path.join(root, 'src/web/static/modules/ui/agent-desktop.js'), 'utf-8');
    expect(desktopJs).not.toContain("label: 'Observe'");
    expect(desktopJs).toMatch(/tab: 'observability',\s*label: 'Metrics'/);
  });

  it('[CARD-686] the Settings header describes what Settings really holds', () => {
    const html = fs.readFileSync(path.join(root, 'src/web/templates/index.html'), 'utf-8');
    expect(html).toContain('Each agent\'s model is set in Agents.');
    expect(html).toContain('title="Open this job in Metrics"');
  });
});
