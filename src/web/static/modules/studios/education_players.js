/**
 * CARD-448: Education Studio flashcard / quiz / test players.
 * Durable Learning OS grades via POST /api/education/quiz/grade,
 * GET /api/education/quiz/next, GET /api/education/mastery/due.
 * Flashcards: front-only then reveal/grade (not both-sides dump as only mode).
 * Keeps CARD-447 operator console; Tutor remains coach. Does not retire Studio.
 */

import { $, safeCreateIcons } from '../dom.js';
import { showToast } from '../ui/toast.js';
import {
  STUDY_TUTOR_AGENT_ID,
  loadStudioActiveEducationContext,
  fetchSelectedEducationContext,
} from './study_entry.js';

export const EDUCATION_PLAYER_GRADE_HTTP = 'POST /api/education/quiz/grade';
export const EDUCATION_PLAYER_QUIZ_NEXT_HTTP = 'GET /api/education/quiz/next';
export const EDUCATION_PLAYER_DUE_HTTP = 'GET /api/education/mastery/due';
export const EDUCATION_PLAYER_MODES = ['flashcard', 'quiz', 'test'];

/** @type {'flashcard'|'quiz'|'test'} */
let _mode = 'flashcard';

const flashState = { item: null, revealed: false, deck: [], index: 0 };
const quizState = { item: null };
const testState = { items: [], index: 0, results: [], active: false, limit: 5 };

function _el(id) {
  return typeof $ === 'function' ? $(id) : null;
}

function _toastFn(explicit) {
  return typeof explicit === 'function' ? explicit : showToast;
}

export function resolvePlayerContext(selected) {
  const sel = selected || loadStudioActiveEducationContext() || {};
  const topic = String(sel.topic || '').trim();
  const courseId = String(sel.course_id || sel.courseId || '').trim();
  const agentId =
    String(sel.agent_id || sel.agentId || STUDY_TUTOR_AGENT_ID || 'tutor').trim() || 'tutor';
  return { topic, courseId, agentId, source: topic ? 'education_studio' : 'default' };
}

export async function loadPlayerStudioContext() {
  try {
    const data = await fetchSelectedEducationContext();
    const selected = data && (data.selected || data);
    if (selected && (selected.topic || selected.course_id || selected.agent_id)) {
      return resolvePlayerContext(selected);
    }
  } catch (err) {
    console.warn('[Education Players] selected context fetch failed:', err);
  }
  return resolvePlayerContext(loadStudioActiveEducationContext());
}

/**
 * Durable grade write. Failures return success=false and never set correct=true.
 */
export async function gradePlayerItem({ agentId, item, answer }) {
  const it = item || {};
  const itemId = String(it.item_id || '').trim();
  if (!itemId) {
    return {
      success: false,
      durable: false,
      correct: false,
      error: 'missing_item_id',
      fake_pass: false,
      http_contract: EDUCATION_PLAYER_GRADE_HTTP,
    };
  }
  try {
    const res = await fetch('/api/education/quiz/grade', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        agent_id: agentId || STUDY_TUTOR_AGENT_ID,
        item_id: itemId,
        answer: answer == null ? '' : String(answer),
        topic: it.topic || undefined,
        wiki_path: it.wiki_path || undefined,
        prompt: it._ledger_prompt || it.prompt || undefined,
        expected_answer: it.expected_answer || undefined,
      }),
    });
    if (!res.ok) {
      let detail = '';
      try { detail = await res.text(); } catch (_) { /* ignore */ }
      return {
        success: false,
        durable: false,
        correct: false,
        error: 'HTTP ' + res.status + (detail ? ': ' + detail.slice(0, 180) : ''),
        http_contract: EDUCATION_PLAYER_GRADE_HTTP,
        fake_pass: false,
      };
    }
    const data = await res.json();
    const correct = data && data.correct === true;
    return {
      success: true,
      durable: true,
      correct,
      grade: data.grade || (correct ? 'pass' : 'miss'),
      next_due: data.next_due || null,
      item_id: itemId,
      http_contract: EDUCATION_PLAYER_GRADE_HTTP,
      raw: data,
      fake_pass: false,
    };
  } catch (err) {
    return {
      success: false,
      durable: false,
      correct: false,
      error: String(err && err.message ? err.message : err),
      http_contract: EDUCATION_PLAYER_GRADE_HTTP,
      fake_pass: false,
    };
  }
}

