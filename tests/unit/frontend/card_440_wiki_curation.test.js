/**
 * CARD-440: Wiki curation from links / curriculum in Tutor education mode.
 * Education Studio wiki grounding chrome must remain.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';
import { loadPageHtml } from './template_helper.js';
import {
  STUDY_WIKI_CURATION_SKILL,
  STUDY_EDUCATION_MODE_MARKER,
  STUDY_TUTOR_AGENT_ID,
  buildWikiCurationPrompt,
  curateStudyWiki,
  openWikiCurationInEducationMode,
  enterTutorEducationMode,
  clearStudyEducationMode,
  getStudyEducationModeBinding,
  renderStudyWikiCuratePanel,
  hideStudyWikiCuratePanel,
} from '../../../src/web/static/modules/studios/study_entry.js';

function makeEl(id, tag = 'div') {
  const classSet = new Set(['hidden']);
  const attrs = { 'aria-hidden': 'true' };
  const el = {
    id,
    tagName: tag.toUpperCase(),
    textContent: '',
    value: '',
    innerHTML: '',
    options: [],
    classList: {
      add: (c) => classSet.add(c),
      remove: (c) => classSet.delete(c),
      contains: (c) => classSet.has(c),
    },
    setAttribute: (k, v) => {
      attrs[k] = String(v);
    },
    getAttribute: (k) => (k in attrs ? attrs[k] : null),
    focus: () => {},
    dispatchEvent: () => true,
    addEventListener: () => {},
  };
  if (tag === 'select') {
    el.options = [{ value: 'tutor' }];
  }
  return el;
}

describe('CARD-440 Wiki curation in Tutor education mode', () => {
  let html;
  let studyJs;
  let educationJs;
  let prevDocument;
  let els;

  beforeEach(() => {
    html = loadPageHtml();
    studyJs = fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/studios/study_entry.js'),
      'utf-8',
    );
    educationJs = fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/studios/education.js'),
      'utf-8',
    );
    const store = new Map();
    globalThis.localStorage = {
      getItem: (k) => (store.has(k) ? store.get(k) : null),
      setItem: (k, v) => store.set(String(k), String(v)),
      removeItem: (k) => store.delete(k),
      clear: () => store.clear(),
    };
    prevDocument = globalThis.document;
    els = {
      chatEducationModeStrip: makeEl('chatEducationModeStrip'),
      chatEducationModeTopic: makeEl('chatEducationModeTopic', 'span'),
      chatEducationModeCourseId: makeEl('chatEducationModeCourseId', 'span'),
      chatEducationModeSkill: makeEl('chatEducationModeSkill', 'span'),
      chatEducationModeCurateBtn: makeEl('chatEducationModeCurateBtn', 'button'),
      chatEducationModeCuratePanel: makeEl('chatEducationModeCuratePanel'),
      chatEducationModeCurateResult: makeEl('chatEducationModeCurateResult'),
      chatEducationModeCurateLinkBtn: makeEl('chatEducationModeCurateLinkBtn', 'button'),
      chatEducationModeCurateCurriculumBtn: makeEl('chatEducationModeCurateCurriculumBtn', 'button'),
      chatEducationModeCurateRawBtn: makeEl('chatEducationModeCurateRawBtn', 'button'),
      chatEducationModeCurateHideBtn: makeEl('chatEducationModeCurateHideBtn', 'button'),
      chatEducationModeDueBtn: makeEl('chatEducationModeDueBtn', 'button'),
      chatEducationModeDuePanel: makeEl('chatEducationModeDuePanel'),
      chatEducationModeDueList: makeEl('chatEducationModeDueList'),
      chatInput: makeEl('chatInput', 'textarea'),
      agentSelect: makeEl('agentSelect', 'select'),
    };
    globalThis.document = {
      getElementById: (id) => els[id] || null,
    };
    clearStudyEducationMode();
  });

  afterEach(() => {
    globalThis.document = prevDocument;
    vi.restoreAllMocks();
  });

  it('keeps Education Studio wiki chrome and adds Tutor curation affordances [REQ-440-004]', () => {
    expect(html).toContain('id="tab-education"');
    expect(html).toContain('id="view-education"');
    expect(html).toContain('id="chatEducationModeCurateBtn"');
    expect(html).toContain('id="chatEducationModeCuratePanel"');
    expect(educationJs).toContain('educationWikiSearchInput');
    expect(educationJs).toContain('educationWikiHits');
    expect(studyJs).toContain('/api/education/wiki/curate');
    expect(studyJs).toContain(STUDY_WIKI_CURATION_SKILL);
    expect(studyJs.toLowerCase()).toContain('do not claim the library was updated');
  });

  it('buildWikiCurationPrompt names education-wiki-curation skill and curate contract', () => {
    const prompt = buildWikiCurationPrompt('Bayes', 'course_1', 'link');
    expect(prompt).toContain(STUDY_EDUCATION_MODE_MARKER);
    expect(prompt).toContain('education-wiki-curation');
    expect(prompt).toContain('Bayes');
    expect(prompt).toContain('education_wiki_curate_from_link');
    expect(prompt).toContain('/api/education/wiki/curate');
  });

  it('curateStudyWiki posts Learning OS wiki/curate [REQ-440-001]', async () => {
    globalThis.fetch = vi.fn(async (url, init) => {
      expect(String(url)).toContain('/api/education/wiki/curate');
      expect(init.method).toBe('POST');
      const body = JSON.parse(init.body);
      expect(body.mode).toBe('link');
      expect(body.url).toBe('https://example.com/x');
      expect(body.agent_id).toBe('tutor');
      return {
        ok: true,
        json: async () => ({
          success: true,
          durable: true,
          notes: [{ path: '00_Inbox/demo.md', title: 'Demo', template: 'education-concept' }],
          path: '00_Inbox/demo.md',
        }),
      };
    });
    const result = await curateStudyWiki({
      mode: 'link',
      url: 'https://example.com/x',
      topic: 'Bayes',
      agentId: STUDY_TUTOR_AGENT_ID,
    });
    expect(result.ok).toBe(true);
    expect(result.durable).toBe(true);
    expect(result.notes[0].path).toBe('00_Inbox/demo.md');
  });

  it('curateStudyWiki surfaces failure without durable success [REQ-440-003]', async () => {
    globalThis.fetch = vi.fn(async () => ({
      ok: true,
      json: async () => ({
        success: false,
        durable: false,
        notes: [],
        error: 'fetch failed: dns',
      }),
    }));
    const result = await curateStudyWiki({
      mode: 'link',
      url: 'https://bad.example/x',
      topic: 'Bayes',
    });
    expect(result.ok).toBe(false);
    expect(result.durable).toBe(false);
    expect(result.error).toMatch(/fetch failed/i);
  });

  it('openWikiCurationInEducationMode requires education mode then sets skill', async () => {
    const toasts = [];
    const blocked = await openWikiCurationInEducationMode({
      toast: (m, t) => toasts.push({ m, t }),
    });
    expect(blocked.ok).toBe(false);
    expect(blocked.error).toBe('EDUCATION_MODE_REQUIRED');

    globalThis.fetch = vi.fn(async (url) => {
      if (String(url).includes('/api/education/course/start')) {
        return { ok: true, json: async () => ({ course: { course_id: 'c1' } }) };
      }
      if (String(url).includes('/api/education/tutor/context')) {
        return { ok: true, json: async () => ({ ok: true }) };
      }
      return { ok: true, json: async () => ({}) };
    });
    await enterTutorEducationMode({
      topic: 'Bayes',
      skipPrompt: true,
      toast: () => {},
    });
    expect(getStudyEducationModeBinding()?.topic).toBe('Bayes');

    const opened = await openWikiCurationInEducationMode({ toast: () => {} });
    expect(opened.ok).toBe(true);
    expect(getStudyEducationModeBinding()?.skillId).toBe(STUDY_WIKI_CURATION_SKILL);
    expect(els.chatEducationModeCuratePanel.classList.contains('hidden')).toBe(false);
    hideStudyWikiCuratePanel();
    expect(els.chatEducationModeCuratePanel.classList.contains('hidden')).toBe(true);
  });

  it('renderStudyWikiCuratePanel shows paths and errors', () => {
    renderStudyWikiCuratePanel({
      ok: true,
      success: true,
      notes: [{ path: '00_Inbox/a.md', title: 'A', template: 'education-concept' }],
    });
    expect(els.chatEducationModeCurateResult.innerHTML).toContain('00_Inbox/a.md');
    renderStudyWikiCuratePanel({ ok: false, success: false, error: 'boom', notes: [] });
    expect(els.chatEducationModeCurateResult.innerHTML).toContain('boom');
  });
});
