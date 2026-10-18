/**
 * Study Entry panels & actions (Due reviews, Progress summary, Wiki curation).
 * Extracted from study_entry.js for CARD-716 modularization.
 */

import { $, safeCreateIcons } from '../dom.js';
import { showToast } from '../ui/toast.js';
import {
  STUDY_TUTOR_AGENT_ID,
  STUDY_DUE_REVIEW_SKILL,
  STUDY_WIKI_CURATION_SKILL,
  STUDY_PROGRESS_SKILL,
  getStudyEducationModeBinding,
  persistStudyBinding,
  getStudyComposerInput,
  renderStudyEducationModeChrome,
  fetchStudyDueReviews,
  buildDueReviewPrompt,
  buildProgressSummaryPrompt,
  buildWikiCurationPrompt,
} from './study_entry.js';

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
  persistStudyBinding(binding);

  const chatInput = getStudyComposerInput();
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

/**
 * Fetch trustable progress from Learning OS (course + mastery + due).
 * [CARD-441] Non-Studio surface; Studio chrome retained separately.
 */
export async function fetchStudyProgress(agentId = STUDY_TUTOR_AGENT_ID, opts = {}) {
  const aid = String(agentId || STUDY_TUTOR_AGENT_ID).trim() || STUDY_TUTOR_AGENT_ID;
  const topic = String(opts.topicId || opts.topic || '').trim();
  const courseId = String(opts.courseId || '').trim();
  const qs = new URLSearchParams({ agent_id: aid });
  if (topic) qs.set('topic_id', topic);
  if (courseId) qs.set('course_id', courseId);
  const res = await fetch(`/api/education/progress?${qs.toString()}`);
  if (!res.ok) {
    let detail = '';
    try {
      const errBody = await res.json();
      detail = errBody.detail || errBody.error || '';
    } catch {
      /* ignore */
    }
    return {
      ok: false,
      success: false,
      empty: true,
      error: `progress ${res.status}${detail ? `: ${detail}` : ''}`,
      empty_state: 'Progress unavailable.',
      mastery: { mastery_pct: null, empty: true },
      due: { count: 0, empty: true },
      course: { count: 0, empty: true },
      http_contract: 'GET /api/education/progress',
    };
  }
  const body = await res.json();
  const success = body && body.success !== false;
  if (!success) {
    return {
      ok: false,
      success: false,
      empty: true,
      error: (body && (body.error || body.empty_state)) || 'Progress unavailable.',
      empty_state: (body && body.empty_state) || 'Progress unavailable.',
      mastery: (body && body.mastery) || { mastery_pct: null, empty: true },
      due: (body && body.due) || { count: 0, empty: true },
      course: (body && body.course) || { count: 0, empty: true },
      http_contract: 'GET /api/education/progress',
      raw: body,
    };
  }
  const mastery = body.mastery || {};
  const due = body.due || {};
  const course = body.course || {};
  const empty = Boolean(body.empty);
  return {
    ok: true,
    success: true,
    empty,
    empty_state: body.empty_state || (empty ? 'No course or mastery progress yet.' : ''),
    topic: body.topic || topic || null,
    course_id: body.course_id || courseId || null,
    current_course: body.current_course || null,
    chrome: body.chrome || null,
    mastery,
    mastery_all: body.mastery_all || null,
    due,
    course,
    learner: body.learner || null,
    studio_required: false,
    http_contract: 'GET /api/education/progress',
    raw: body,
  };
}