export async function fetchPlayerDueDeck({ agentId, limit = 10 } = {}) {
  const lim = Math.max(1, Math.min(Number(limit) || 10, 50));
  const res = await fetch(
    '/api/education/mastery/due?agent_id=' + encodeURIComponent(agentId || STUDY_TUTOR_AGENT_ID),
  );
  if (!res.ok) throw new Error('mastery/due HTTP ' + res.status);
  const data = await res.json();
  const items = Array.isArray(data.items) ? data.items.slice(0, lim) : [];
  return { items, count: items.length, http_contract: EDUCATION_PLAYER_DUE_HTTP, agent_id: data.agent_id };
}

export async function fetchPlayerQuizDeck({ agentId, topic = '', limit = 5 } = {}) {
  const lim = Math.max(1, Math.min(Number(limit) || 5, 50));
  let url =
    '/api/education/quiz/next?agent_id=' +
    encodeURIComponent(agentId || STUDY_TUTOR_AGENT_ID) +
    '&limit=' +
    lim;
  if (topic) url += '&topic=' + encodeURIComponent(topic);
  const res = await fetch(url);
  if (!res.ok) throw new Error('quiz/next HTTP ' + res.status);
  const data = await res.json();
  const items = Array.isArray(data.items) ? data.items : [];
  return {
    items,
    count: items.length,
    http_contract: EDUCATION_PLAYER_QUIZ_NEXT_HTTP,
    delivery: data.delivery || null,
  };
}

function _setStatus(text, kind) {
  const el = _el('educationPlayerStatus');
  if (!el) return;
  el.textContent = text || '';
  const colors = {
    error: 'text-rose-300',
    success: 'text-emerald-300',
    warn: 'text-amber-300',
    info: 'text-slate-400',
  };
  el.className = 'text-[11px] font-medium min-h-[1rem] ' + (colors[kind] || colors.info);
}

function _setContextChrome(ctx) {
  const topicEl = _el('educationPlayerContextTopic');
  const courseEl = _el('educationPlayerContextCourse');
  if (topicEl) topicEl.textContent = (ctx && ctx.topic) || '-';
  if (courseEl) courseEl.textContent = (ctx && ctx.courseId) || '-';
}

export function setPlayerMode(mode) {
  _mode = EDUCATION_PLAYER_MODES.includes(mode) ? mode : 'flashcard';
  const map = {
    flashcard: 'educationPlayerFlashcardPanel',
    quiz: 'educationPlayerQuizPanel',
    test: 'educationPlayerTestPanel',
  };
  Object.keys(map).forEach((m) => {
    const panel = _el(map[m]);
    if (!panel) return;
    if (m === _mode) panel.classList.remove('hidden');
    else panel.classList.add('hidden');
  });
  const btnMap = {
    flashcard: 'educationPlayerModeFlashcardBtn',
    quiz: 'educationPlayerModeQuizBtn',
    test: 'educationPlayerModeTestBtn',
  };
  Object.keys(btnMap).forEach((m) => {
    const btn = _el(btnMap[m]);
    if (!btn) return;
    if (m === _mode) {
      btn.classList.add('ring-1', 'ring-emerald-400/60');
      btn.setAttribute('aria-pressed', 'true');
    } else {
      btn.classList.remove('ring-1', 'ring-emerald-400/60');
      btn.setAttribute('aria-pressed', 'false');
    }
  });
}

function _normalizeItem(raw) {
  if (!raw) return null;
  return {
    ...raw,
    item_id: raw.item_id,
    prompt: raw.presentation_prompt || raw.prompt,
    _ledger_prompt: raw.prompt,
    expected_answer: raw.expected_answer,
    topic: raw.topic,
    wiki_path: raw.wiki_path,
  };
}

