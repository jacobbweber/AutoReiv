/**
 * CARD-437: Study entry opens Tutor education mode with durable course bind.
 * Education Studio (#tab-education / #view-education) must remain available.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';
import { loadPageHtml } from './template_helper.js';
import {
  STUDY_LAST_TOPIC_KEY,
  STUDY_EDUCATION_MODE_KEY,
  STUDY_TUTOR_AGENT_ID,
  STUDY_LEARNING_OS_SKILL,
  STUDY_EDUCATION_MODE_MARKER,
  buildStudyEducationModePrompt,
  saveLastStudyTopic,
  loadLastStudyTopic,
  startOrResumeStudyCourse,
  assembleStudyTutorContext,
  enterTutorEducationMode,
  clearStudyEducationMode,
  isStudyEducationModeActive,
  getStudyEducationModeBinding,
  renderStudyEducationModeChrome,
} from '../../../src/web/static/modules/studios/study_entry.js';

function makeEl(id, tag = 'div') {
  const classSet = new Set();
  const attrs = {};
  const el = {
    id,
    tagName: tag.toUpperCase(),
    textContent: '',
    value: '',
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

describe('CARD-437 Study entry = Tutor education mode (thin shell)', () => {
  let html;
  let studyJs;
  let appJs;
  let educationJs;
  let prevDocument;
  let els;

  beforeEach(() => {
    html = loadPageHtml();
    studyJs = fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/studios/study_entry.js'),
      'utf-8',
    );
    appJs = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/app.js'), 'utf-8');
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
      chatInput: makeEl('chatInput', 'textarea'),
      agentSelect: makeEl('agentSelect', 'select'),
    };
    els.chatEducationModeStrip.classList.add('hidden');
    globalThis.document = {
      getElementById: (id) => els[id] || null,
    };
    clearStudyEducationMode();
  });

  afterEach(() => {
    globalThis.document = prevDocument;
    vi.restoreAllMocks();
  });

  it('keeps Education Studio tab/view and adds Study entry controls [REQ-437-003]', () => {
    expect(html).toContain('id="tab-education"');
    expect(html).toContain('id="view-education"');
    expect(html).toContain('id="educationStudio"');
    expect(html).toContain('id="btn-study-entry"');
    expect(html).toContain('id="chatStudyEntryBtn"');
    expect(html).toContain('id="chatEducationModeStrip"');
    expect(html).toContain('id="chatEducationModeTopic"');
    expect(html).toContain('id="chatEducationModeCourseId"');
    expect(html).toContain('id="chatEducationModeSkill"');
    expect(html).not.toMatch(/id="btn-study-entry"[^>]*data-tab=/);
    expect(html).not.toMatch(/id="tab-study"/);
  });

  it('wires Study entry module from app.js and Learning OS skill id [REQ-437-001]', () => {
    expect(appJs).toContain('initStudyEntry');
    expect(appJs).toContain('./modules/studios/study_entry.js');
    expect(studyJs).toContain('/api/education/course/start');
    expect(studyJs).toContain('/api/education/tutor/context');
    expect(studyJs).toContain(STUDY_LEARNING_OS_SKILL);
    expect(studyJs).toContain(STUDY_TUTOR_AGENT_ID);
    expect(STUDY_LEARNING_OS_SKILL).toBe('start-resume-topic');
  });

  it('buildStudyEducationModePrompt is not freeform untitled chat [REQ-437-002]', () => {
    const prompt = buildStudyEducationModePrompt('Photosynthesis', 'course_abc');
    expect(prompt).toContain(STUDY_EDUCATION_MODE_MARKER);
    expect(prompt).toContain('start-resume-topic');
    expect(prompt).toContain('Photosynthesis');
    expect(prompt).toContain('course_id=course_abc');
    expect(prompt.toLowerCase()).not.toMatch(/^hi\b/);
  });

  it('persists last Study topic locally', () => {
    expect(STUDY_LAST_TOPIC_KEY).toContain('study');
    saveLastStudyTopic('Standing Jobs');
    expect(loadLastStudyTopic()).toBe('Standing Jobs');
  });

  it('startOrResumeStudyCourse POSTs durable Learning OS course/start [REQ-437-004]', async () => {
    const calls = [];
    globalThis.fetch = vi.fn(async (url, init) => {
      calls.push({ url, init });
      return {
        ok: true,
        json: async () => ({
          agent_id: 'tutor',
          course: { course_id: 'course_1', topic_id: 'Bayes' },
          chrome: { topic_id: 'Bayes' },
        }),
      };
    });
    const data = await startOrResumeStudyCourse('Bayes', 'tutor');
    expect(data.course.course_id).toBe('course_1');
    expect(calls).toHaveLength(1);
    expect(calls[0].url).toBe('/api/education/course/start');
    expect(calls[0].init.method).toBe('POST');
    const body = JSON.parse(calls[0].init.body);
    expect(body.agent_id).toBe('tutor');
    expect(body.topic_id).toBe('Bayes');
  });

  it('startOrResumeStudyCourse rejects empty topic (no silent plain Chat)', async () => {
    globalThis.fetch = vi.fn();
    await expect(startOrResumeStudyCourse('  ')).rejects.toThrow(/topic is required/i);
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it('assembleStudyTutorContext POSTs /api/education/tutor/context', async () => {
    globalThis.fetch = vi.fn(async () => ({
      ok: true,
      json: async () => ({ topic: 'Bayes', snippets: [] }),
    }));
    await assembleStudyTutorContext('Bayes');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/education/tutor/context',
      expect.objectContaining({ method: 'POST' }),
    );
    const body = JSON.parse(globalThis.fetch.mock.calls[0][1].body);
    expect(body.agent_id).toBe('tutor');
    expect(body.topic).toBe('Bayes');
  });

  it('enterTutorEducationMode binds Tutor + course + education rails [REQ-437-001..002]', async () => {
    const switched = [];
    const agentCalls = [];
    globalThis.fetch = vi.fn(async (url) => {
      if (String(url).includes('/course/start')) {
        return {
          ok: true,
          json: async () => ({
            course: { course_id: 'course_live', topic_id: 'Bayes Theorem' },
            chrome: {},
          }),
        };
      }
      return { ok: true, json: async () => ({ ok: true }) };
    });

    const result = await enterTutorEducationMode({
      topic: 'Bayes Theorem',
      skipPrompt: true,
      switchTab: (t) => switched.push(t),
      getChatCtrl: () => ({
        switchSelectedAgent: async (id) => {
          agentCalls.push(id);
        },
      }),
      toast: () => {},
    });

    expect(result.ok).toBe(true);
    expect(switched).toEqual(['chat']);
    expect(agentCalls).toEqual(['tutor']);
    expect(isStudyEducationModeActive()).toBe(true);
    const binding = getStudyEducationModeBinding();
    expect(binding.topic).toBe('Bayes Theorem');
    expect(binding.courseId).toBe('course_live');
    expect(binding.skillId).toBe('start-resume-topic');
    expect(els.chatEducationModeStrip.classList.contains('hidden')).toBe(false);
    expect(els.chatEducationModeTopic.textContent).toBe('Bayes Theorem');
    expect(els.chatEducationModeCourseId.textContent).toBe('course_live');
    expect(els.chatInput.value).toContain(STUDY_EDUCATION_MODE_MARKER);
    expect(els.chatInput.value).toContain('start-resume-topic');
    expect(loadLastStudyTopic()).toBe('Bayes Theorem');
    expect(STUDY_EDUCATION_MODE_KEY).toContain('education_mode');
  });

  it('enterTutorEducationMode fails soft without topic (no plain Chat)', async () => {
    globalThis.fetch = vi.fn();
    const toasts = [];
    const result = await enterTutorEducationMode({
      topic: '',
      skipPrompt: true,
      toast: (msg, type) => toasts.push({ msg, type }),
    });
    expect(result.ok).toBe(false);
    expect(result.error).toBe('STUDY_TOPIC_REQUIRED');
    expect(globalThis.fetch).not.toHaveBeenCalled();
    expect(isStudyEducationModeActive()).toBe(false);
    expect(toasts.some((t) => t.type === 'error')).toBe(true);
  });

  it('Education Studio discussWithTutor reuses Study entry path', () => {
    expect(educationJs).toContain("from './study_entry.js'");
    expect(educationJs).toContain('enterTutorEducationMode');
    expect(educationJs).toContain('CARD-437');
    expect(studyJs).toContain('/api/education/tutor/context');
  });

  it('renderStudyEducationModeChrome toggles strip visibility', () => {
    renderStudyEducationModeChrome({
      active: true,
      topic: 'X',
      courseId: 'c1',
      skillId: 'start-resume-topic',
    });
    expect(els.chatEducationModeStrip.classList.contains('hidden')).toBe(false);
    clearStudyEducationMode();
    expect(els.chatEducationModeStrip.classList.contains('hidden')).toBe(true);
  });
});
