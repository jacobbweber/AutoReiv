/**
 * CARD-464: full-screen players, flip-style flashcards, one Progress view.
 * REQ-464-001..006
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';
import { loadPageHtml } from './template_helper.js';

function makeClassList(initial = []) {
  const set = new Set(initial);
  return {
    add: (...c) => c.forEach((x) => set.add(x)),
    remove: (...c) => c.forEach((x) => set.delete(x)),
    contains: (c) => set.has(c),
    toggle: (c, force) => {
      const on = force === undefined ? !set.has(c) : Boolean(force);
      if (on) set.add(c); else set.delete(c);
      return on;
    },
  };
}

function makeEl(id, { hidden = false, tagName = 'DIV' } = {}) {
  const attrs = {};
  return {
    id,
    tagName,
    textContent: '',
    innerHTML: '',
    className: '',
    value: '',
    classList: makeClassList(hidden ? ['hidden'] : []),
    setAttribute: (k, v) => { attrs[k] = String(v); },
    getAttribute: (k) => (k in attrs ? attrs[k] : null),
    addEventListener: () => {},
  };
}

const IDS = [
  'educationPlayerFlashFront', 'educationPlayerFlashMeta', 'educationPlayerStatus',
  'educationPlayerContextTopic', 'educationPlayerContextCourse', 'educationPlayerFlashCard',
  'educationPlayerFlashcardPanel', 'educationPlayerModeFlashcardBtn', 'educationPlayerModeQuizBtn',
  'educationPlayerModeTestBtn', 'educationPlayerModeProgressBtn',
];
const HIDDEN_IDS = [
  'educationPlayerFlashBack', 'educationPlayerFlashRevealBtn', 'educationPlayerFlashGradeRow',
  'educationPlayerQuizPanel', 'educationPlayerTestPanel', 'educationPlayerProgressPanel',
];

const DECK = [
  { item_id: 'q1', prompt: 'What is Raft?', expected_answer: 'A consensus algorithm', topic: 'raft' },
  { item_id: 'q2', prompt: 'Who leads?', expected_answer: 'The leader', topic: 'raft' },
];
const CTX = { agentId: 'tutor', topic: '', courseId: '' };

describe('CARD-464 Education Studio players', () => {
  let els;
  let fetchMock;
  let reduced;
  let players;
  let prevDocument;
  let prevWindow;

  beforeEach(async () => {
    vi.resetModules();
    els = {};
    IDS.forEach((id) => { els[id] = makeEl(id); });
    HIDDEN_IDS.forEach((id) => { els[id] = makeEl(id, { hidden: true }); });
    prevDocument = globalThis.document;
    prevWindow = globalThis.window;
    globalThis.document = { getElementById: (id) => els[id] || null };
    reduced = false;
    globalThis.window = { matchMedia: () => ({ matches: reduced }) };
    fetchMock = vi.fn(async (url) => {
      if (String(url).startsWith('/api/education/mastery/due')) {
        return { ok: true, json: async () => ({ items: DECK }) };
      }
      if (String(url).startsWith('/api/education/quiz/grade')) {
        return { ok: true, json: async () => ({ correct: true, grade: 'pass', next_due: '2026-10-04' }) };
      }
      return { ok: true, json: async () => ({ items: [] }) };
    });
    globalThis.fetch = fetchMock;
    players = await import('../../../src/web/static/modules/studios/education_players.js');
  });

  afterEach(() => {
    globalThis.document = prevDocument;
    globalThis.window = prevWindow;
    vi.restoreAllMocks();
  });

  it('[REQ-464-002] the answer is not on the card and Know / Miss stay hidden until the flip', async () => {
    const res = await players.startFlashcardDeck({ context: CTX, toast: () => {} });
    expect(res.ok).toBe(true);
    expect(els.educationPlayerFlashFront.textContent).toBe('What is Raft?');
    expect(els.educationPlayerFlashBack.textContent).toBe('');
    expect(els.educationPlayerFlashBack.classList.contains('hidden')).toBe(true);
    expect(els.educationPlayerFlashGradeRow.classList.contains('hidden')).toBe(true);
    expect(els.educationPlayerFlashCard.classList.contains('is-flipped')).toBe(false);
    expect(els.educationPlayerFlashMeta.textContent).toContain('1/2');
  });

  it('[REQ-464-002] flipping shows the back and the grade row; flipping again turns it back', async () => {
    await players.startFlashcardDeck({ context: CTX, toast: () => {} });
    expect(players.flipFlashcard()).toBe(true);
    expect(els.educationPlayerFlashCard.classList.contains('is-flipped')).toBe(true);
    expect(els.educationPlayerFlashCard.getAttribute('aria-pressed')).toBe('true');
    expect(els.educationPlayerFlashBack.textContent).toBe('A consensus algorithm');
    expect(els.educationPlayerFlashBack.classList.contains('hidden')).toBe(false);
    expect(els.educationPlayerFlashGradeRow.classList.contains('hidden')).toBe(false);
    players.flipFlashcard();
    expect(els.educationPlayerFlashCard.classList.contains('is-flipped')).toBe(false);
    expect(els.educationPlayerFlashGradeRow.classList.contains('hidden')).toBe(false);
  });

  it('[REQ-464-004] grading after the flip writes the ledger once and shows the next card face down', async () => {
    await players.startFlashcardDeck({ context: CTX, toast: () => {} });
    const early = await players.gradeFlashcard({ context: CTX, toast: () => {}, know: true });
    expect(early.success).toBe(false);
    expect(fetchMock.mock.calls.filter(([u]) => String(u).includes('quiz/grade'))).toHaveLength(0);
    players.flipFlashcard();
    const graded = await players.gradeFlashcard({ context: CTX, toast: () => {}, know: true });
    expect(graded.success).toBe(true);
    const gradeCalls = fetchMock.mock.calls.filter(([u]) => String(u).includes('quiz/grade'));
    expect(gradeCalls).toHaveLength(1);
    expect(JSON.parse(gradeCalls[0][1].body).item_id).toBe('q1');
    expect(els.educationPlayerFlashFront.textContent).toBe('Who leads?');
    expect(els.educationPlayerFlashCard.classList.contains('is-flipped')).toBe(false);
    expect(els.educationPlayerFlashBack.textContent).toBe('');
    expect(els.educationPlayerFlashGradeRow.classList.contains('hidden')).toBe(true);
  });

  it('[REQ-464-003] the flip animates unless the OS asks for reduced motion', async () => {
    await players.startFlashcardDeck({ context: CTX, toast: () => {} });
    players.flipFlashcard();
    expect(els.educationPlayerFlashCard.classList.contains('edu-flip-animated')).toBe(true);
    reduced = true;
    expect(players.prefersReducedMotion()).toBe(true);
    players.flipFlashcard();
    expect(els.educationPlayerFlashCard.classList.contains('edu-flip-animated')).toBe(false);
  });

  it('[REQ-464-002] Space flips only on the Flashcards tab and never while typing or on a button', () => {
    const key = (tagName, extra = {}) => ({ key: ' ', code: 'Space', target: { tagName }, defaultPrevented: false, ...extra });
    expect(players.shouldFlipOnKey(key('DIV'), { mode: 'flashcard', studioVisible: true })).toBe(true);
    expect(players.shouldFlipOnKey(key('BODY'), { mode: 'flashcard', studioVisible: true })).toBe(true);
    expect(players.shouldFlipOnKey(key('TEXTAREA'), { mode: 'flashcard', studioVisible: true })).toBe(false);
    expect(players.shouldFlipOnKey(key('INPUT'), { mode: 'flashcard', studioVisible: true })).toBe(false);
    expect(players.shouldFlipOnKey(key('BUTTON'), { mode: 'flashcard', studioVisible: true })).toBe(false);
    expect(players.shouldFlipOnKey(key('DIV'), { mode: 'quiz', studioVisible: true })).toBe(false);
    expect(players.shouldFlipOnKey(key('DIV'), { mode: 'flashcard', studioVisible: false })).toBe(false);
    expect(players.shouldFlipOnKey(key('DIV', { ctrlKey: true }), { mode: 'flashcard', studioVisible: true })).toBe(false);
    expect(players.shouldFlipOnKey({ key: 'a', target: { tagName: 'DIV' } }, { mode: 'flashcard', studioVisible: true })).toBe(false);
  });

  it('[REQ-464-005] Progress is a player tab; it hides the other players', () => {
    players.setPlayerMode('progress');
    expect(players.getPlayerMode()).toBe('progress');
    expect(els.educationPlayerProgressPanel.classList.contains('hidden')).toBe(false);
    expect(els.educationPlayerFlashcardPanel.classList.contains('hidden')).toBe(true);
    expect(els.educationPlayerModeProgressBtn.getAttribute('aria-pressed')).toBe('true');
    expect(els.educationPlayerModeFlashcardBtn.getAttribute('aria-pressed')).toBe('false');
  });
});

describe('CARD-464 page layout', () => {
  const html = loadPageHtml();
  const section = html.slice(html.indexOf('id="view-education"'), html.indexOf('<!-- ==================== VIEW 9: CAPABILITIES'));
  const opStart = section.indexOf('id="educationOperatorConsole"');
  const playersStart = section.indexOf('id="educationPlayersConsole"');

  it('[REQ-464-001] the players region fills the space below the operator bar', () => {
    expect(playersStart).toBeGreaterThan(opStart);
    expect(section).toMatch(/id="educationPlayersConsole"[^>]*class="[^"]*flex-1[^"]*min-h-0/);
    expect(section).toMatch(/id="educationPlayerFlashcardPanel"[^>]*class="[^"]*flex-1/);
  });

  it('[REQ-464-001] the card sizes to the space left so Flip / Know / Miss never need scrolling (v2)', () => {
    expect(section).toMatch(/id="educationPlayerFlashcardPanel"[^>]*class="[^"]*flex-1 min-h-0/);
    expect(section).toMatch(/id="educationPlayerFlashScene"[^>]*class="[^"]*flex-1/);
    expect(section).toMatch(/id="educationPlayerFlashGradeRow"[^>]*class="[^"]*shrink-0/);
    const css = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/css/studios.css'), 'utf-8');
    const card = css.slice(css.indexOf('.edu-flip-card {'), css.indexOf('}', css.indexOf('.edu-flip-card {')));
    expect(card).toContain('min-height: 0');
    expect(card).not.toMatch(/min-height:\s*\d+rem/);
  });

  it('[REQ-464-005] one progress view: inside the players, none in the operator bar', () => {
    const progress = section.indexOf('id="educationOperatorProgressPanel"');
    expect(progress).toBeGreaterThan(playersStart);
    expect(section.split('id="educationOperatorProgressPanel"').length).toBe(2);
    expect(section).toContain('id="educationPlayerModeProgressBtn"');
    expect(section).toContain('id="educationOperatorProgressBtn"');
    expect(section).not.toContain('id="educationOperatorProgressHideBtn"');
  });

  it('[REQ-464-002] the flashcard is one focusable card with front and back faces', () => {
    expect(section).toMatch(/id="educationPlayerFlashCard"[^>]*tabindex="0"/);
    const card = section.indexOf('id="educationPlayerFlashCard"');
    expect(section.indexOf('id="educationPlayerFlashFront"')).toBeGreaterThan(card);
    expect(section.indexOf('id="educationPlayerFlashBack"')).toBeGreaterThan(card);
  });

  it('[REQ-464-006] quiz and test take multi-line answers with larger prompts', () => {
    expect(section).toMatch(/<textarea id="educationPlayerQuizAnswer"/);
    expect(section).toMatch(/<textarea id="educationPlayerTestAnswer"/);
    expect(section).toMatch(/id="educationPlayerQuizPrompt"[^>]*class="[^"]*text-base[^"]*min-h-\[8rem\]/);
    expect(section).toMatch(/id="educationPlayerTestPrompt"[^>]*class="[^"]*text-base[^"]*min-h-\[8rem\]/);
  });
});