function _renderFlashcardView() {
  const frontEl = _el('educationPlayerFlashFront');
  const backEl = _el('educationPlayerFlashBack');
  const metaEl = _el('educationPlayerFlashMeta');
  const revealBtn = _el('educationPlayerFlashRevealBtn');
  const gradeRow = _el('educationPlayerFlashGradeRow');
  const item = flashState.item;
  if (!item) {
    if (frontEl) frontEl.textContent = 'No flashcard loaded. Start a deck from due mastery.';
    if (backEl) {
      backEl.textContent = '';
      backEl.classList.add('hidden');
    }
    if (metaEl) metaEl.textContent = '';
    if (revealBtn) revealBtn.classList.add('hidden');
    if (gradeRow) gradeRow.classList.add('hidden');
    flashState.revealed = false;
    return;
  }
  // Front-only until reveal — do not dump both sides as the only mode [CARD-448]
  if (frontEl) frontEl.textContent = item.prompt || '(empty front)';
  if (metaEl) {
    metaEl.textContent =
      (item.item_id || '') +
      ' · ' +
      (item.topic || '') +
      ' · card ' +
      (flashState.index + 1) +
      '/' +
      Math.max(flashState.deck.length, 1);
  }
  if (!flashState.revealed) {
    if (backEl) {
      backEl.textContent = '';
      backEl.classList.add('hidden');
      backEl.setAttribute('aria-hidden', 'true');
    }
    if (revealBtn) revealBtn.classList.remove('hidden');
    if (gradeRow) gradeRow.classList.add('hidden');
  } else {
    if (backEl) {
      backEl.textContent = item.expected_answer || '(no back text on ledger)';
      backEl.classList.remove('hidden');
      backEl.setAttribute('aria-hidden', 'false');
    }
    if (revealBtn) revealBtn.classList.add('hidden');
    if (gradeRow) gradeRow.classList.remove('hidden');
  }
}

function _renderQuizView() {
  const promptEl = _el('educationPlayerQuizPrompt');
  const input = _el('educationPlayerQuizAnswer');
  const resultEl = _el('educationPlayerQuizResult');
  const item = quizState.item;
  if (!item) {
    if (promptEl) promptEl.textContent = 'No quiz item loaded. Start quiz player.';
    if (input) input.value = '';
    if (resultEl) resultEl.textContent = '';
    return;
  }
  if (promptEl) promptEl.textContent = item.prompt || '(empty prompt)';
  if (input) input.value = '';
  if (resultEl) resultEl.textContent = '';
}

function _renderTestView() {
  const promptEl = _el('educationPlayerTestPrompt');
  const input = _el('educationPlayerTestAnswer');
  const progressEl = _el('educationPlayerTestProgress');
  const resultEl = _el('educationPlayerTestResult');
  const summaryEl = _el('educationPlayerTestSummary');
  if (!testState.active || !testState.items.length) {
    if (promptEl) promptEl.textContent = 'No test session. Start a multi-item test.';
    if (progressEl) progressEl.textContent = '';
    if (input) input.value = '';
    if (resultEl) resultEl.textContent = '';
    if (summaryEl) summaryEl.textContent = '';
    return;
  }
  if (testState.index >= testState.items.length) {
    if (promptEl) promptEl.textContent = 'Test complete.';
    if (progressEl) {
      progressEl.textContent = 'Done ' + testState.results.length + '/' + testState.items.length;
    }
    const passes = testState.results.filter((r) => r.correct).length;
    const fails = testState.results.filter((r) => r.success && !r.correct).length;
    const errors = testState.results.filter((r) => !r.success).length;
    if (summaryEl) {
      summaryEl.textContent =
        'Durable results: ' +
        passes +
        ' pass · ' +
        fails +
        ' miss · ' +
        errors +
        ' error (ledger via quiz/grade)';
    }
    if (input) input.value = '';
    return;
  }
  const item = testState.items[testState.index];
  if (promptEl) promptEl.textContent = item.prompt || '(empty)';
  if (progressEl) {
    progressEl.textContent = 'Item ' + (testState.index + 1) + ' of ' + testState.items.length;
  }
  if (input) input.value = '';
  if (resultEl) resultEl.textContent = '';
  if (summaryEl) summaryEl.textContent = '';
}

