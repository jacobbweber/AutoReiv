/**
 * CARD-437: Study Entry = Tutor education mode (thin shell).
 * Reuses Chat + Tutor agent + Learning OS course APIs. Does not retire Education Studio.
 */

import { $, safeCreateIcons } from '../dom.js';
import { showToast } from '../ui/toast.js';

export const STUDY_LAST_TOPIC_KEY = 'autoreiv.study.last_topic.v1';
export const STUDY_EDUCATION_MODE_KEY = 'autoreiv.study.education_mode.v1';
export const STUDY_TUTOR_AGENT_ID = 'tutor';
export const STUDY_LEARNING_OS_SKILL = 'start-resume-topic';
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
    clearStudyEducationMode,
    getStudyEducationModeBinding,
    isStudyEducationModeActive,
  };
}
