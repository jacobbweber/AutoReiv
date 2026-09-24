/**
 * CARD-437: Study Entry = Tutor education mode (thin shell).
 * CARD-439: Due reviews surface in Tutor education mode (Learning OS mastery/due).
 * Reuses Chat + Tutor agent + Learning OS course APIs. Does not retire Education Studio.
 */

import { $, safeCreateIcons } from '../dom.js';
import { showToast } from '../ui/toast.js';

export const STUDY_LAST_TOPIC_KEY = 'autoreiv.study.last_topic.v1';
export const STUDY_EDUCATION_MODE_KEY = 'autoreiv.study.education_mode.v1';
export const STUDY_TUTOR_AGENT_ID = 'tutor';
export const STUDY_LEARNING_OS_SKILL = 'start-resume-topic';
export const STUDY_DUE_REVIEW_SKILL = 'due-review';
export const STUDY_EDUCATION_MODE_MARKER = '[Tutor Education Mode]';

/** @type {{ active: boolean, topic: string, courseId: string, skillId: string, agentId: string } | null} */
let _activeBinding = null;

export function getStudyEducationModeBinding() {
  return _activeBinding ? { ..._activeBinding } : null;
}

export function isStudyEducationModeActive() {
  return !!( _activeBinding && _activeBinding.active);
}

export function loadLastStudyTopic() {
  try {
    const raw = localStorage.getItem(STUDY_LAST_TOPIC_KEY);
    return raw ? String(raw).trim() : '';
  } catch {
    return '';
  }
}

export function saveLastStudyTopic(topic) {
  const t = String(topic || '').trim();
  if (!t) return;
  try {
    localStorage.setItem(STUDY_LAST_TOPIC_KEY, t);
  } catch {
    /* ignore quota */
  }
}

export function buildStudyEducationModePrompt(topic, courseId = '') {
  const t = String(topic || '').trim() || 'Active Study Topic';
  const courseBit = courseId ? ` course_id=${courseId}` : '';
  return (
    `${STUDY_EDUCATION_MODE_MARKER} skill=${STUDY_LEARNING_OS_SKILL}${courseBit}\n` +
    `Start or resume Learning OS course for topic "${t}". ` +
    `Use the named Learning OS skill "${STUDY_LEARNING_OS_SKILL}" (not open vibes). ` +
    `Guide me with Socratic tutoring inside that skill.`
  );
}

/**
 * Durable course start/resume for Study entry (Learning OS).
 * @param {string} topic
 * @param {string} [agentId]
 */
export async function startOrResumeStudyCourse(topic, agentId = STUDY_TUTOR_AGENT_ID) {
  const topicId = String(topic || '').trim();
  if (!topicId) {
    const err = new Error('topic is required for Study entry');
    err.code = 'STUDY_TOPIC_REQUIRED';
    throw err;
  }
  const res = await fetch('/api/education/course/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      agent_id: agentId || STUDY_TUTOR_AGENT_ID,
      topic_id: topicId,
    }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    throw new Error(`course/start ${res.status}${detail ? `: ${detail}` : ''}`);
  }
  return res.json();
}

/**
 * Assemble Tutor topic context for education mode.
 * @param {string} topic
 * @param {string} [agentId]
 */
export async function assembleStudyTutorContext(topic, agentId = STUDY_TUTOR_AGENT_ID) {
  const t = String(topic || '').trim();
  if (!t) {
    const err = new Error('topic is required for tutor context');
    err.code = 'STUDY_TOPIC_REQUIRED';
    throw err;
  }
  const res = await fetch('/api/education/tutor/context', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      agent_id: agentId || STUDY_TUTOR_AGENT_ID,
      topic: t,
    }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    throw new Error(`tutor/context ${res.status}${detail ? `: ${detail}` : ''}`);
  }
  return res.json();
}

export function renderStudyEducationModeChrome(binding) {
  const strip = $('chatEducationModeStrip');
  const topicEl = $('chatEducationModeTopic');
  const courseEl = $('chatEducationModeCourseId');
  const skillEl = $('chatEducationModeSkill');
  if (!strip) return;
  if (!binding || !binding.active) {
    strip.classList.add('hidden');
    strip.setAttribute('aria-hidden', 'true');
    return;
  }
  if (topicEl) topicEl.textContent = binding.topic || '—';
  if (courseEl) courseEl.textContent = binding.courseId || '—';
  if (skillEl) skillEl.textContent = binding.skillId || STUDY_LEARNING_OS_SKILL;
  strip.classList.remove('hidden');
  strip.setAttribute('aria-hidden', 'false');
  safeCreateIcons();
}