export function renderStudyProgressPanel(payload) {
  const panel = typeof $ === 'function' ? $('chatEducationModeProgressPanel') : document.getElementById('chatEducationModeProgressPanel');
  const bodyEl = typeof $ === 'function' ? $('chatEducationModeProgressBody') : document.getElementById('chatEducationModeProgressBody');
  const badgeEl = typeof $ === 'function' ? $('chatEducationModeProgressBadge') : document.getElementById('chatEducationModeProgressBadge');
  if (!panel || !bodyEl) return;
  panel.classList.remove('hidden');
  panel.setAttribute('aria-hidden', 'false');
  if (!payload || payload.ok === false || payload.success === false) {
    const err = (payload && (payload.error || payload.empty_state)) || 'Progress unavailable.';
    bodyEl.innerHTML = `<div class="text-[11px] text-rose-300 px-1">${_escapeHtml(err)}</div>`;
    if (badgeEl) badgeEl.textContent = '!';
    return;
  }
  if (payload.empty) {
    bodyEl.innerHTML = `<div class="text-[11px] text-slate-500 px-1">${_escapeHtml(payload.empty_state || 'No course or mastery progress yet.')}</div>`;
    if (badgeEl) badgeEl.textContent = '0';
    return;
  }
  const course = payload.current_course || {};
  const courseMeta = payload.course || {};
  const mastery = payload.mastery || {};
  const due = payload.due || {};
  const chrome = payload.chrome || {};
  const topic = _escapeHtml(payload.topic || course.topic_id || '—');
  const cid = _escapeHtml(payload.course_id || course.course_id || '—');
  const status = _escapeHtml(course.status || chrome.status || 'none');
  const step = _escapeHtml(chrome.current_step || course.current_step || '—');
  const courseCount = Number(courseMeta.count || 0);
  const passN = Number(mastery.pass_count || 0);
  const missN = Number(mastery.miss_count || 0);
  const unseenN = Number(mastery.unseen_count || 0);
  const dueN = Number(due.count || 0);
  const pct = mastery.mastery_pct;
  const pctLabel =
    pct === null || pct === undefined
      ? 'n/a (no graded items)'
      : `${pct}% pass of graded`;
  if (badgeEl) {
    badgeEl.textContent = pct === null || pct === undefined ? String(dueN) : `${Math.round(pct)}%`;
  }
  bodyEl.innerHTML = `
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-1.5 text-[11px]">
      <div class="rounded-md border border-emerald-900/40 bg-emerald-950/20 px-2 py-1.5">
        <div class="text-[10px] uppercase tracking-wider text-emerald-200/80 mb-0.5">Course</div>
        <div class="text-slate-200">topic <span class="text-sky-300">${topic}</span></div>
        <div class="font-mono text-[10px] text-brand-300 truncate" title="${cid}">${cid}</div>
        <div class="text-slate-400">status <span class="text-slate-200">${status}</span> · step <span class="text-slate-200">${step}</span></div>
        <div class="text-slate-500">${courseCount} course row(s)</div>
      </div>
      <div class="rounded-md border border-violet-900/40 bg-violet-950/20 px-2 py-1.5">
        <div class="text-[10px] uppercase tracking-wider text-violet-200/80 mb-0.5">Mastery</div>
        <div class="text-slate-200">${pctLabel}</div>
        <div class="text-slate-400">pass ${passN} · miss ${missN} · unseen ${unseenN}</div>
        <div class="text-slate-500">${Number(mastery.item_count || 0)} ledger item(s)</div>
      </div>
      <div class="rounded-md border border-amber-900/40 bg-amber-950/20 px-2 py-1.5">
        <div class="text-[10px] uppercase tracking-wider text-amber-200/80 mb-0.5">Due</div>
        <div class="text-slate-200 font-mono">${dueN}</div>
        <div class="text-slate-500">${due.empty ? _escapeHtml(due.empty_state || 'No due reviews.') : 'from mastery/due'}</div>
      </div>
    </div>`;
}

export function hideStudyProgressPanel() {
  const panel = document.getElementById('chatEducationModeProgressPanel');
  if (!panel) return;
  panel.classList.add('hidden');
  panel.setAttribute('aria-hidden', 'true');
}

/**
 * Open trustable progress inside Tutor education mode (skill=progress-summary).
 * Does not open Education Studio (#view-education).
 */
