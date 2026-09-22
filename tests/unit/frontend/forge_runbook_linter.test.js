/**
 * CARD-390: Integrated Runbook Editor & Mechanical Capability Linter.
 * Verifies that #studioRunbookEditor provides live ADR-0054 capability contract validation,
 * character budget tracking, canonical blueprint scaffolding, and pre-save violation guards.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Integrated Runbook Editor & Mechanical Capability Linter [CARD-390]', () => {
  const html = read('src/web/templates/index.html');
  const forgeJs = read('src/web/static/modules/studios/forge.js') + read('src/web/static/modules/studios/forge/runbook.js');

  it('[REQ-390-005] index.html provides validation button, status container, and char count inside #studioRunbookEditor', () => {
    expect(html).toContain('id="studioRunbookEditor"');
    expect(html).toContain('id="studioRunbookValidateBtn"');
    expect(html).toContain('id="studioRunbookLintStatus"');
    expect(html).toContain('id="studioRunbookCharCount"');
  });

  it('[REQ-390-005] forge.js caches linter elements and defines the canonical blueprint template', () => {
    expect(forgeJs).toContain("const studioRunbookValidateBtn = $('studioRunbookValidateBtn');");
    expect(forgeJs).toContain("const studioRunbookLintStatus = $('studioRunbookLintStatus');");
    expect(forgeJs).toContain("const studioRunbookCharCount = $('studioRunbookCharCount');");
    expect(forgeJs).toContain('CANONICAL_RUNBOOK_TEMPLATE');
    expect(forgeJs).toContain('Operating Principles');
    expect(forgeJs).toContain('Available Tools');
    expect(forgeJs).toContain('Done-When');
  });

  it('[REQ-390-005] forge.js implements char counting, status rendering, and endpoint validation', () => {
    expect(forgeJs).toContain('function updateRunbookCharCount()');
    expect(forgeJs).toContain('function clearRunbookLintStatus()');
    expect(forgeJs).toContain('function renderRunbookLintReport(');
    expect(forgeJs).toContain('async function validateActiveRunbook(');
    expect(forgeJs).toContain("fetch('/api/skills/lint'");
  });

  it('[CARD-411] Forge does not persist runbooks; validation stays read-only', () => {
    expect(forgeJs).not.toContain('await validateActiveRunbook(true)');
    expect(forgeJs).not.toContain("method: 'PUT'");
    expect(forgeJs).toContain('studioRunbookOpenFactoryBtn');
  });

  it('[REQ-390-005] forge.js wires validate button and textarea input listeners', () => {
    expect(forgeJs).toMatch(/studioRunbookValidateBtn.*addEventListener\(['"]click['"]/);
    expect(forgeJs).toMatch(/studioRunbookBody.*addEventListener\(['"]input['"]/);
  });

  it('[REQ-390-SINGLE-LEVER] Standalone Skills Studio (#view-skills) remains retired', () => {
    // Single Lever Invariant: We must never resurrect a separate Skills Studio window/dock icon
    expect(html).not.toContain('id="tab-skills"');
    expect(html).not.toContain('id="view-skills"');
    expect(forgeJs).not.toContain('initSkillsStudio');
  });
});
