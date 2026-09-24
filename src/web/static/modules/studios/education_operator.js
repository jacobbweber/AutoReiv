/**
 * CARD-447: Education Studio operator console + Tutor topic/course context.
 * Reuses Learning OS Due / Progress / Wiki curate APIs from study_entry.
 * Does NOT build flashcard/quiz/test players (CARD-448).
 */

import { $, safeCreateIcons } from '../dom.js';
import { showToast } from '../ui/toast.js';
import {
  STUDY_TUTOR_AGENT_ID,
  STUDY_LEARNING_OS_SKILL,
  STUDY_WIKI_CURATION_SKILL,
  fetchStudyDueReviews,
  fetchStudyProgress,
  curateStudyWiki,
  enterTutorEducationMode,
  getStudyEducationModeBinding,
  assembleStudyTutorContext,
  startOrResumeStudyCourse,
  saveLastStudyTopic,
  fetchSelectedEducationContext,
  putSelectedEducationContext,
  loadStudioActiveEducationContext,
  saveStudioActiveEducationContext,
  mirrorSelectedToLocal,
  EDUCATION_STUDIO_ACTIVE_KEY,
} from './study_entry.js';

function _escapeHtml(s) {
  return String(s || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function renderEducationActiveContextChrome(selected) {
  const topicEl = $('educationActiveTopic');
  const courseEl = $('educationActiveCourseId');
  const topic = selected && selected.topic ? String(selected.topic) : '';
  const courseId = selected && (selected.course_id || selected.courseId)
    ? String(selected.course_id || selected.courseId)
    : '';
  if (topicEl) topicEl.textContent = topic || '-';
  if (courseEl) courseEl.textContent = courseId || '-';
  safeCreateIcons();
}

export async function hydrateEducationStudioActiveContext() {
  let selected = {};
  try {
    const data = await fetchSelectedEducationContext();
    selected = (data && data.selected) || {};
  } catch (err) {
    console.warn('[Education Operator] GET /api/education/selected failed:', err);
    selected = loadStudioActiveEducationContext() || {};
  }
  if (selected && selected.topic) {
    mirrorSelectedToLocal(selected);
    const topicInput = $('educationTopicInput');
    if (topicInput && !String(topicInput.value || '').trim()) {
      topicInput.value = selected.topic;
    }
  }
  renderEducationActiveContextChrome(selected);
  return selected;
}

export async function setEducationStudioActiveContext(opts = {}) {
  const toast = typeof opts.toast === 'function' ? opts.toast : showToast;
  const topicInput = $('educationTopicInput');
  let topic = String(opts.topic || (topicInput && topicInput.value) || '').trim();
  let courseId = String(opts.courseId || opts.course_id || '').trim();
  const agentId = opts.agentId || STUDY_TUTOR_AGENT_ID;

  if (!topic) {
    toast('Enter a Target Topic before Set active.', 'error');
    return { ok: false, error: 'TOPIC_REQUIRED' };
  }

  let coursePayload = null;
  try {
    coursePayload = await startOrResumeStudyCourse(topic, agentId);
    const course = (coursePayload && coursePayload.course) || {};
    if (!courseId) {
      courseId = String(course.course_id || course.id || '').trim();
    }
  } catch (err) {
    console.error('[Education Operator] course/start failed:', err);
    toast(`Course start failed: ${err && err.message ? err.message : err}`, 'error');
    return { ok: false, error: 'COURSE_START_FAILED', detail: String(err && err.message ? err.message : err) };
  }

  let putRes;
  try {
    putRes = await putSelectedEducationContext({
      topic,
      course_id: courseId,
      agent_id: agentId,
    });
  } catch (err) {
    console.error('[Education Operator] PUT /api/education/selected failed:', err);
    toast(`Save active context failed: ${err && err.message ? err.message : err}`, 'error');
    return { ok: false, error: 'SELECTED_PUT_FAILED' };
  }

  const selected = (putRes && putRes.selected) || { topic, course_id: courseId, agent_id: agentId };
  mirrorSelectedToLocal(selected);
  saveStudioActiveEducationContext(selected);
  saveLastStudyTopic(topic);
  renderEducationActiveContextChrome(selected);

  try {
    await assembleStudyTutorContext(topic, agentId);
  } catch (err) {
    console.warn('[Education Operator] tutor/context soft-fail:', err);
    toast(`Tutor context soft-fail: ${err && err.message ? err.message : err}`, 'warn');
  }

  toast(`Active education context: ${topic}${courseId ? ` · ${courseId}` : ''}`, 'success');
  return { ok: true, selected, course: coursePayload };
}

function _showPanel(id, show) {
  const el = $(id);
  if (!el) return;
  if (show) {
    el.classList.remove('hidden');
    el.setAttribute('aria-hidden', 'false');
  } else {
    el.classList.add('hidden');
    el.setAttribute('aria-hidden', 'true');
  }
}

export function renderStudioDuePanel(payload) {
  const listEl = $('educationOperatorDueList');
  const countEl = $('educationOperatorDueCount');
  const panel = $('educationOperatorDuePanel');
  if (panel) panel.classList.remove('hidden');
  if (!listEl) return;
  if (!payload || payload.ok === false || payload.success === false) {
    listEl.innerHTML = `<div class="text-[11px] text-rose-300 px-1">${_escapeHtml(payload && (payload.error || payload.empty_state) || 'Due list failed.')}</div>`;
    if (countEl) countEl.textContent = '!';
    return;
  }
  const items = Array.isArray(payload.items) ? payload.items : [];
  if (countEl) countEl.textContent = String(payload.count != null ? payload.count : items.length);
  if (!items.length) {
    listEl.innerHTML = `<div class="text-[11px] text-slate-500 px-1">${_escapeHtml(payload.empty_state || 'No due reviews.')}</div>`;
    return;
  }
  listEl.innerHTML = items
    .map((it) => {
      const id = _escapeHtml(it.item_id || it.id || '');
      const prompt = _escapeHtml(it.prompt || it.presentation_prompt || id || 'item');
      return `<button type="button" class="edu-op-due-item w-full text-left px-1.5 py-1 rounded bg-[#141721] hover:bg-slate-800 border border-white/[0.06] text-[11px] text-slate-200" data-item-id="${id}">${prompt}</button>`;
    })
    .join('');
}

export function renderStudioProgressPanel(payload) {
  const bodyEl = $('educationOperatorProgressBody');
  const badgeEl = $('educationOperatorProgressBadge');
  const panel = $('educationOperatorProgressPanel');
  if (panel) {
    panel.classList.remove('hidden');
    panel.setAttribute('aria-hidden', 'false');
  }
  if (!bodyEl) return;
  if (!payload || payload.success === false || payload.ok === false) {
    const err = (payload && (payload.error || payload.empty_state)) || 'Progress unavailable.';
    bodyEl.innerHTML = `<div class="text-[11px] text-rose-300 px-1">${_escapeHtml(err)}</div>`;
    if (badgeEl) badgeEl.textContent = '!';
    return;
  }
  const mastery = (payload && payload.mastery) || {};
  const due = (payload && payload.due) || {};
  const course = (payload && payload.course) || {};
  const pct = mastery.mastery_pct;
  const dueN = due.count != null ? due.count : (Array.isArray(due.items) ? due.items.length : 0);
  if (badgeEl) {
    badgeEl.textContent = pct === null || pct === undefined ? `due ${dueN}` : `${pct}%`;
  }
  bodyEl.innerHTML = `
    <div class="grid grid-cols-3 gap-1.5">
      <div class="rounded border border-white/[0.06] bg-[#141721]/80 p-1.5">
        <div class="text-[10px] uppercase tracking-wider text-sky-200/80 mb-0.5">Course</div>
        <div class="text-[11px] text-slate-200 truncate">${_escapeHtml(course.topic_id || course.topic || payload.topic || '-')}</div>
        <div class="text-[10px] font-mono text-slate-500 truncate">${_escapeHtml(course.course_id || course.id || '-')}</div>
      </div>
      <div class="rounded border border-white/[0.06] bg-[#141721]/80 p-1.5">
        <div class="text-[10px] uppercase tracking-wider text-violet-200/80 mb-0.5">Mastery</div>
        <div class="text-[11px] text-slate-200">${pct === null || pct === undefined ? 'no graded mastery' : `${pct}% graded pass`}</div>
      </div>
      <div class="rounded border border-white/[0.06] bg-[#141721]/80 p-1.5">
        <div class="text-[10px] uppercase tracking-wider text-amber-200/80 mb-0.5">Due</div>
        <div class="text-[11px] text-slate-200">${dueN} item(s)</div>
      </div>
    </div>`;
}

export function renderStudioWikiCuratePanel(payload) {
  const resultEl = $('educationOperatorCurateResult');
  const panel = $('educationOperatorCuratePanel');
  if (panel) panel.classList.remove('hidden');
  if (!resultEl) return;
  if (payload && payload.idle) {
    resultEl.innerHTML = `<div class="text-[11px] text-slate-500 px-1">Supply a link or curriculum outline. Notes stage in 00_Inbox/.</div>`;
    return;
  }
  if (!payload || payload.success === false || payload.ok === false) {
    resultEl.innerHTML = `<div class="text-[11px] text-rose-300 px-1">${_escapeHtml((payload && payload.error) || 'Wiki curation failed.')}</div>`;
    return;
  }
  const notes = Array.isArray(payload.notes) ? payload.notes : [];
  if (!notes.length) {
    resultEl.innerHTML = `<div class="text-[11px] text-slate-500 px-1">No notes returned.</div>`;
    return;
  }
  resultEl.innerHTML = notes
    .map((n) => {
      const path = _escapeHtml(n.relative_path || n.path || n.title || 'note');
      return `<div class="px-1.5 py-1 rounded bg-[#141721] border border-white/[0.06] text-[11px] font-mono text-slate-300">${path}</div>`;
    })
    .join('');
}

function _studioBinding() {
  const local = loadStudioActiveEducationContext() || {};
  const study = getStudyEducationModeBinding();
  const topic = (local.topic || (study && study.topic) || '').trim();
  const courseId = (local.course_id || local.courseId || (study && study.courseId) || '').trim();
  const agentId = local.agent_id || (study && study.agentId) || STUDY_TUTOR_AGENT_ID;
  if (!topic) return null;
  return { active: true, topic, courseId, agentId, skillId: STUDY_LEARNING_OS_SKILL };
}

export async function openStudioDueReviews(opts = {}) {
  const toast = typeof opts.toast === 'function' ? opts.toast : showToast;
  const binding = _studioBinding();
  if (!binding) {
    toast('Set an active topic/course in Education Studio first.', 'error');
    return { ok: false, error: 'NO_ACTIVE_CONTEXT' };
  }
  const due = await fetchStudyDueReviews(binding.agentId || STUDY_TUTOR_AGENT_ID);
  renderStudioDuePanel(due);
  if (!due || due.ok === false || due.success === false) {
    toast(`Due reviews failed: ${(due && due.error) || 'mastery/due error'}`, 'error');
    return { ok: false, error: 'DUE_FAILED', due };
  }
  toast(`Due reviews: ${due.count != null ? due.count : (due.items || []).length} item(s) from Learning OS`, 'info');
  return { ok: true, due, binding };
}

export async function openStudioProgress(opts = {}) {
  const toast = typeof opts.toast === 'function' ? opts.toast : showToast;
  const binding = _studioBinding();
  if (!binding) {
    toast('Set an active topic/course in Education Studio first.', 'error');
    return { ok: false, error: 'NO_ACTIVE_CONTEXT' };
  }
  const progress = await fetchStudyProgress(binding.agentId || STUDY_TUTOR_AGENT_ID, {
    topic: binding.topic,
    course_id: binding.courseId,
  });
  renderStudioProgressPanel(progress);
  if (!progress || progress.success === false || progress.ok === false) {
    toast(`Progress failed: ${(progress && (progress.error || progress.empty_state)) || 'unavailable'}`, 'error');
    return { ok: false, error: 'PROGRESS_FAILED', progress };
  }
  const mastery = progress.mastery || {};
  const pct = mastery.mastery_pct;
  const dueN = (progress.due && progress.due.count) || 0;
  toast(
    `Progress: ${pct === null || pct === undefined ? 'no graded mastery' : pct + '% graded pass'} · due ${dueN}`,
    'info',
  );
  return { ok: true, progress, binding };
}

export async function openStudioWikiCurate(opts = {}) {
  const toast = typeof opts.toast === 'function' ? opts.toast : showToast;
  const binding = _studioBinding();
  if (!binding) {
    toast('Set an active topic/course in Education Studio first.', 'error');
    return { ok: false, error: 'NO_ACTIVE_CONTEXT' };
  }
  _showPanel('educationOperatorCuratePanel', true);
  renderStudioWikiCuratePanel({ idle: true, notes: [], ok: true, success: true });
  toast(`Wiki curation ready (skill ${STUDY_WIKI_CURATION_SKILL})`, 'info');
  return { ok: true, binding };
}

export async function runStudioWikiCuration(opts = {}) {
  const toast = typeof opts.toast === 'function' ? opts.toast : showToast;
  const binding = _studioBinding();
  if (!binding) {
    toast('Set an active topic/course in Education Studio first.', 'error');
    return { ok: false, error: 'NO_ACTIVE_CONTEXT' };
  }
  const mode = opts.mode === 'curriculum' ? 'curriculum' : 'link';
  const rawSource = !!opts.raw_source;
  let url = String(opts.url || '').trim();
  let curriculum = String(opts.curriculum || '').trim();

  if (mode === 'curriculum' && !curriculum) {
    const raw =
      typeof window !== 'undefined' && typeof window.prompt === 'function'
        ? window.prompt('Curriculum outline to curate into Wiki:', '')
        : null;
    if (raw === null) return { ok: false, error: 'CANCELLED' };
    curriculum = String(raw).trim();
    if (!curriculum) {
      toast('Curriculum text required.', 'error');
      return { ok: false, error: 'CURRICULUM_REQUIRED' };
    }
  }
  if (mode === 'link' && !url) {
    const raw =
      typeof window !== 'undefined' && typeof window.prompt === 'function'
        ? window.prompt('URL to curate into Wiki:', 'https://')
        : null;
    if (raw === null) return { ok: false, error: 'CANCELLED' };
    url = String(raw).trim();
    if (!url) {
      toast('URL required.', 'error');
      return { ok: false, error: 'URL_REQUIRED' };
    }
  }

  const result = await curateStudyWiki({
    mode,
    url,
    curriculum,
    topic: binding.topic,
    raw_source: rawSource,
    template: rawSource ? undefined : 'education-concept',
    agentId: binding.agentId || STUDY_TUTOR_AGENT_ID,
  });
  renderStudioWikiCuratePanel(result);
  if (!result.success) {
    toast(`Wiki curation failed: ${result.error || 'unknown'}`, 'error');
    return { ok: false, error: 'CURATE_FAILED', result };
  }
  toast(`Wiki curated ${(result.notes || []).length} note(s) into library`, 'info');
  return { ok: true, result, binding };
}

/**
 * Wire Education Studio operator console [CARD-447].
 */
export function initEducationStudioOperator(callbacks = {}) {
  const toast = callbacks.showToast || showToast;

  hydrateEducationStudioActiveContext().catch((err) => {
    console.warn('[Education Operator] hydrate failed:', err);
  });

  const setActiveBtn = $('educationSetActiveContextBtn');
  if (setActiveBtn) {
    setActiveBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      await setEducationStudioActiveContext({ toast });
    });
  }

  const pairBtn = $('educationPairTutorBtn');
  if (pairBtn) {
    pairBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      const selected = loadStudioActiveEducationContext() || (await fetchSelectedEducationContext().then((d) => d.selected).catch(() => ({})));
      const topic = (selected && selected.topic) || '';
      if (!topic) {
        toast('Set an active topic/course first, then Pair Tutor.', 'error');
        return;
      }
      await enterTutorEducationMode({
        topic,
        switchTab: callbacks.switchTab,
        getChatCtrl: callbacks.getChatCtrl,
        toast,
        skipPrompt: true,
        preferStudioContext: true,
      });
    });
  }

  const dueBtn = $('educationOperatorDueBtn');
  if (dueBtn) {
    dueBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      await openStudioDueReviews({ toast });
    });
  }
  const dueRefresh = $('educationOperatorDueRefreshBtn');
  if (dueRefresh) {
    dueRefresh.addEventListener('click', async (e) => {
      e.preventDefault();
      await openStudioDueReviews({ toast });
    });
  }

  const progressBtn = $('educationOperatorProgressBtn');
  if (progressBtn) {
    progressBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      await openStudioProgress({ toast });
    });
  }
  const progressRefresh = $('educationOperatorProgressRefreshBtn');
  if (progressRefresh) {
    progressRefresh.addEventListener('click', async (e) => {
      e.preventDefault();
      await openStudioProgress({ toast });
    });
  }
  const progressHide = $('educationOperatorProgressHideBtn');
  if (progressHide) {
    progressHide.addEventListener('click', (e) => {
      e.preventDefault();
      _showPanel('educationOperatorProgressPanel', false);
    });
  }

  const curateBtn = $('educationOperatorCurateBtn');
  if (curateBtn) {
    curateBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      await openStudioWikiCurate({ toast });
    });
  }
  const curateHide = $('educationOperatorCurateHideBtn');
  if (curateHide) {
    curateHide.addEventListener('click', (e) => {
      e.preventDefault();
      _showPanel('educationOperatorCuratePanel', false);
    });
  }
  const curateLink = $('educationOperatorCurateLinkBtn');
  if (curateLink) {
    curateLink.addEventListener('click', async (e) => {
      e.preventDefault();
      await runStudioWikiCuration({ mode: 'link', toast });
    });
  }
  const curateCurriculum = $('educationOperatorCurateCurriculumBtn');
  if (curateCurriculum) {
    curateCurriculum.addEventListener('click', async (e) => {
      e.preventDefault();
      await runStudioWikiCuration({ mode: 'curriculum', toast });
    });
  }
  const curateRaw = $('educationOperatorCurateRawBtn');
  if (curateRaw) {
    curateRaw.addEventListener('click', async (e) => {
      e.preventDefault();
      await runStudioWikiCuration({ mode: 'link', raw_source: true, toast });
    });
  }

  return {
    hydrateEducationStudioActiveContext,
    setEducationStudioActiveContext,
    openStudioDueReviews,
    openStudioProgress,
    openStudioWikiCurate,
    EDUCATION_STUDIO_ACTIVE_KEY,
  };
}