export function clearStudyEducationMode() {
  _activeBinding = null;
  try {
    localStorage.removeItem(STUDY_EDUCATION_MODE_KEY);
  } catch {
    /* ignore */
  }
  renderStudyEducationModeChrome(null);
  hideStudyDueReviewsPanel();
}

function _persistBinding(binding) {
  _activeBinding = binding;
  try {
    localStorage.setItem(STUDY_EDUCATION_MODE_KEY, JSON.stringify(binding));
  } catch {
    /* ignore */
  }
  renderStudyEducationModeChrome(binding);
}

/**
 * Prompt operator for topic; prefer last Study topic as default.
 * @returns {string|null} null if cancelled
 */
export function promptStudyTopic(defaultTopic = '') {
  const seed = String(defaultTopic || loadLastStudyTopic() || '').trim();
  const message =
    'Study topic (Tutor education mode / start-resume-topic).\n' +
    'Leave blank to cancel — Study will not open plain Chat without a topic.';
  const raw = typeof window !== 'undefined' && typeof window.prompt === 'function'
    ? window.prompt(message, seed)
    : null;
  if (raw === null) return null;
  return String(raw).trim();
}

/**
 * Thin Study entry: Chat + Tutor + education-mode rails + durable course bind.
 * @param {{
 *   topic?: string,
 *   switchTab?: (tab: string) => void,
 *   getChatCtrl?: () => any,
 *   toast?: (msg: string, type?: string) => void,
 *   skipPrompt?: boolean,
 * }} opts
 */

export function buildDueReviewPrompt(topic, courseId = '', dueCount = null) {
  const t = String(topic || '').trim() || 'Active Study Topic';
  const courseBit = courseId ? ` course_id=${courseId}` : '';
  const countBit =
    dueCount === null || dueCount === undefined
      ? ''
      : ` due_count=${Number(dueCount) || 0}`;
  return (
    `${STUDY_EDUCATION_MODE_MARKER} skill=${STUDY_DUE_REVIEW_SKILL}${courseBit}${countBit}\n` +
    `List and complete due SRS reviews for topic "${t}" using Learning OS skill "${STUDY_DUE_REVIEW_SKILL}". ` +
    `Call education_due_review_list (GET /api/education/mastery/due). If empty, say "No due reviews." honestly. ` +
    `When I answer a due item, call education_due_review_complete so the grade lands in education_mastery. ` +
    `Delivery profiles do not replace ledger/SRS.`
  );
}

/**
 * Fetch due reviews from Learning OS (not a client-only list).
 * @param {string} [agentId]
 * @returns {Promise<{ ok: boolean, items: any[], count: number, empty: boolean, empty_state: string, error?: string }>}
 */
export async function fetchStudyDueReviews(agentId = STUDY_TUTOR_AGENT_ID) {
  const aid = String(agentId || STUDY_TUTOR_AGENT_ID).trim() || STUDY_TUTOR_AGENT_ID;
  const res = await fetch(`/api/education/mastery/due?agent_id=${encodeURIComponent(aid)}`);
  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    return {
      ok: false,
      items: [],
      count: 0,
      empty: true,
      empty_state: 'Due list failed.',
      error: `mastery/due ${res.status}${detail ? `: ${detail}` : ''}`,
    };
  }
  const data = await res.json();
  const items = Array.isArray(data.items) ? data.items : [];
  const empty = items.length === 0;
  return {
    ok: true,
    items,
    count: items.length,
    empty,
    empty_state: empty ? 'No due reviews.' : '',
    http_contract: 'GET /api/education/mastery/due',
  };
}

