import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  EDUCATION_PEDAGOGY_PANEL_IDS,
  EDUCATION_SECTION_KEYS,
  educationAskKeepsOriginSession,
} from '../../../src/web/static/modules/studios/education.js';

describe('CARD-315 Education continuity / honesty (shell)', () => {
  const html = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/templates/index.html'),
    'utf-8',
  );
  const educationJs = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/static/modules/studios/education.js'),
    'utf-8',
  );

  it('wraps Learning OS panels as collapsed details.edu-section', () => {
    expect(EDUCATION_SECTION_KEYS.length).toBe(EDUCATION_PEDAGOGY_PANEL_IDS.length);
    for (const key of EDUCATION_SECTION_KEYS) {
      expect(html).toContain(`data-edu-section="${key}"`);
    }
    for (const pid of EDUCATION_PEDAGOGY_PANEL_IDS) {
      expect(html).toContain(`id="${pid}"`);
    }
    const matches = html.match(/<details class="edu-section"[^>]*>/g) || [];
    expect(matches.length).toBeGreaterThanOrEqual(7);
    for (const tag of matches) {
      expect(tag).not.toMatch(/\sopen\b/);
    }
    expect(html).toContain('class="edu-section-body"');
  });

  it('gives Education view min-h-0 + CARD-315 scroll contract', () => {
    expect(html).toMatch(/id="view-education"[^>]*min-h-0/);
    expect(html).toContain('CARD-315: Education sections collapse + scroll');
    expect(html).toContain('#educationPedagogyColumns > details.edu-section[open]');
    expect(html).toContain('overflow: visible');
    expect(html).toContain('overflow-x-hidden');
    expect(html).toContain('/static/app.js?v=2.0.51');
  });

  it('keeps Ask origin-session + HITL continuity markers', () => {
    expect(educationJs).toMatch(/REQ-EDU-SHELL-002a|mint fresh Education session/i);
    expect(educationJs).toMatch(/never reuse Chat\/phase activeSessionId|Do not clobber Chat's activeSessionId/);
    expect(educationJs).toMatch(/REQ-HITL-ORIGIN-003/);
    expect(educationJs).toMatch(/DO NOT cancel|DO NOT cancel\/abort the SSE/i);
    expect(educationJs).toMatch(/REQ-HITL-ORIGIN-001/);
    expect(educationJs).toMatch(/forwardJobPhaseChromeEvent/);
    expect(educationJs).toMatch(/CARD-315/);
    expect(educationAskKeepsOriginSession()).toBe(true);
    expect(educationAskKeepsOriginSession({ reuseChatActiveSessionId: true })).toBe(false);
    expect(educationAskKeepsOriginSession({ abortSseOnJobCreated: true })).toBe(false);
  });
});
