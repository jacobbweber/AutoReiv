/**
 * CARD-437: Study Entry = Tutor education mode (thin shell).
 * CARD-439: Due reviews surface in Tutor education mode (Learning OS mastery/due).
 * CARD-440: Wiki curation from links / curriculum in Tutor education mode.
 * CARD-441: Trustable progress (course/mastery/due) on Tutor strip — not Studio-only.
 * CARD-447: Studio is operator home for Due/Progress/Wiki curate; Tutor injects Studio-active topic/course.
 * Reuses Chat + Tutor agent + Learning OS course APIs. Does not retire Education Studio.
 */

import { $, safeCreateIcons } from '../dom.js';
import { showToast } from '../ui/toast.js';
import {
  renderStudyDueReviewsPanel,
  hideStudyDueReviewsPanel,
  openDueReviewsInEducationMode,
  fetchStudyProgress,
  renderStudyProgressPanel,
  hideStudyProgressPanel,
  openProgressInEducationMode,
  curateStudyWiki,
  renderStudyWikiCuratePanel,
  hideStudyWikiCuratePanel,
  openWikiCurationInEducationMode,
  runStudyWikiCuration,
} from './study_entry_panels.js';

export {
  renderStudyDueReviewsPanel,
  hideStudyDueReviewsPanel,
  openDueReviewsInEducationMode,
  fetchStudyProgress,
  renderStudyProgressPanel,
  hideStudyProgressPanel,
  openProgressInEducationMode,
  curateStudyWiki,
  renderStudyWikiCuratePanel,
  hideStudyWikiCuratePanel,
  openWikiCurationInEducationMode,
  runStudyWikiCuration,
};

export const STUDY_LAST_TOPIC_KEY = 'autoreiv.study.last_topic.v1';
export const STUDY_EDUCATION_MODE_KEY = 'autoreiv.study.education_mode.v1';
export const STUDY_TUTOR_AGENT_ID = 'tutor';
export const STUDY_LEARNING_OS_SKILL = 'start-resume-topic';
export const STUDY_DUE_REVIEW_SKILL = 'due-review';
export const STUDY_WIKI_CURATION_SKILL = 'education-wiki-curation';
export const STUDY_PROGRESS_SKILL = 'progress-summary';
export const STUDY_EDUCATION_MODE_MARKER = '[Tutor Education Mode]';

/** Durable Studio-active topic/course (Projects selected parallel) [CARD-447]. */
export const EDUCATION_STUDIO_ACTIVE_KEY = 'autoreiv.educationStudio.activeContext.v1';
export const EDUCATION_SELECTED_HTTP = '/api/education/selected';

/** @type {{ active: boolean, topic: string, courseId: string, skillId: string, agentId: string } | null} */
let _activeBinding = null;

function _composerInput() {
  return $('promptInput') || $('chatInput');
}

export function getStudyComposerInput() {
  return _composerInput();
}

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

export function loadStudioActiveEducationContext() {
  try {
    const raw = localStorage.getItem(EDUCATION_STUDIO_ACTIVE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || !parsed.topic) return null;
    return {
      topic: String(parsed.topic || '').trim(),
      course_id: String(parsed.course_id || parsed.courseId || '').trim(),
      agent_id: String(parsed.agent_id || parsed.agentId || STUDY_TUTOR_AGENT_ID).trim() || STUDY_TUTOR_AGENT_ID,
      updated_at: String(parsed.updated_at || '').trim(),
      source: String(parsed.source || 'education_studio').trim() || 'education_studio',
    };
  } catch {
    return null;
  }
}

export function saveStudioActiveEducationContext(selected) {
  if (!selected || !selected.topic) return;
  try {
    localStorage.setItem(
      EDUCATION_STUDIO_ACTIVE_KEY,
      JSON.stringify({
        topic: String(selected.topic || '').trim(),
        course_id: String(selected.course_id || selected.courseId || '').trim(),
        agent_id: String(selected.agent_id || selected.agentId || STUDY_TUTOR_AGENT_ID).trim() || STUDY_TUTOR_AGENT_ID,
        updated_at: String(selected.updated_at || '').trim(),
        source: String(selected.source || 'education_studio').trim() || 'education_studio',
      }),
    );
  } catch {
    /* ignore quota */
  }
}

export function mirrorSelectedToLocal(selected) {
  if (selected && selected.topic) saveStudioActiveEducationContext(selected);
}

