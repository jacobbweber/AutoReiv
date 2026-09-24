/**
 * CARD-447: Education Studio operator strip + Tutor topic/course context.
 * Studio hosts Due/Progress/Wiki curate; Tutor injects Studio-active selection
 * (Projects selected parallel). Chat strip is thinned (deep-link). No CARD-448 players.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';
import { loadPageHtml } from './template_helper.js';
import {
  EDUCATION_STUDIO_ACTIVE_KEY,
  EDUCATION_SELECTED_HTTP,
  loadStudioActiveEducationContext,
  saveStudioActiveEducationContext,
  resolveTutorEducationTopic,
  fetchSelectedEducationContext,
  putSelectedEducationContext,
  enterTutorEducationMode,
  clearStudyEducationMode,
  STUDY_TUTOR_AGENT_ID,
} from '../../../src/web/static/modules/studios/study_entry.js';

function makeEl(id, tag = 'div') {
  const classSet = new Set(['hidden']);
  const attrs = {};
  const dataset = {};
  const el = {
    id,
    tagName: tag.toUpperCase(),
    textContent: '',
    value: '',
    innerHTML: '',
    dataset,
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
    click: () => {},
  };
  if (tag === 'select') {
    el.options = [{ value: 'tutor' }];
  }
  return el;
}

describe('CARD-447 Education Studio operator + Tutor context', () => {
  let html;
  let studyJs;
  let educationJs;
  let operatorJs;
  let prevDocument;
  let store;
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
    operatorJs = fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/studios/education_operator.js'),
      'utf-8',
    );
    store = new Map();
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
      chatEducationModeOpenStudioBtn: makeEl('chatEducationModeOpenStudioBtn', 'button'),
      chatEducationModeDueBtn: makeEl('chatEducationModeDueBtn', 'button'),
      chatEducationModeProgressBtn: makeEl('chatEducationModeProgressBtn', 'button'),
      chatEducationModeCurateBtn: makeEl('chatEducationModeCurateBtn', 'button'),
      educationOperatorConsole: makeEl('educationOperatorConsole'),
      educationActiveTopic: makeEl('educationActiveTopic', 'span'),
      educationActiveCourseId: makeEl('educationActiveCourseId', 'span'),
      educationSetActiveContextBtn: makeEl('educationSetActiveContextBtn', 'button'),
      educationOperatorDueBtn: makeEl('educationOperatorDueBtn', 'button'),
      educationOperatorProgressBtn: makeEl('educationOperatorProgressBtn', 'button'),
      educationOperatorCurateBtn: makeEl('educationOperatorCurateBtn', 'button'),
      educationTopicInput: makeEl('educationTopicInput', 'input'),
      chatInput: makeEl('chatInput', 'textarea'),
      agentSelect: makeEl('agentSelect', 'select'),
      tabEducation: makeEl('tab-education', 'button'),
    };
    // $() helper uses getElementById; map tab-education id
    globalThis.document = {
      getElementById: (id) => {
        if (id === 'tab-education') return els.tabEducation;
        return els[id] || null;
      },
    };
    clearStudyEducationMode();
    store.clear();
  });

  afterEach(() => {
    globalThis.document = prevDocument;
    vi.restoreAllMocks();
  });

  it('[REQ-447-006] keeps Education Studio tab/landing', () => {
    expect(html).toContain('id="tab-education"');
    expect(html).toContain('id="view-education"');
    expect(html).toContain('id="educationStudio"');
  });

  it('[REQ-447-003][REQ-447-004] Studio operator console hosts Due/Progress/Wiki curate', () => {
    expect(html).toContain('id="educationOperatorConsole"');
    expect(html).toContain('id="educationOperatorDueBtn"');
    expect(html).toContain('id="educationOperatorProgressBtn"');
    expect(html).toContain('id="educationOperatorCurateBtn"');
    expect(html).toContain('id="educationSetActiveContextBtn"');
    expect(html).toContain('/api/education/mastery/due');
    expect(html).toContain('GET /api/education/progress');
    expect(html).toContain('POST /api/education/wiki/curate');
    expect(operatorJs).toContain("fetchStudyDueReviews");
    expect(operatorJs).toContain("fetchStudyProgress");
    expect(operatorJs).toContain("curateStudyWiki");
    expect(operatorJs).toContain('/api/education/selected');
  });

  it('[REQ-447-004] chat strip thins with Studio deep-link (not sole operator home)', () => {
    expect(html).toContain('id="chatEducationModeOpenStudioBtn"');
    expect(html).toContain('data-operator-home="studio"');
    expect(studyJs).toContain('chatEducationModeOpenStudioBtn');
    expect(studyJs).toContain('card447Wired');
    expect(studyJs).toContain("tab-education");
  });

  it('[REQ-447-001] persists Studio-active context in localStorage key', () => {
    expect(EDUCATION_STUDIO_ACTIVE_KEY).toBe('autoreiv.educationStudio.activeContext.v1');
    saveStudioActiveEducationContext({
      topic: 'Bayes',
      course_id: 'course_1',
      agent_id: 'tutor',
    });
    const loaded = loadStudioActiveEducationContext();
    expect(loaded.topic).toBe('Bayes');
    expect(loaded.course_id).toBe('course_1');
    expect(JSON.parse(store.get(EDUCATION_STUDIO_ACTIVE_KEY)).topic).toBe('Bayes');
  });

  it('[REQ-447-001][REQ-447-002] selected HTTP helpers call /api/education/selected', async () => {
    expect(EDUCATION_SELECTED_HTTP).toBe('/api/education/selected');
    globalThis.fetch = vi.fn(async (url, init) => {
      if (String(url).includes('/api/education/selected') && (!init || !init.method || init.method === 'GET')) {
        return {
          ok: true,
          json: async () => ({ selected: { topic: 'Raft', course_id: 'c1', agent_id: 'tutor' } }),
        };
      }
      if (String(url).includes('/api/education/selected') && init && init.method === 'PUT') {
        const body = JSON.parse(init.body);
        return {
          ok: true,
          json: async () => ({ success: true, selected: { topic: body.topic, course_id: body.course_id, agent_id: body.agent_id } }),
        };
      }
      return { ok: false, status: 404, text: async () => '' };
    });
    const got = await fetchSelectedEducationContext();
    expect(got.selected.topic).toBe('Raft');
    const put = await putSelectedEducationContext({ topic: 'Raft', course_id: 'c1' });
    expect(put.selected.topic).toBe('Raft');
    expect(loadStudioActiveEducationContext().topic).toBe('Raft');
  });

  it('[REQ-447-002] resolveTutorEducationTopic prefers Studio selected', async () => {
    globalThis.fetch = vi.fn(async () => ({
      ok: true,
      json: async () => ({ selected: { topic: 'Studio Topic', course_id: 'sc1' } }),
    }));
    const resolved = await resolveTutorEducationTopic('');
    expect(resolved.topic).toBe('Studio Topic');
    expect(resolved.source).toBe('education_studio');
    expect(resolved.courseId).toBe('sc1');
  });

  it('[REQ-447-002] enterTutorEducationMode injects Studio topic via tutor/context', async () => {
    const calls = [];
    globalThis.fetch = vi.fn(async (url, init) => {
      calls.push({ url: String(url), method: (init && init.method) || 'GET', body: init && init.body });
      if (String(url).includes('/api/education/selected') && (!init || !init.method || init.method === 'GET')) {
        return {
          ok: true,
          json: async () => ({ selected: { topic: 'Inject Me', course_id: 'inj1' } }),
        };
      }
      if (String(url).includes('/api/education/course/start')) {
        return {
          ok: true,
          json: async () => ({ course: { course_id: 'inj1', topic_id: 'Inject Me' } }),
        };
      }
      if (String(url).includes('/api/education/tutor/context')) {
        return { ok: true, json: async () => ({ topic: 'Inject Me', context_prompt_clause: 'x' }) };
      }
      if (String(url).includes('/api/education/selected') && init && init.method === 'PUT') {
        return {
          ok: true,
          json: async () => ({ success: true, selected: { topic: 'Inject Me', course_id: 'inj1' } }),
        };
      }
      return { ok: false, status: 500, text: async () => 'nope' };
    });
    const res = await enterTutorEducationMode({
      skipPrompt: true,
      toast: () => {},
      switchTab: () => {},
    });
    expect(res.ok).toBe(true);
    expect(res.binding.topic).toBe('Inject Me');
    expect(calls.some((c) => c.url.includes('/api/education/tutor/context'))).toBe(true);
    expect(calls.some((c) => c.url.includes('/api/education/selected') && c.method === 'PUT')).toBe(true);
  });

  it('[REQ-447-007] does not rip Learning OS API strings from study_entry', () => {
    expect(studyJs).toContain('/api/education/mastery/due');
    expect(studyJs).toContain('/api/education/progress');
    expect(studyJs).toContain('/api/education/wiki/curate');
    expect(studyJs).toContain('/api/education/course/start');
    expect(studyJs).toContain('/api/education/tutor/context');
  });

  it('education.js loads operator module; no CARD-448 player shell claimed', () => {
    expect(educationJs).toContain("education_operator.js");
    expect(educationJs).toContain('CARD-447');
    expect(operatorJs).not.toContain('flashcard player');
    expect(operatorJs).toMatch(/Does NOT build.*CARD-448|not implement CARD-448/i);
    expect(operatorJs).not.toContain('initFlashcardPlayer');
    expect(operatorJs).not.toContain('quizPlayerSession');
  });

  it('agent id default remains tutor', () => {
    expect(STUDY_TUTOR_AGENT_ID).toBe('tutor');
  });
});