export async function openProgressInEducationMode(opts = {}) {
  const toast = typeof opts.toast === 'function' ? opts.toast : () => {};
  let binding = getStudyEducationModeBinding();
  if (!binding || !binding.topic) {
    toast('Enter Study / Tutor education mode first (sidebar Study), then open Progress.', 'error');
    return { ok: false, error: 'EDUCATION_MODE_REQUIRED' };
  }
  const progress = await fetchStudyProgress(binding.agentId || STUDY_TUTOR_AGENT_ID, {
    topicId: binding.topic,
    courseId: binding.courseId,
  });
  if (!progress.ok) {
    toast(`Progress failed: ${progress.error || 'unavailable'}`, 'error');
    renderStudyProgressPanel(progress);
    return { ok: false, error: 'PROGRESS_FETCH_FAILED', progress };
  }
  binding = {
    ...binding,
    skillId: STUDY_PROGRESS_SKILL,
  };
  persistStudyBinding(binding);
  renderStudyEducationModeChrome(binding);
  const chatInput = getStudyComposerInput();
  if (chatInput && !opts.skipPrompt) {
    chatInput.value = buildProgressSummaryPrompt(binding.topic, binding.courseId);
  }
  renderStudyProgressPanel(progress);
  if (progress.empty) {
    toast(progress.empty_state || 'No course or mastery progress yet.', 'info');
  } else {
    const pct = progress.mastery && progress.mastery.mastery_pct;
    const dueN = (progress.due && progress.due.count) || 0;
    toast(
      `Progress: ${pct === null || pct === undefined ? 'no graded mastery' : pct + '% graded pass'} · due ${dueN}`,
      'info',
    );
  }
  return { ok: true, binding, progress };
}

/**
 * POST /api/education/wiki/curate — durable Wiki note path (not transcript-only).
 * @param {{ mode: string, url?: string, curriculum?: string, topic?: string, template?: string, raw_source?: boolean, body?: string, agentId?: string }} opts
 */
export async function curateStudyWiki(opts = {}) {
  const mode = String(opts.mode || 'link').trim().toLowerCase() || 'link';
  const payload = {
    mode,
    url: opts.url || undefined,
    curriculum: opts.curriculum || undefined,
    topic: opts.topic || undefined,
    title: opts.title || undefined,
    template: opts.template || undefined,
    raw_source: !!opts.raw_source,
    body: opts.body || undefined,
    agent_id: opts.agentId || STUDY_TUTOR_AGENT_ID,
  };
  const res = await fetch('/api/education/wiki/curate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  let data;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    const detail = data && (data.detail || data.error) ? String(data.detail || data.error) : '';
    return {
      ok: false,
      success: false,
      durable: false,
      notes: [],
      error: `wiki/curate ${res.status}${detail ? `: ${detail}` : ''}`,
      http_contract: 'POST /api/education/wiki/curate',
    };
  }
  const success = !!(data && data.success);
  return {
    ok: success,
    success,
    durable: !!(data && data.durable && success),
    notes: (data && Array.isArray(data.notes)) ? data.notes : [],
    paths: (data && Array.isArray(data.paths)) ? data.paths : [],
    path: (data && data.path) || '',
    error: success ? '' : String((data && data.error) || 'curation failed'),
    raw: data,
    http_contract: 'POST /api/education/wiki/curate',
    skill_hint: STUDY_WIKI_CURATION_SKILL,
  };
}

export function renderStudyWikiCuratePanel(payload) {
  const panel = $('chatEducationModeCuratePanel');
  const resultEl = $('chatEducationModeCurateResult');
  if (!panel || !resultEl) return;
  const failed = payload && (payload.ok === false || payload.success === false);
  const notes = (payload && Array.isArray(payload.notes)) ? payload.notes : [];
  if (failed) {
    resultEl.innerHTML = `<div class="text-[11px] text-rose-300 px-1">${_escapeHtml(payload.error || 'Curation failed.')}</div>`;
  } else if (!notes.length && payload && payload.idle) {
    resultEl.innerHTML = '<div class="text-[11px] text-slate-500 px-1">Supply a link or curriculum outline. Notes stage in 00_Inbox/ via wiki_note_create.</div>';
  } else if (!notes.length) {
    resultEl.innerHTML = '<div class="text-[11px] text-slate-500 px-1">No notes written.</div>';
  } else {
    resultEl.innerHTML = notes
      .map((n) => {
        const path = _escapeHtml(n.path || '');
        const title = _escapeHtml(n.title || '');
        const tpl = _escapeHtml(n.template || '');
        const raw = n.raw_source ? ' · raw' : '';
        return `<div class="px-2 py-1 rounded border border-sky-900/30 bg-[#0e1015]/80">
          <div class="text-[11px] font-medium text-slate-200 truncate">${title}</div>
          <div class="text-[10px] font-mono text-sky-300/90 truncate">${path}</div>
          <div class="text-[10px] text-slate-500">${tpl}${raw}</div>
        </div>`;
      })
      .join('');
  }
  panel.classList.remove('hidden');
  panel.setAttribute('aria-hidden', 'false');
  safeCreateIcons();
}