/** GET /api/education/selected — durable Studio-active topic/course [CARD-447]. */
export async function fetchSelectedEducationContext() {
  const res = await fetch(EDUCATION_SELECTED_HTTP);
  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    throw new Error(`education/selected ${res.status}${detail ? `: ${detail}` : ''}`);
  }
  return res.json();
}

/** PUT /api/education/selected — persist Studio-active topic/course [CARD-447]. */
export async function putSelectedEducationContext(payload = {}) {
  const body = {
    topic: payload.topic,
    course_id: payload.course_id || payload.courseId || '',
    agent_id: payload.agent_id || payload.agentId || STUDY_TUTOR_AGENT_ID,
    clear: !!payload.clear,
  };
  const res = await fetch(EDUCATION_SELECTED_HTTP, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    throw new Error(`education/selected PUT ${res.status}${detail ? `: ${detail}` : ''}`);
  }
  const data = await res.json();
  if (data && data.selected) mirrorSelectedToLocal(data.selected);
  return data;
}

/** Resolve topic for Tutor education mode: explicit -> Studio selected -> last Study topic. */
export async function resolveTutorEducationTopic(explicitTopic = '') {
  const direct = String(explicitTopic || '').trim();
  if (direct) return { topic: direct, source: 'explicit' };
  try {
    const data = await fetchSelectedEducationContext();
    const sel = data && data.selected;
    if (sel && sel.topic) {
      mirrorSelectedToLocal(sel);
      return {
        topic: String(sel.topic).trim(),
        courseId: String(sel.course_id || '').trim(),
        source: 'education_studio',
      };
    }
  } catch {
    /* fall through */
  }
  const local = loadStudioActiveEducationContext();
  if (local && local.topic) {
    return { topic: local.topic, courseId: local.course_id || '', source: 'education_studio_local' };
  }
  const last = loadLastStudyTopic();
  if (last) return { topic: last, source: 'last_study' };
  return { topic: '', source: 'none' };
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
  hideStudyProgressPanel();
  hideStudyWikiCuratePanel();
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

export function persistStudyBinding(binding) {
  _persistBinding(binding);
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

export function buildProgressSummaryPrompt(topic, courseId = '') {
  const t = String(topic || '').trim() || 'current topic';
  const courseBit = courseId ? ` course_id=${courseId}` : '';
  return (
    `${STUDY_EDUCATION_MODE_MARKER} skill=${STUDY_PROGRESS_SKILL}${courseBit}\n` +
    `Summarize trustable Learning OS progress for topic "${t}" using skill "${STUDY_PROGRESS_SKILL}". ` +
    `Call education_progress_summary (GET /api/education/progress). Cite course status/step, mastery pass/miss/due counts from the tool result. ` +
    `If empty, say so honestly. Never invent mastery percentages. Education Studio is not required to view progress.`
  );
}

export function buildWikiCurationPrompt(topic, courseId = '', mode = 'link') {
  const t = String(topic || '').trim() || 'Active Study Topic';
  const courseBit = courseId ? ` course_id=${courseId}` : '';
  const modeBit = mode === 'curriculum' ? 'curriculum outline' : 'link(s)';
  return (
    `${STUDY_EDUCATION_MODE_MARKER} skill=${STUDY_WIKI_CURATION_SKILL}${courseBit}\n` +
    `Curate ${modeBit} for topic "${t}" into the Wiki library using Learning OS skill "${STUDY_WIKI_CURATION_SKILL}". ` +
    `Call education_wiki_template_catalog, then education_wiki_curate_from_link or education_wiki_curate_from_curriculum ` +
    `(POST /api/education/wiki/curate). Prefer catalogued education-* templates; raw sources MAY omit education tags. ` +
    `On fetch/write failure report the error and do not claim the library was updated.`
  );
}


export async function enterTutorEducationMode(opts = {}) {
  const toast = typeof opts.toast === 'function' ? opts.toast : showToast;
  let topic = String(opts.topic || '').trim();
  let studioCourseId = '';
  if (!topic) {
    const resolved = await resolveTutorEducationTopic('');
    if (resolved.topic) {
      topic = resolved.topic;
      studioCourseId = resolved.courseId || '';
    }
  }
  if (!topic && !opts.skipPrompt) {
    const seed = (loadStudioActiveEducationContext() || {}).topic || loadLastStudyTopic();
    topic = promptStudyTopic(seed) || '';
  }
  if (!topic) {
    toast('Study needs a topic — education mode not started (no freeform Chat).', 'error');
    return { ok: false, error: 'STUDY_TOPIC_REQUIRED' };
  }

  let coursePayload;
  try {
    coursePayload = await startOrResumeStudyCourse(topic, STUDY_TUTOR_AGENT_ID);
  } catch (err) {
    console.error('[Study Entry] course/start failed:', err);
    toast(`Study course start failed: ${err && err.message ? err.message : err}`, 'error');
    return { ok: false, error: 'COURSE_START_FAILED', detail: String(err && err.message ? err.message : err) };
  }

  const course = (coursePayload && coursePayload.course) || {};
  let courseId = String(course.course_id || course.id || '').trim();

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
        toast('Tutor skill missing from Chat agent list — Study entry aborted (no plain Chat).', 'error');
        return { ok: false, error: 'TUTOR_SKILL_MISSING' };
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

  if (!courseId && studioCourseId) courseId = studioCourseId;
  const binding = {
    active: true,
    topic,
    courseId,
    skillId: STUDY_LEARNING_OS_SKILL,
    agentId: STUDY_TUTOR_AGENT_ID,
  };
  _persistBinding(binding);
  saveLastStudyTopic(topic);
  try {
    await putSelectedEducationContext({
      topic,
      course_id: courseId,
      agent_id: STUDY_TUTOR_AGENT_ID,
    });
  } catch (err) {
    console.warn('[Study Entry] PUT /api/education/selected soft-fail:', err);
  }

  const chatInput = _composerInput();
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


  const progressRefreshBtn = $('chatEducationModeProgressRefreshBtn');
  if (progressRefreshBtn) {
    progressRefreshBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      await openProgressInEducationMode({ toast: showToast, skipPrompt: true });
    });
  }
  const progressHideBtn = $('chatEducationModeProgressHideBtn');
  if (progressHideBtn) {
    progressHideBtn.addEventListener('click', (e) => {
      e.preventDefault();
      hideStudyProgressPanel();
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
      const chatInput = _composerInput();
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

  const curateHideBtn = $('chatEducationModeCurateHideBtn');
  if (curateHideBtn) {
    curateHideBtn.addEventListener('click', (e) => {
      e.preventDefault();
      hideStudyWikiCuratePanel();
    });
  }
  const curateLinkBtn = $('chatEducationModeCurateLinkBtn');
  if (curateLinkBtn) {
    curateLinkBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      await runStudyWikiCuration({ mode: 'link', toast: showToast });
    });
  }
  const curateCurriculumBtn = $('chatEducationModeCurateCurriculumBtn');
  if (curateCurriculumBtn) {
    curateCurriculumBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      await runStudyWikiCuration({ mode: 'curriculum', toast: showToast });
    });
  }
  const curateRawBtn = $('chatEducationModeCurateRawBtn');
  if (curateRawBtn) {
    curateRawBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      await runStudyWikiCuration({ mode: 'link', raw_source: true, toast: showToast });
    });
  }

  const openStudioBtn = $('chatEducationModeOpenStudioBtn');
  if (openStudioBtn) {
    openStudioBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const tab = $('tab-education');
      if (tab) tab.click();
      else if (typeof callbacks.switchTab === 'function') callbacks.switchTab('education');
      showToast('Education Studio is the operator console (Due / Progress / Wiki curate).', 'info');
    });
  }

  // CARD-447: chat Due/Progress/Wiki curate deep-link to Studio operator console (strip thinned).
  const deepLinkStudio = (e) => {
    if (e) {
      e.preventDefault();
      if (typeof e.stopImmediatePropagation === 'function') e.stopImmediatePropagation();
      else if (typeof e.stopPropagation === 'function') e.stopPropagation();
    }
    const tab = $('tab-education');
    if (tab) tab.click();
    else if (typeof callbacks.switchTab === 'function') callbacks.switchTab('education');
    showToast('Opened Education Studio operator console.', 'info');
  };
  ['chatEducationModeDueBtn', 'chatEducationModeProgressBtn', 'chatEducationModeCurateBtn'].forEach((id) => {
    const btn = $(id);
    if (!btn || btn.dataset.card447Wired === '1') return;
    btn.dataset.card447Wired = '1';
    btn.addEventListener('click', deepLinkStudio, true);
  });

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
    openProgressInEducationMode,
    openWikiCurationInEducationMode,
    runStudyWikiCuration,
    clearStudyEducationMode,
    getStudyEducationModeBinding,
    isStudyEducationModeActive,
  };
}