export async function startFlashcardDeck(opts) {
  opts = opts || {};
  const toast = _toastFn(opts.toast);
  const ctx = opts.context || (await loadPlayerStudioContext());
  _setContextChrome(ctx);
  setPlayerMode('flashcard');
  try {
    let deck = [];
    try {
      const due = await fetchPlayerDueDeck({ agentId: ctx.agentId, limit: opts.limit || 10 });
      deck = due.items || [];
    } catch (err) {
      console.warn('[Education Players] due deck failed, trying quiz/next', err);
    }
    if (!deck.length) {
      const quiz = await fetchPlayerQuizDeck({
        agentId: ctx.agentId,
        topic: ctx.topic || '',
        limit: opts.limit || 10,
      });
      deck = quiz.items || [];
    }
    if (ctx.topic && deck.length) {
      const filtered = deck.filter(
        (it) => String(it.topic || '').toLowerCase() === ctx.topic.toLowerCase(),
      );
      if (filtered.length) deck = filtered;
    }
    flashState.deck = deck.map(_normalizeItem).filter(Boolean);
    flashState.index = 0;
    flashState.revealed = false;
    flashState.item = flashState.deck[0] || null;
    _renderFlashcardView();
    if (!flashState.deck.length) {
      _setStatus('No due/quiz items for flashcard deck.', 'warn');
      toast('No flashcard items available', 'info');
      return { ok: false, count: 0 };
    }
    _setStatus(
      'Flashcard deck loaded (' +
        flashState.deck.length +
        '). Front only — reveal before grade.',
      'success',
    );
    toast('Flashcard deck: ' + flashState.deck.length + ' card(s)', 'success');
    return { ok: true, count: flashState.deck.length };
  } catch (err) {
    console.error('[Education Players] startFlashcardDeck failed:', err);
    _setStatus('Flashcard start failed: ' + (err.message || err), 'error');
    toast('Flashcard deck failed — no fake progress', 'error');
    return { ok: false, error: String(err.message || err) };
  }
}

export function revealFlashcard() {
  if (!flashState.item) {
    _setStatus('Load a flashcard first.', 'warn');
    return false;
  }
  flashState.revealed = true;
  _renderFlashcardView();
  _setStatus('Back revealed. Grade honestly (Know / Miss) — writes Learning OS ledger.', 'info');
  return true;
}

export async function gradeFlashcard(opts) {
  opts = opts || {};
  const toast = _toastFn(opts.toast);
  const ctx = opts.context || (await loadPlayerStudioContext());
  if (!flashState.item) {
    toast('No flashcard to grade', 'error');
    return { success: false, correct: false, fake_pass: false };
  }
  if (!flashState.revealed && opts.requireReveal !== false) {
    toast('Reveal the back before grading', 'info');
    return { success: false, correct: false, error: 'not_revealed', fake_pass: false };
  }
  let answer = opts.answer;
  if (answer == null) {
    answer = opts.know === true ? String(flashState.item.expected_answer || '') : '';
  }
  const graded = await gradePlayerItem({
    agentId: ctx.agentId,
    item: flashState.item,
    answer,
  });
  if (!graded.success) {
    _setStatus('Grade failed — no fake pass. ' + (graded.error || ''), 'error');
    toast('Flashcard grade failed', 'error');
    return graded;
  }
  _setStatus(
    graded.correct
      ? 'Pass (durable). Next due ' + (graded.next_due || '')
      : 'Miss (durable). Next due ' + (graded.next_due || ''),
    graded.correct ? 'success' : 'warn',
  );
  toast(
    graded.correct ? 'Flashcard pass (ledger)' : 'Flashcard miss (ledger)',
    graded.correct ? 'success' : 'info',
  );
  flashState.index += 1;
  flashState.revealed = false;
  flashState.item = flashState.deck[flashState.index] || null;
  _renderFlashcardView();
  if (!flashState.item) _setStatus('Deck finished. Progress is on mastery/due.', 'success');
  return graded;
}

export async function startQuizPlayer(opts) {
  opts = opts || {};
  const toast = _toastFn(opts.toast);
  const ctx = opts.context || (await loadPlayerStudioContext());
  _setContextChrome(ctx);
  setPlayerMode('quiz');
  try {
    const data = await fetchPlayerQuizDeck({
      agentId: ctx.agentId,
      topic: ctx.topic || '',
      limit: opts.limit || 5,
    });
    const items = data.items || [];
    quizState.item = items[0] ? _normalizeItem(items[0]) : null;
    _renderQuizView();
    if (!quizState.item) {
      _setStatus('No quiz items from Learning OS.', 'warn');
      toast('No quiz items', 'info');
      return { ok: false, count: 0 };
    }
    _setStatus(
      'Quiz item ' + quizState.item.item_id + ' (topic context: ' + (ctx.topic || 'any') + ')',
      'success',
    );
    toast('Quiz player ready', 'success');
    return { ok: true, item: quizState.item };
  } catch (err) {
    console.error('[Education Players] startQuizPlayer failed:', err);
    quizState.item = null;
    _renderQuizView();
    _setStatus('Quiz start failed: ' + (err.message || err), 'error');
    toast('Quiz player failed — no fake score', 'error');
    return { ok: false, error: String(err.message || err) };
  }
}