export function hideStudyWikiCuratePanel() {
  if (typeof document === 'undefined' || !document.getElementById) return;
  const panel = document.getElementById('chatEducationModeCuratePanel');
  if (!panel) return;
  panel.classList.add('hidden');
  panel.setAttribute('aria-hidden', 'true');
}

/**
 * Open wiki curation chrome in Tutor education mode (skill=education-wiki-curation).
 * @param {{ toast?: Function, mode?: string }} [opts]
 */
export async function openWikiCurationInEducationMode(opts = {}) {
  const toast = typeof opts.toast === 'function' ? opts.toast : showToast;
  let binding = getStudyEducationModeBinding();
  if (!binding || !binding.active || !binding.topic) {
    toast('Enter Study / Tutor education mode first (sidebar Study), then open Wiki curate.', 'error');
    return { ok: false, error: 'EDUCATION_MODE_REQUIRED' };
  }

  binding = {
    ...binding,
    skillId: STUDY_WIKI_CURATION_SKILL,
  };
  persistStudyBinding(binding);

  const mode = String(opts.mode || 'link').trim().toLowerCase() || 'link';
  const chatInput = getStudyComposerInput();
  if (chatInput) {
    chatInput.value = buildWikiCurationPrompt(binding.topic, binding.courseId, mode);
    chatInput.focus();
  }

  renderStudyWikiCuratePanel({ idle: true, notes: [], ok: true, success: true });
  toast(`Wiki curation ready (skill ${STUDY_WIKI_CURATION_SKILL})`, 'info');
  return { ok: true, binding };
}

/**
 * Prompt + run durable curation for a link or curriculum outline.
 * @param {{ mode: 'link'|'curriculum', raw_source?: boolean, toast?: Function }} opts
 */
export async function runStudyWikiCuration(opts = {}) {
  const toast = typeof opts.toast === 'function' ? opts.toast : showToast;
  let binding = getStudyEducationModeBinding();
  if (!binding || !binding.active || !binding.topic) {
    toast('Enter Study / Tutor education mode first, then curate.', 'error');
    return { ok: false, error: 'EDUCATION_MODE_REQUIRED' };
  }

  const mode = String(opts.mode || 'link').trim().toLowerCase() || 'link';
  const rawSource = !!opts.raw_source;
  let url = '';
  let curriculum = '';
  if (mode === 'curriculum') {
    const seed = '- ';
    const raw =
      typeof window !== 'undefined' && typeof window.prompt === 'function'
        ? window.prompt(
            'Curriculum outline (one bullet per line). Cancel to abort.',
            seed,
          )
        : null;
    if (raw === null) return { ok: false, error: 'CANCELLED' };
    curriculum = String(raw).trim();
    if (!curriculum) {
      toast('Curriculum outline required.', 'error');
      return { ok: false, error: 'CURRICULUM_REQUIRED' };
    }
  } else {
    const raw =
      typeof window !== 'undefined' && typeof window.prompt === 'function'
        ? window.prompt(
            rawSource
              ? 'Source URL (raw note, no education tags). Cancel to abort.'
              : 'URL to curate into Wiki (education template). Cancel to abort.',
            'https://',
          )
        : null;
    if (raw === null) return { ok: false, error: 'CANCELLED' };
    url = String(raw).trim();
    if (!url) {
      toast('URL required.', 'error');
      return { ok: false, error: 'URL_REQUIRED' };
    }
  }

  binding = { ...binding, skillId: STUDY_WIKI_CURATION_SKILL };
  persistStudyBinding(binding);

  const chatInput = getStudyComposerInput();
  if (chatInput) {
    chatInput.value = buildWikiCurationPrompt(binding.topic, binding.courseId, mode);
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

  renderStudyWikiCuratePanel(result);
  if (!result.success) {
    toast(`Wiki curation failed: ${result.error || 'unknown'}`, 'error');
    return { ok: false, error: 'CURATE_FAILED', result };
  }
  const count = (result.notes || []).length;
  toast(`Wiki curated ${count} note(s) into library`, 'info');
  return { ok: true, result, binding };
}
