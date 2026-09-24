/**
 * CARD-441: Trustable progress on Tutor education-mode strip (non-Studio).
 * Education Studio course/mastery chrome must remain.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';
import { loadPageHtml } from './template_helper.js';
import {
  STUDY_PROGRESS_SKILL,
  STUDY_EDUCATION_MODE_MARKER,
  STUDY_TUTOR_AGENT_ID,
  buildProgressSummaryPrompt,
  fetchStudyProgress,
  openProgressInEducationMode,
  enterTutorEducationMode,
  clearStudyEducationMode,
  renderStudyProgressPanel,
  hideStudyProgressPanel,
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

describe('CARD-441 Progress you can trust (non-Studio Tutor surface)', () => {
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
      chatEducationModeProgressBtn: makeEl('chatEducationModeProgressBtn', 'button'),
      chatEducationModeProgressBadge: makeEl('chatEducationModeProgressBadge', 'span'),
      chatEducationModeProgressPanel: makeEl('chatEducationModeProgressPanel'),
      chatEducationModeProgressBody: makeEl('chatEducationModeProgressBody'),
      chatEducationModeProgressRefreshBtn: makeEl('chatEducationModeProgressRefreshBtn', 'button'),
      chatEducationModeProgressHideBtn: makeEl('chatEducationModeProgressHideBtn', 'button'),
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

  it('keeps Studio chrome and adds Tutor Progress affordances [REQ-441-004]', () => {
    expect(html).toContain('id="tab-education"');
    expect(html).toContain('id="view-education"');
    expect(html).toContain('id="educationCourseChrome"');
    expect(html).toContain('id="chatEducationModeProgressBtn"');
    expect(html).toContain('id="chatEducationModeProgressPanel"');
    expect(html).toContain('id="chatEducationModeProgressBody"');
    expect(html).toContain('/api/education/progress');
    expect(studyJs).toContain('/api/education/progress');
    expect(studyJs).toContain(STUDY_PROGRESS_SKILL);
    expect(studyJs).toContain('education_progress_summary');
    expect(educationJs).toContain('renderEducationCourseChrome');
  });

  it('buildProgressSummaryPrompt names progress-summary skill and progress API', () => {
    const prompt = buildProgressSummaryPrompt('Bayes', 'course_1');
    expect(prompt).toContain(STUDY_EDUCATION_MODE_MARKER);
    expect(prompt).toContain('progress-summary');
    expect(prompt).toContain('Bayes');
    expect(prompt).toContain('education_progress_summary');
    expect(prompt).toContain('/api/education/progress');
    expect(prompt.toLowerCase()).toMatch(/never invent|not invent|honest/);
  });

  it('fetchStudyProgress sources Learning OS progress API [REQ-441-001]', async () => {
    globalThis.fetch = vi.fn(async (url) => {
      expect(String(url)).toContain('/api/education/progress');
      expect(String(url)).toContain('agent_id=tutor');
      return {
        ok: true,
        json: async () => ({
          success: true,
          empty: false,
          topic: 'Bayes',
          course_id: 'c1',
          current_course: {
            course_id: 'c1',
            topic_id: 'Bayes',
            status: 'active',
            current_step: 'retrieval',
          },
          course: { count: 1, empty: false },
          mastery: {
            item_count: 2,
            pass_count: 1,
            miss_count: 1,
            unseen_count: 0,
            mastery_pct: 50,
            empty: false,
          },
          due: { count: 1, empty: false },
          chrome: { current_step: 'retrieval', status: 'active' },
        }),
      };
    });
    const progress = await fetchStudyProgress(STUDY_TUTOR_AGENT_ID, { topicId: 'Bayes' });
    expect(progress.ok).toBe(true);
    expect(progress.empty).toBe(false);
    expect(progress.mastery.mastery_pct).toBe(50);
    expect(progress.due.count).toBe(1);
    expect(progress.studio_required).toBe(false);
  });

  it('fetchStudyProgress empty/failure is honest [REQ-441-003]', async () => {
    globalThis.fetch = vi.fn(async () => ({
      ok: true,
      json: async () => ({
        success: true,
        empty: true,
        empty_state: 'No course or mastery progress yet.',
        mastery: { mastery_pct: null, empty: true, item_count: 0 },
        due: { count: 0, empty: true },
        course: { count: 0, empty: true },
      }),
    }));
    const empty = await fetchStudyProgress();
    expect(empty.ok).toBe(true);
    expect(empty.empty).toBe(true);
    expect(empty.mastery.mastery_pct).toBeNull();

    globalThis.fetch = vi.fn(async () => ({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'boom' }),
    }));
    const failed = await fetchStudyProgress();
    expect(failed.ok).toBe(false);
    expect(failed.mastery.mastery_pct).toBeNull();
    expect(String(failed.error || '')).toContain('500');
  });

  it('openProgressInEducationMode requires education mode then renders panel', async () => {
    const toasts = [];
    globalThis.fetch = vi.fn();
    const blocked = await openProgressInEducationMode({
      toast: (msg, type) => toasts.push({ msg, type }),
    });
    expect(blocked.ok).toBe(false);
    expect(blocked.error).toBe('EDUCATION_MODE_REQUIRED');

    globalThis.fetch = vi.fn(async (url) => {
      if (String(url).includes('/course/start')) {
        return {
          ok: true,
          json: async () => ({ course: { course_id: 'course_p', topic_id: 'Bayes' } }),
        };
      }
      if (String(url).includes('/tutor/context')) {
        return { ok: true, json: async () => ({ ok: true }) };
      }
      if (String(url).includes('/progress')) {
        return {
          ok: true,
          json: async () => ({
            success: true,
            empty: false,
            topic: 'Bayes',
            course_id: 'course_p',
            current_course: {
              course_id: 'course_p',
              topic_id: 'Bayes',
              status: 'active',
              current_step: 'priming',
            },
            course: { count: 1 },
            mastery: {
              pass_count: 0,
              miss_count: 0,
              unseen_count: 0,
              mastery_pct: null,
              item_count: 0,
              empty: true,
            },
            due: { count: 0, empty: true, empty_state: 'No due reviews.' },
            chrome: { current_step: 'priming' },
          }),
        };
      }
      return { ok: true, json: async () => ({}) };
    });

    await enterTutorEducationMode({
      topic: 'Bayes',
      skipPrompt: true,
      switchTab: () => {},
      getChatCtrl: () => ({ switchSelectedAgent: async () => {} }),
      toast: () => {},
    });

    const opened = await openProgressInEducationMode({
      toast: (msg, type) => toasts.push({ msg, type }),
    });
    expect(opened.ok).toBe(true);
    expect(els.chatEducationModeProgressPanel.classList.contains('hidden')).toBe(false);
    hideStudyProgressPanel();
    expect(els.chatEducationModeProgressPanel.classList.contains('hidden')).toBe(true);
  });

  it('renderStudyProgressPanel never paints fake 100% on error', () => {
    renderStudyProgressPanel({
      ok: false,
      success: false,
      error: 'progress 500',
      mastery: { mastery_pct: null },
    });
    expect(els.chatEducationModeProgressBody.innerHTML).toContain('progress 500');
    expect(els.chatEducationModeProgressBody.innerHTML).not.toMatch(/100%/);
  });
});