export async function gradeQuizPlayer(opts) {
  opts = opts || {};
  const toast = _toastFn(opts.toast);
  const ctx = opts.context || (await loadPlayerStudioContext());
  const input = _el('educationPlayerQuizAnswer');
  const answer = opts.answer != null ? opts.answer : input ? input.value : '';
  if (!quizState.item) {
    toast('Load a quiz item first', 'error');
    return { success: false, correct: false, fake_pass: false };
  }
  const graded = await gradePlayerItem({
    agentId: ctx.agentId,
    item: quizState.item,
    answer,
  });
  const resultEl = _el('educationPlayerQuizResult');
  if (!graded.success) {
    if (resultEl) resultEl.textContent = 'Grade failed — no fake pass. ' + (graded.error || '');
    _setStatus('Quiz grade failed: ' + (graded.error || ''), 'error');
    toast('Quiz grade failed', 'error');
    return graded;
  }
  if (resultEl) {
    resultEl.textContent = graded.correct
      ? 'Pass — next due ' + (graded.next_due || '')
      : 'Miss — next due ' + (graded.next_due || '');
  }
  _setStatus(
    graded.correct ? 'Quiz pass (durable ledger)' : 'Quiz miss (durable ledger)',
    graded.correct ? 'success' : 'warn',
  );
  toast(graded.correct ? 'Pass (binary grade)' : 'Miss scheduled', graded.correct ? 'success' : 'info');
  return graded;
}

export async function startTestSession(opts) {
  opts = opts || {};
  const toast = _toastFn(opts.toast);
  const ctx = opts.context || (await loadPlayerStudioContext());
  _setContextChrome(ctx);
  setPlayerMode('test');
  const limit = Math.max(2, Math.min(Number(opts.limit) || testState.limit || 5, 20));
  testState.limit = limit;
  try {
    const data = await fetchPlayerQuizDeck({
      agentId: ctx.agentId,
      topic: ctx.topic || '',
      limit,
    });
    const items = (data.items || []).map(_normalizeItem).filter(Boolean);
    testState.items = items;
    testState.index = 0;
    testState.results = [];
    testState.active = items.length > 0;
    _renderTestView();
    if (!items.length) {
      _setStatus('No items for test session.', 'warn');
      toast('No test items', 'info');
      return { ok: false, count: 0 };
    }
    _setStatus('Test session: ' + items.length + ' item(s). Each grade writes Learning OS.', 'success');
    toast('Test started (' + items.length + ')', 'success');
    return { ok: true, count: items.length };
  } catch (err) {
    console.error('[Education Players] startTestSession failed:', err);
    testState.active = false;
    testState.items = [];
    _renderTestView();
    _setStatus('Test start failed: ' + (err.message || err), 'error');
    toast('Test session failed — no fake results', 'error');
    return { ok: false, error: String(err.message || err) };
  }
}

export async function gradeTestItem(opts) {
  opts = opts || {};
  const toast = _toastFn(opts.toast);
  const ctx = opts.context || (await loadPlayerStudioContext());
  if (!testState.active || testState.index >= testState.items.length) {
    toast('No active test item', 'error');
    return { success: false, correct: false, fake_pass: false };
  }
  const item = testState.items[testState.index];
  const input = _el('educationPlayerTestAnswer');
  const answer = opts.answer != null ? opts.answer : input ? input.value : '';
  const graded = await gradePlayerItem({ agentId: ctx.agentId, item, answer });
  const resultEl = _el('educationPlayerTestResult');
  testState.results.push({
    item_id: item.item_id,
    success: graded.success,
    correct: graded.correct === true,
    next_due: graded.next_due || null,
    error: graded.error || null,
  });
  if (!graded.success) {
    if (resultEl) resultEl.textContent = 'Grade failed — no fake pass. ' + (graded.error || '');
    _setStatus('Test item grade failed: ' + (graded.error || ''), 'error');
    toast('Test grade failed', 'error');
  } else {
    if (resultEl) {
      resultEl.textContent = graded.correct
        ? 'Pass — next due ' + (graded.next_due || '')
        : 'Miss — next due ' + (graded.next_due || '');
    }
    toast(graded.correct ? 'Test item pass' : 'Test item miss', graded.correct ? 'success' : 'info');
  }
  testState.index += 1;
  _renderTestView();
  if (testState.index >= testState.items.length) {
    const passes = testState.results.filter((r) => r.correct).length;
    _setStatus(
      'Test complete. Durable ' + passes + '/' + testState.results.length + ' pass on ledger.',
      'success',
    );
  }
  return graded;
}

