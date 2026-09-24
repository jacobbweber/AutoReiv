/**
 * CARD-439: Due reviews surface in Tutor education mode from Learning OS mastery/due.
 * Education Studio due chrome must remain.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';
import { loadPageHtml } from './template_helper.js';
import {
  STUDY_DUE_REVIEW_SKILL,
  STUDY_EDUCATION_MODE_MARKER,
  STUDY_TUTOR_AGENT_ID,
  buildDueReviewPrompt,
  fetchStudyDueReviews,
  openDueReviewsInEducationMode,
  enterTutorEducationMode,
  clearStudyEducationMode,
  getStudyEducationModeBinding,
  renderStudyDueReviewsPanel,
  hideStudyDueReviewsPanel,
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

describe('CARD-439 Due reviews in Tutor education mode', () => {
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
      chatEducationModeDueBtn: makeEl('chatEducationModeDueBtn', 'button'),
      chatEducationModeDueCount: makeEl('chatEducationModeDueCount', 'span'),
      chatEducationModeDuePanel: makeEl('chatEducationModeDuePanel'),
      chatEducationModeDueList: makeEl('chatEducationModeDueList'),
      chatEducationModeDueRefreshBtn: makeEl('chatEducationModeDueRefreshBtn', 'button'),
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

  it('keeps Education Studio due chrome and adds Tutor due affordances [REQ-439]', () => {
    expect(html).toContain('id="tab-education"');
    expect(html).toContain('id="educationDueList"');
    expect(html).toContain('id="educationRefreshDueBtn"');
    expect(html).toContain('id="educationRunRetentionBtn"');
    expect(html).toContain('id="chatEducationModeDueBtn"');
    expect(html).toContain('id="chatEducationModeDuePanel"');
    expect(html).toContain('id="chatEducationModeDueList"');
    expect(educationJs).toContain('/api/education/mastery/due');
    expect(studyJs).toContain('/api/education/mastery/due');
    expect(studyJs).toContain(STUDY_DUE_REVIEW_SKILL);
    expect(studyJs).toContain('No due reviews.');
    expect(studyJs.toLowerCase()).toContain('do not replace ledger/srs');
  });

  it('buildDueReviewPrompt names due-review skill and mastery due contract', () => {
    const prompt = buildDueReviewPrompt('Bayes', 'course_1', 2);
    expect(prompt).toContain(STUDY_EDUCATION_MODE_MARKER);
    expect(prompt).toContain('due-review');
    expect(prompt).toContain('Bayes');
    expect(prompt).toContain('education_due_review_list');
    expect(prompt).toContain('/api/education/mastery/due');
    expect(prompt.toLowerCase()).toContain('do not replace ledger/srs');
  });

  it('fetchStudyDueReviews sources Learning OS mastery/due [REQ-439-001]', async () => {
    globalThis.fetch = vi.fn(async (url) => {
      expect(String(url)).toContain('/api/education/mastery/due');
      expect(String(url)).toContain('agent_id=tutor');
      return {
        ok: true,
        json: async () => ({
          items: [
            {
              item_id: 'edu_1',
              topic: 'Bayes',
              prompt: 'Prior?',
              next_due: '2026-09-01T00:00:00Z',
            },
          ],
        }),
      };
    });
    const due = await fetchStudyDueReviews(STUDY_TUTOR_AGENT_ID);
    expect(due.ok).toBe(true);
    expect(due.empty).toBe(false);
    expect(due.count).toBe(1);
    expect(due.items[0].item_id).toBe('edu_1');
  });

  it('fetchStudyDueReviews empty state is honest [REQ-439-003]', async () => {
    globalThis.fetch = vi.fn(async () => ({
      ok: true,
      json: async () => ({ items: [] }),
    }));
    const due = await fetchStudyDueReviews();
    expect(due.ok).toBe(true);
    expect(due.empty).toBe(true);
    expect(due.count).toBe(0);
    expect(due.empty_state).toBe('No due reviews.');
  });

  it('openDueReviewsInEducationMode requires education mode then lists dues', async () => {
    const toasts = [];
    globalThis.fetch = vi.fn();
    const blocked = await openDueReviewsInEducationMode({
      toast: (msg, type) => toasts.push({ msg, type }),
    });
    expect(blocked.ok).toBe(false);
    expect(blocked.error).toBe('EDUCATION_MODE_REQUIRED');

    globalThis.fetch = vi.fn(async (url) => {
      if (String(url).includes('/course/start')) {
        return {
          ok: true,
          json: async () => ({ course: { course_id: 'course_due', topic_id: 'Bayes' } }),
        };
      }
      if (String(url).includes('/tutor/context')) {
        return { ok: true, json: async () => ({ ok: true }) };
      }
      if (String(url).includes('/mastery/due')) {
        return { ok: true, json: async () => ({ items: [] }) };
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

    const opened = await openDueReviewsInEducationMode({
      toast: (msg, type) => toasts.push({ msg, type }),
    });
    expect(opened.ok).toBe(true);
    expect(opened.due.empty).toBe(true);
    const binding = getStudyEducationModeBinding();
    expect(binding.skillId).toBe('due-review');
    expect(els.chatInput.value).toContain('due-review');
    expect(els.chatEducationModeDuePanel.classList.contains('hidden')).toBe(false);
    expect(els.chatEducationModeDueList.innerHTML).toContain('No due reviews.');
    expect(STUDY_DUE_REVIEW_SKILL).toBe('due-review');
  });

  it('renderStudyDueReviewsPanel shows items; hide clears panel', () => {
    renderStudyDueReviewsPanel({
      ok: true,
      empty: false,
      items: [{ item_id: 'edu_x', topic: 'T', prompt: 'Q?', next_due: '2026-09-02T00:00:00Z' }],
    });
    expect(els.chatEducationModeDueList.innerHTML).toContain('edu_x');
    expect(els.chatEducationModeDueCount.textContent).toBe('1');
    hideStudyDueReviewsPanel();
    expect(els.chatEducationModeDuePanel.classList.contains('hidden')).toBe(true);
  });
});