function _escapeHtml(s) {
  return String(s || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function renderStudyDueReviewsPanel(payload) {
  const panel = $('chatEducationModeDuePanel');
  const listEl = $('chatEducationModeDueList');
  const countEl = $('chatEducationModeDueCount');
  if (!panel || !listEl) return;
  const items = (payload && Array.isArray(payload.items)) ? payload.items : [];
  const empty = !payload || payload.empty || items.length === 0;
  const failed = payload && payload.ok === false;
  if (countEl) {
    countEl.textContent = failed ? '!' : String(items.length);
  }
  if (failed) {
    listEl.innerHTML = `<div class="text-[11px] text-rose-300 px-1">${_escapeHtml(payload.error || 'Due list failed.')}</div>`;
  } else if (empty) {
    listEl.innerHTML = '<div class="text-[11px] text-slate-500 px-1">No due reviews.</div>';
  } else {
    listEl.innerHTML = items
      .map((it) => {
        const id = _escapeHtml(it.item_id || '');
        const topic = _escapeHtml(it.topic || '');
        const due = _escapeHtml(it.next_due || '');
        const prompt = _escapeHtml(it.prompt || '');
        return `<button type="button" class="chat-edu-due-item w-full text-left px-2 py-1.5 rounded-lg hover:bg-slate-800 border border-transparent hover:border-amber-900/40" data-item-id="${id}">
          <div class="text-[11px] font-medium text-slate-200 truncate">${topic}</div>
          <div class="text-[10px] text-slate-400 truncate">${prompt}</div>
          <div class="text-[10px] font-mono text-amber-300/80">due ${due}</div>
        </button>`;
      })
      .join('');
  }
  panel.classList.remove('hidden');
  panel.setAttribute('aria-hidden', 'false');
  safeCreateIcons();
}

export function hideStudyDueReviewsPanel() {
  if (typeof document === 'undefined' || !document.getElementById) return;
  const panel = document.getElementById('chatEducationModeDuePanel');
  if (!panel) return;
  panel.classList.add('hidden');
  panel.setAttribute('aria-hidden', 'true');
}

/**
 * Open due reviews inside Tutor education mode: skill=due-review + live mastery/due list.
 * @param {{ toast?: Function }} [opts]
 */
export async function openDueReviewsInEducationMode(opts = {}) {
  const toast = typeof opts.toast === 'function' ? opts.toast : showToast;
  let binding = getStudyEducationModeBinding();
  if (!binding || !binding.active || !binding.topic) {
    toast('Enter Study / Tutor education mode first (sidebar Study), then open Due reviews.', 'error');
    return { ok: false, error: 'EDUCATION_MODE_REQUIRED' };
  }

  const due = await fetchStudyDueReviews(binding.agentId || STUDY_TUTOR_AGENT_ID);
  if (!due.ok) {
    toast(`Due reviews failed: ${due.error || 'mastery/due error'}`, 'error');
    renderStudyDueReviewsPanel(due);
    return { ok: false, error: 'DUE_FETCH_FAILED', due };
  }

  binding = {
    ...binding,
    skillId: STUDY_DUE_REVIEW_SKILL,
  };
  _persistBinding(binding);

  const chatInput = $('chatInput');
  if (chatInput) {
    chatInput.value = buildDueReviewPrompt(binding.topic, binding.courseId, due.count);
    chatInput.focus();
  }

  renderStudyDueReviewsPanel(due);
  if (due.empty) {
    toast('No due reviews.', 'info');
  } else {
    toast(`Due reviews: ${due.count} item(s) from Learning OS mastery/due`, 'info');
  }
  return { ok: true, binding, due };
}


export async function enterTutorEducationMode(opts = {}) {
  const toast = typeof opts.toast === 'function' ? opts.toast : showToast;
  let topic = String(opts.topic || '').trim();
  if (!topic && !opts.skipPrompt) {
    topic = promptStudyTopic(loadLastStudyTopic()) || '';
  }
  if (!topic) {
    toast('Study needs a topic — education mode not started (no freeform Chat).', 'error');
    return { ok: false, error: 'STUDY_TOPIC_REQUIRED' };
  }

  let coursePayload = null;
  try {
    coursePayload = await startOrResumeStudyCourse(topic, STUDY_TUTOR_AGENT_ID);
  } catch (err) {
    console.error('[Study Entry] course/start failed:', err);
    toast(`Study course start failed: ${err && err.message ? err.message : err}`, 'error');
    return { ok: false, error: 'COURSE_START_FAILED', detail: String(err && err.message ? err.message : err) };
  }

  const course = (coursePayload && coursePayload.course) || {};
  const courseId = String(course.course_id || course.id || '').trim();

  try {
    await assembleStudyTutorContext(topic, STUDY_TUTOR_AGENT_ID);
  } catch (err) {
    console.warn('[Study Entry] tutor/context soft-fail:', err);
    toast(`Tutor context soft-fail: ${err && err.message ? err.message : err}`, 'warn');
  }

  if (typeof opts.switchTab === 'function') {
    opts.switchTab('chat');
  }

  const chatCtrl = typeof opts.getChatCtrl === 'function' ? opts.getChatCtrl() : null;
  let tutorSelected = false;
  if (chatCtrl && typeof chatCtrl.switchSelectedAgent === 'function') {
    try {
      await chatCtrl.switchSelectedAgent(STUDY_TUTOR_AGENT_ID);
      tutorSelected = true;
    } catch (err) {
      console.error('[Study Entry] switchSelectedAgent(tutor) failed:', err);
    }
  }
  if (!tutorSelected) {
    const agentSelect = $('agentSelect');
    if (agentSelect) {
      const hasTutor = Array.from(agentSelect.options || []).some((o) => o.value === STUDY_TUTOR_AGENT_ID);
      if (!hasTutor) {
        toast('Tutor pack missing from Chat agent list — Study entry aborted (no plain Chat).', 'error');
        return { ok: false, error: 'TUTOR_PACK_MISSING' };
      }
      agentSelect.value = STUDY_TUTOR_AGENT_ID;
      agentSelect.dispatchEvent(new Event('change'));
      tutorSelected = true;
    }
  }
  if (!tutorSelected) {
    toast('Could not select Tutor — Study entry aborted (no plain Chat).', 'error');
    return { ok: false, error: 'TUTOR_SELECT_FAILED' };
  }

  const binding = {
    active: true,
    topic,
    courseId,
    skillId: STUDY_LEARNING_OS_SKILL,
    agentId: STUDY_TUTOR_AGENT_ID,
  };
  _persistBinding(binding);
  saveLastStudyTopic(topic);

  const chatInput = $('chatInput');
  if (chatInput) {
    chatInput.value = buildStudyEducationModePrompt(topic, courseId);
    chatInput.focus();
  }

  toast(`Study: Tutor education mode · ${topic}${courseId ? ` · ${courseId}` : ''}`, 'info');
  return { ok: true, binding, course: coursePayload };
}

/**
 * Wire Study entry controls (sidebar + Chat header). Education tab stays untouched.
 * @param {{ switchTab?: Function, getChatCtrl?: Function, state?: object }} callbacks
 */
export function initStudyEntry(callbacks = {}) {
  const run = async (presetTopic) => {
    await enterTutorEducationMode({
      topic: presetTopic || '',
      switchTab: callbacks.switchTab,
      getChatCtrl: callbacks.getChatCtrl,
      toast: showToast,
      skipPrompt: !!String(presetTopic || '').trim(),
    });
  };

  const sidebarBtn = $('btn-study-entry');
  if (sidebarBtn) {
    sidebarBtn.addEventListener('click', (e) => {
      e.preventDefault();
      run('');
    });
  }

  const chatBtn = $('chatStudyEntryBtn');
  if (chatBtn) {
    chatBtn.addEventListener('click', (e) => {
      e.preventDefault();
      run('');
    });
  }


  const dueBtn = $('chatEducationModeDueBtn');
  if (dueBtn) {
    dueBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      await openDueReviewsInEducationMode({ toast: showToast });
    });
  }
  const dueRefreshBtn = $('chatEducationModeDueRefreshBtn');
  if (dueRefreshBtn) {
    dueRefreshBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      await openDueReviewsInEducationMode({ toast: showToast });
    });
  }
  const dueListEl = $('chatEducationModeDueList');
  if (dueListEl) {
    dueListEl.addEventListener('click', (e) => {
      const btn = e.target && e.target.closest ? e.target.closest('.chat-edu-due-item') : null;
      if (!btn) return;
      const itemId = btn.getAttribute('data-item-id') || '';
      const binding = getStudyEducationModeBinding();
      const chatInput = $('chatInput');
      if (!chatInput || !itemId) return;
      const topic = (binding && binding.topic) || 'Active Study Topic';
      const courseId = (binding && binding.courseId) || '';
      chatInput.value =
        `${STUDY_EDUCATION_MODE_MARKER} skill=${STUDY_DUE_REVIEW_SKILL}` +
        (courseId ? ` course_id=${courseId}` : '') +
        `\nPresent due item ${itemId} for topic "${topic}". ` +
        `After my answer, call education_due_review_complete with item_id=${itemId}.`;
      chatInput.focus();
    });
  }

  const exitBtn = $('chatEducationModeExitBtn');
  if (exitBtn) {
    exitBtn.addEventListener('click', (e) => {
      e.preventDefault();
      clearStudyEducationMode();
      showToast('Left Tutor education mode (Chat remains; course row stays durable).', 'info');
    });
  }

  // Restore chrome strip from prior session if present (visual only; course APIs still durable).
  try {
    const raw = localStorage.getItem(STUDY_EDUCATION_MODE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && parsed.active && parsed.topic) {
        _activeBinding = {
          active: true,
          topic: String(parsed.topic),
          courseId: String(parsed.courseId || ''),
          skillId: String(parsed.skillId || STUDY_LEARNING_OS_SKILL),
          agentId: String(parsed.agentId || STUDY_TUTOR_AGENT_ID),
        };
        renderStudyEducationModeChrome(_activeBinding);
      }
    }
  } catch {
    /* ignore */
  }

  return {
    enterTutorEducationMode: (opts) =>
      enterTutorEducationMode({
        ...opts,
        switchTab: opts.switchTab || callbacks.switchTab,
        getChatCtrl: opts.getChatCtrl || callbacks.getChatCtrl,
      }),
    openDueReviewsInEducationMode,
    clearStudyEducationMode,
    getStudyEducationModeBinding,
    isStudyEducationModeActive,
  };
}