export function initEducationStudioPlayers(callbacks) {
  callbacks = callbacks || {};
  const toast = _toastFn(callbacks.showToast);

  loadPlayerStudioContext()
    .then((ctx) => _setContextChrome(ctx))
    .catch((err) => console.warn('[Education Players] context hydrate failed', err));

  setPlayerMode('flashcard');
  _renderFlashcardView();
  _renderQuizView();
  _renderTestView();

  const modeFlash = _el('educationPlayerModeFlashcardBtn');
  const modeQuiz = _el('educationPlayerModeQuizBtn');
  const modeTest = _el('educationPlayerModeTestBtn');
  if (modeFlash) {
    modeFlash.addEventListener('click', (e) => {
      e.preventDefault();
      setPlayerMode('flashcard');
    });
  }
  if (modeQuiz) {
    modeQuiz.addEventListener('click', (e) => {
      e.preventDefault();
      setPlayerMode('quiz');
    });
  }
  if (modeTest) {
    modeTest.addEventListener('click', (e) => {
      e.preventDefault();
      setPlayerMode('test');
    });
  }

  const flashStart = _el('educationPlayerFlashStartBtn');
  if (flashStart) {
    flashStart.addEventListener('click', async (e) => {
      e.preventDefault();
      await startFlashcardDeck({ toast });
    });
  }
  const flashReveal = _el('educationPlayerFlashRevealBtn');
  if (flashReveal) {
    flashReveal.addEventListener('click', (e) => {
      e.preventDefault();
      revealFlashcard();
    });
  }
  const flashKnow = _el('educationPlayerFlashKnowBtn');
  if (flashKnow) {
    flashKnow.addEventListener('click', async (e) => {
      e.preventDefault();
      await gradeFlashcard({ toast, know: true });
    });
  }
  const flashMiss = _el('educationPlayerFlashMissBtn');
  if (flashMiss) {
    flashMiss.addEventListener('click', async (e) => {
      e.preventDefault();
      await gradeFlashcard({ toast, know: false });
    });
  }

  const quizStart = _el('educationPlayerQuizStartBtn');
  if (quizStart) {
    quizStart.addEventListener('click', async (e) => {
      e.preventDefault();
      await startQuizPlayer({ toast });
    });
  }
  const quizGrade = _el('educationPlayerQuizGradeBtn');
  if (quizGrade) {
    quizGrade.addEventListener('click', async (e) => {
      e.preventDefault();
      await gradeQuizPlayer({ toast });
    });
  }
  const quizNext = _el('educationPlayerQuizNextBtn');
  if (quizNext) {
    quizNext.addEventListener('click', async (e) => {
      e.preventDefault();
      await startQuizPlayer({ toast });
    });
  }

  const testStart = _el('educationPlayerTestStartBtn');
  if (testStart) {
    testStart.addEventListener('click', async (e) => {
      e.preventDefault();
      await startTestSession({ toast });
    });
  }
  const testGrade = _el('educationPlayerTestGradeBtn');
  if (testGrade) {
    testGrade.addEventListener('click', async (e) => {
      e.preventDefault();
      await gradeTestItem({ toast });
    });
  }

  try {
    safeCreateIcons();
  } catch (_) {
    /* ignore */
  }

  return {
    setPlayerMode,
    startFlashcardDeck,
    revealFlashcard,
    gradeFlashcard,
    startQuizPlayer,
    gradeQuizPlayer,
    startTestSession,
    gradeTestItem,
    gradePlayerItem,
    loadPlayerStudioContext,
    EDUCATION_PLAYER_GRADE_HTTP,
    EDUCATION_PLAYER_MODES,
  };
}
