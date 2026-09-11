import { describe, it, expect, beforeEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  EDUCATION_SESSIONS_KEY,
  EDUCATION_ASK_MARKER,
  buildEducationAsk,
  EDUCATION_MODES,
  loadEducationSessions,
  saveEducationSessions,
  upsertEducationSession,
  extractJobIdFromSsePayload,
  isEducationJobGoal,
} from '../../../src/web/static/modules/studios/education.js';

describe('Education Studio shell [CARD-237 / REQ-EDU-SHELL-001..004]', () => {
  let html;
  let educationJs;
  let appJs;
  let desktopJs;

  beforeEach(() => {
    html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
    educationJs = fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/studios/education.js'),
      'utf-8',
    );
    appJs = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/app.js'), 'utf-8');
    desktopJs = fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/ui/agent-desktop.js'),
      'utf-8',
    );
    const store = new Map();
    globalThis.localStorage = {
      getItem: (k) => (store.has(k) ? store.get(k) : null),
      setItem: (k, v) => store.set(String(k), String(v)),
      removeItem: (k) => store.delete(k),
      clear: () => store.clear(),
    };
  });

  it('registers Education Studio tab + view in SPA nav [REQ-EDU-SHELL-001]', () => {
    expect(html).toContain('id="tab-education"');
    expect(html).toContain('data-tab="education"');
    expect(html).toContain('id="view-education"');
    expect(html).toContain('id="educationStudio"');
    expect(html).toMatch(/Education\s*Studio|Education/);
    expect(appJs).toContain("initEducationStudio");
    expect(appJs).toContain("./modules/studios/education.js");
    expect(desktopJs).toContain("dock-education");
    expect(desktopJs).toContain("education: 'view-education'");
  });

  it('declares Wiki-backed ask fields (topic + how to teach) [REQ-EDU-SHELL-002]', () => {
    expect(html).toContain('id="educationTopicInput"');
    expect(html).toContain('id="educationTeachStyleInput"');
    expect(html).toContain('id="educationWikiSearchInput"');
    expect(html).toContain('id="educationWikiHits"');
    expect(html).toContain('id="educationAskSubmitBtn"');
    expect(html).toContain('id="educationJobIdChip"');
    expect(html).toContain('id="educationCopyJobIdBtn"');
  });

  it('declares Education Jobs session list with Chat/Observe open actions [REQ-EDU-SHELL-003]', () => {
    expect(html).toContain('id="educationSessionList"');
    expect(html).toContain('id="educationSessionsRefreshBtn"');
    expect(educationJs).toContain('Open in Chat');
    expect(educationJs).toContain('Open in Observe');
    expect(educationJs).toContain('standingJourneyJobIdInput');
  });

  it('wires ask → standing Chat/Job mint path (236) with copyable job_id [REQ-EDU-SHELL-002]', () => {
    expect(educationJs).toContain('/api/chat/stream');
    expect(educationJs).toContain('buildChatStreamPayload');
    expect(educationJs).toContain('job_created');
    expect(educationJs).toContain('/api/sessions');
    expect(educationJs).toContain('/api/wiki/search');
    expect(educationJs).toContain('copyToClipboard');
    expect(educationJs).toContain(EDUCATION_ASK_MARKER);
  });

  it('does not ship pedagogy depth hooks in this shell [REQ-EDU-SHELL-004]', () => {
    // Shell + Job mint only — no feature IDs / module wiring for later Learning OS slices.
    expect(html).not.toMatch(/id=["']educationQuiz/i);
    expect(html).not.toMatch(/id=["']educationSrs/i);
    expect(html).not.toMatch(/id=["']educationConceptPlayer/i);
    expect(educationJs).not.toMatch(/conceptPlayer|spacedRepetition|learnerModel/i);
    expect(educationJs.toLowerCase()).not.toContain('lumina');
    expect(educationJs.toLowerCase()).not.toContain('mycel');
  });

  it('buildEducationAsk is outcome-shaped with topic, teach style, and done-when', () => {
    const ask = buildEducationAsk({
      topic: 'standing Jobs',
      teachStyle: 'ADHD bite-size with one analogy',
      wikiPath: 'concepts/jobs.md',
      wikiTitle: 'Jobs',
    });
    expect(ask).toContain(EDUCATION_ASK_MARKER);
    expect(ask.toLowerCase()).toContain('standing jobs');
    expect(ask.toLowerCase()).toContain('adhd bite-size');
    expect(ask).toContain('concepts/jobs.md');
    expect(ask.toLowerCase()).toContain('done-when');
    expect(isEducationJobGoal(ask)).toBe(true);
  });

  it('persists education sessions locally and upserts by job_id [REQ-EDU-SHELL-003]', () => {
    expect(EDUCATION_SESSIONS_KEY).toContain('education');
    saveEducationSessions([]);
    upsertEducationSession({
      job_id: 'job_abc',
      session_id: 'sess_1',
      topic: 'Jobs',
      teach_style: 'bite-size',
      created_at: '2026-09-11T12:00:00-04:00',
    });
    const rows = loadEducationSessions();
    expect(rows).toHaveLength(1);
    expect(rows[0].job_id).toBe('job_abc');
    upsertEducationSession({
      job_id: 'job_abc',
      session_id: 'sess_1',
      topic: 'Jobs updated',
      teach_style: 'bite-size',
      created_at: '2026-09-11T12:01:00-04:00',
    });
    expect(loadEducationSessions()).toHaveLength(1);
    expect(loadEducationSessions()[0].topic).toBe('Jobs updated');
  });

  it('extractJobIdFromSsePayload reads job_id from standing mint events', () => {
    expect(extractJobIdFromSsePayload({ type: 'job_created', job_id: 'job_xyz' })).toBe('job_xyz');
    expect(extractJobIdFromSsePayload({ type: 'token', text: 'hi' })).toBe('');
    expect(extractJobIdFromSsePayload({ job_id: 'job_plain' })).toBe('job_plain');
  });

  it('isolates Education load so a studio failure cannot blank initApp [REQ-EDU-SHELL-005]', () => {
    // No static top-level import — that would SyntaxError/abort the whole SPA module graph
    expect(appJs).not.toMatch(/import\s*\{\s*initEducationStudio\s*\}\s*from\s*['"]\.\/modules\/studios\/education\.js['"]/);
    expect(appJs).toMatch(/import\(\s*['"]\.\/modules\/studios\/education\.js['"]\s*\)/);
    // Education tab loader is a real else-if in the try, not a stray brace after the chain
    expect(appJs).toMatch(
      /promptsCtrl\.loadPrompts\(\);\s*\} else if \(tabName === 'education' && educationCtrl\)/,
    );
    expect(appJs).not.toMatch(
      /promptsCtrl\.loadPrompts\(\);\s*\}\s*\} else if \(tabName === 'education'/,
    );
  });


  it('Ask mint never reuses Chat/phase session [REQ-EDU-SHELL-002a]', () => {
    expect(educationJs).toMatch(/never reuse Chat\/phase activeSessionId/);
    expect(educationJs).toMatch(/ensureSession\(topic/);
    expect(educationJs).not.toMatch(/if \(state\.activeSessionId\) \{\s*lastSessionId = state\.activeSessionId/);
    expect(educationJs).toMatch(/AbortController/);
    expect(educationJs).toMatch(/educationAskSubmitBtn/);
  });


  it('keeps Education SSE open after job_created [REQ-HITL-ORIGIN-003]', () => {
    expect(educationJs).toMatch(/REQ-HITL-ORIGIN-003/);
    expect(educationJs).not.toMatch(/reader\.cancel\(\)/);
    expect(educationJs).toMatch(/onJobMinted/);
    expect(educationJs).toMatch(/openOriginChatForHitl|selectSession/);
  });

  it('surfaces Needs approval on Education Jobs with Approve in Chat [REQ-HITL-ORIGIN-002]', () => {
    expect(educationJs).toMatch(/needs_approval/);
    expect(educationJs).toMatch(/Approve in Chat/);
    expect(educationJs).toMatch(/refreshEducationApprovals/);
    expect(educationJs).toMatch(/\/api\/approvals\/pending/);
  });

  it('Priming / Dual Coding modes shape Ask + success_rule [REQ-LOS-012-001/002]', () => {
    expect(html).toContain('id="educationModePriming"');
    expect(html).toContain('id="educationModeDualCoding"');
    expect(html).toContain('id="educationModeCustom"');
    expect(educationJs).toContain('EDUCATION_MODES');
    const priming = buildEducationAsk({ topic: 'Jobs', mode: EDUCATION_MODES.priming });
    expect(priming).toContain('never wiki_overview');
    expect(priming).toContain('wiki_note_create');
    expect(priming).toMatch(/Mode: Priming/);
    expect(priming).toMatch(/education-priming/);
    expect(priming).toMatch(/Done-when:.*Priming schema note/i);
    const dual = buildEducationAsk({ topic: 'Jobs', mode: EDUCATION_MODES.dual_coding });
    expect(dual).toContain('never wiki_overview');
    expect(dual).toMatch(/Mode: Dual Coding/);
    expect(dual).toMatch(/education-dual-coding/);
    expect(dual).toMatch(/Mermaid/);
    expect(dual).toMatch(/Done-when:.*Dual Coding study note/i);
  });

  it('does not include quiz/SRS/player in Education shell [REQ-LOS-012-003]', () => {
    expect(educationJs.toLowerCase()).not.toMatch(/\bsrs\b|spaced.repetition|concept-player|lumina/);
    expect(html.toLowerCase()).not.toMatch(/\bsrs\b|quiz player|concept-player/);
  });

});

