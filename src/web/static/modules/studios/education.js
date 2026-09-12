/**
 * Education Studio shell [CARD-237 / REQ-EDU-SHELL-001..004]
 *
 * Education Studio: Wiki-backed ask + quiz + elaboration + construction [CARD-243/244/245]
 * Interface-only Studio: Wiki-backed ask → standing Chat Job mint (CARD-236 path)
 * + Education Jobs session list (open in Chat / Observe). Shell + Job mint + Learning OS Priming/Dual Coding modes [CARD-238].
 */

import { $, escapeHtml, safeCreateIcons } from '../dom.js';
import { showToast } from '../ui/toast.js';
import { copyToClipboard } from '../utils/clipboard.js';
import { buildChatStreamPayload, isJobPhaseChromeEvent } from './chat.js';

export const EDUCATION_SESSIONS_KEY = 'autoreiv.education.sessions.v1';
export const EDUCATION_ASK_MARKER = '[Education Studio]';

/**
 * Build an outcome-shaped standing ask for CARD-236 Job mint.
 * @param {{ topic: string, teachStyle?: string, wikiPath?: string, wikiTitle?: string }} opts
 */
export const EDUCATION_MODES = Object.freeze({
  custom: 'custom',
  priming: 'priming',
  dual_coding: 'dual_coding',
  construction: 'construction',
});


/** Binary external grade helper for Studio (mirrors server normalize). [CARD-242] */
export function gradeEducationAnswerLocal(expected, given) {
  const norm = (s) => String(s || '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .replace(/^[.\s,;:!?"'`]+|[.\s,;:!?"'`]+$/g, '');
  const e = norm(expected);
  const g = norm(given);
  return Boolean(e) && e === g;
}


/**
 * Build an outcome-shaped standing ask for CARD-236 Job mint.
 * @param {{ topic: string, teachStyle?: string, wikiPath?: string, wikiTitle?: string, mode?: string }} opts
 */
/** Build Ask pressure clause from weak mastery items [CARD-243]. */

/** Binary external elaboration grade (concepts rubric OR reference tokens). [CARD-244] */
export function gradeElaborationAnswerLocal(given, { reference = '', requiredConcepts = [] } = {}) {
  const normalize = (t) => String(t || '').trim().toLowerCase().replace(/\s+/g, ' ').replace(/^[\s.,;:!?\"'`]+|[\s.,;:!?\"'`]+$/g, '');
  const got = normalize(given);
  if (!got) return false;
  const concepts = (requiredConcepts || []).map(normalize).filter(Boolean);
  if (concepts.length) return concepts.every((c) => got.includes(c));
  const ref = String(reference || '').trim();
  if (!ref) return false;
  if (gradeEducationAnswerLocal(ref, given)) return true;
  const stop = new Set(['a','an','the','and','or','to','of','in','on','for','is','are','was','were','be','as','at','by','with','that','this','it','from','into','about','your','own','words','explain']);
  const tokens = normalize(ref).match(/[a-z0-9][a-z0-9_\-]{1,}/g) || [];
  const need = tokens.filter((t) => !stop.has(t));
  if (!need.length) return false;
  return need.every((t) => got.includes(t));
}


export function buildLearnerPressureClause(items = []) {
  const list = Array.isArray(items) ? items.slice(0, 3) : [];
  if (!list.length) {
    return ' No known weak quiz items in the learner model yet - teach normally without inventing random drills.';
  }
  const lines = list.map((it) => {
    const iid = it.item_id || '';
    const topic = it.topic || '';
    const prompt = it.prompt || '';
    const misses = it.miss_count || 0;
    return `- item_id=${iid} topic="${topic}" prompt="${prompt}" (miss_count=${misses})`;
  });
  return (
    ' Pressure known miss(es) from the durable learner model in memory.db ' +
    '(do NOT quiz random strong items when a miss is known):\n' +
    `${lines.join('\n')}\n` +
    'Re-ask or reteach those weak prompts first, then confirm recall.'
  );
}


export function buildEducationAsk(opts = {}) {
  const topic = String(opts.topic || '').trim();
  const modeRaw = String(opts.mode || EDUCATION_MODES.custom).trim().toLowerCase();
  const mode = Object.values(EDUCATION_MODES).includes(modeRaw) ? modeRaw : EDUCATION_MODES.custom;
  const hasPressureItems = Array.isArray(opts.pressureItems) && opts.pressureItems.length > 0;
  const pressureClause = String(opts.pressureClause || '').trim()
    || (hasPressureItems ? buildLearnerPressureClause(opts.pressureItems) : '');
  const teachStyleDefault =
    mode === EDUCATION_MODES.priming
      ? 'Priming: schema/outline/prerequisites/goals before detail'
      : mode === EDUCATION_MODES.dual_coding
        ? 'Dual Coding: prose + Mermaid diagram pair for each concept'
        : mode === EDUCATION_MODES.construction
          ? 'Construction: generative study artifact (schema + dual-code + quiz/elaboration) to Inbox'
          : 'clear, stepwise explanation with one concrete example';
  const teachStyle = String(opts.teachStyle || '').trim() || teachStyleDefault;
  const wikiPath = String(opts.wikiPath || '').trim();
  const wikiTitle = String(opts.wikiTitle || '').trim();
  const wikiBit = wikiPath
    ? ` Ground the teaching in my Wiki note "${wikiTitle || wikiPath}" (${wikiPath}).`
    : ' Ground the teaching in my existing Wiki notes when relevant.';

  if (mode === EDUCATION_MODES.priming) {
    return (
      `${EDUCATION_ASK_MARKER} [Mode: Priming] Teach me about "${topic}" using the education-priming skill.` +
      wikiBit +
      ` How to teach me: ${teachStyle}.` +
      ` Use only wiki_note_search/wiki_note_list/wiki_note_read/wiki_note_create (never wiki_overview). Search Wiki first, then write a Priming schema note (outline, prerequisites, learning goals) back to Wiki.` +
      ` Done-when: a Priming schema note exists in Wiki for "${topic}" (outline + prerequisites + goals) and I can open it.`
      + (pressureClause || '')
    );
  }
  if (mode === EDUCATION_MODES.dual_coding) {
    return (
      `${EDUCATION_ASK_MARKER} [Mode: Dual Coding] Teach me about "${topic}" using the education-dual-coding skill.` +
      wikiBit +
      ` How to teach me: ${teachStyle}.` +
      ` Use only wiki_note_search/wiki_note_read/wiki_note_create (never wiki_overview). For each key concept write clear prose AND a Mermaid diagram, then save both codes to Wiki.` +
      ` Done-when: a Dual Coding study note exists in Wiki for "${topic}" with prose + at least one Mermaid diagram and I can open it.`
      + (pressureClause || '')
    );
  }
  if (mode === EDUCATION_MODES.construction) {
    return (
      `${EDUCATION_ASK_MARKER} [Mode: Construction] Construct a generative study artifact for "${topic}" using the education-construction skill.` +
      wikiBit +
      ` How to teach me: ${teachStyle}.` +
      ` Use only wiki_note_search/wiki_note_list/wiki_note_read/wiki_note_create (never wiki_overview). Search Wiki first (fail soft), then wiki_note_create a Construction study note into 00_Inbox/ with schema + dual-code (prose+Mermaid) + quiz + elaboration prompts.` +
      ` Done-when: a Construction study artifact note exists in Wiki 00_Inbox/ for "${topic}" and I can open it.`
      + (pressureClause || '')
    );
  }
  return (
    `${EDUCATION_ASK_MARKER} Teach me about "${topic}".` +
    wikiBit +
    ` How to teach me: ${teachStyle}.` +
    ` Write a short study note back to Wiki summarizing what I should retain.` +
    ` Done-when: a study note exists in Wiki for "${topic}" and I can open it.`
    + (pressureClause || '')
  );
}

export function isEducationJobGoal(goal) {
  const g = String(goal || '');
  return g.includes(EDUCATION_ASK_MARKER) || /\[Education Studio\]/i.test(g);
}

export function loadEducationSessions() {
  try {
    const raw = localStorage.getItem(EDUCATION_SESSIONS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveEducationSessions(rows) {
  const list = Array.isArray(rows) ? rows : [];
  localStorage.setItem(EDUCATION_SESSIONS_KEY, JSON.stringify(list));
  return list;
}

/**
 * @param {{ job_id: string, session_id?: string, topic?: string, teach_style?: string, wiki_path?: string, success_rule?: string, created_at?: string, status?: string }} row
 */
export function upsertEducationSession(row) {
  if (!row || !row.job_id) return loadEducationSessions();
  const next = loadEducationSessions().filter((r) => r.job_id !== row.job_id);
  next.unshift({
    job_id: row.job_id,
    session_id: row.session_id || '',
    topic: row.topic || '',
    teach_style: row.teach_style || '',
    wiki_path: row.wiki_path || '',
    success_rule: row.success_rule || '',
    created_at: row.created_at || new Date().toISOString(),
    status: row.status || 'minted',
  });
  return saveEducationSessions(next.slice(0, 100));
}

export function extractJobIdFromSsePayload(data) {
  if (!data || typeof data !== 'object') return '';
  const id = data.job_id || data.jobId || (data.data && (data.data.job_id || data.data.jobId));
  return id ? String(id) : '';
}


/**
 * Forward Education SSE job-phase events into Chat's shared strip. [CARD-240 / REQ-JOB-CHROME]
 * Education must NOT invent a second progress UI — reuse Chat chrome only.
 * @param {{ updateJobPhaseFromEvent?: Function }|null} chatCtrl
 * @param {string} eventType
 * @param {object} ev
 * @returns {boolean}
 */
export function forwardJobPhaseChromeEvent(chatCtrl, eventType, ev) {
  if (!chatCtrl) return false;
  if (!isJobPhaseChromeEvent(eventType)) return false;
  // Prefer grape-vine inline chrome (Formulate/Execute + plan-steps) over strip-only. [CARD-240 AC]
  if (typeof chatCtrl.updateJobChromeFromEvent === 'function') {
    chatCtrl.updateJobChromeFromEvent(eventType, ev || {});
    return true;
  }
  if (typeof chatCtrl.updateJobPhaseFromEvent !== 'function') return false;
  chatCtrl.updateJobPhaseFromEvent(eventType, ev || {});
  return true;
}


/**
 * @param {object} state
 * @param {{ showToast?: Function, switchTab?: Function, getChatCtrl?: Function, getObsCtrl?: Function }} callbacks
 */
export function initEducationStudio(state, callbacks = {}) {
  const toast = callbacks.showToast || showToast;
  const topicInput = $('educationTopicInput');
  const teachInput = $('educationTeachStyleInput');
  const modePrimingBtn = $('educationModePriming');
  const modeDualBtn = $('educationModeDualCoding');
  const modeConstructionBtn = $('educationModeConstruction');
  const modeCustomBtn = $('educationModeCustom');
  let selectedMode = EDUCATION_MODES.custom;
  const wikiSearchInput = $('educationWikiSearchInput');
  const wikiHits = $('educationWikiHits');
  const askBtn = $('educationAskSubmitBtn');
  const statusEl = $('educationAskStatus');
  const jobChip = $('educationJobIdChip');
  const copyJobBtn = $('educationCopyJobIdBtn');
  const openChatBtn = $('educationOpenChatBtn');
  const openObsBtn = $('educationOpenObserveBtn');
  const sessionList = $('educationSessionList');
  const refreshBtn = $('educationSessionsRefreshBtn');
  const selectedWikiPath = $('educationSelectedWikiPath');
  const selectedWikiTitle = $('educationSelectedWikiTitle');

  let lastJobId = '';
  let lastSessionId = '';
  let selectedWiki = { path: '', title: '' };
  let wikiSearchTimer = null;

  function setStatus(msg, isError = false) {
    if (!statusEl) return;
    statusEl.textContent = msg || '';
    statusEl.className = `text-[11px] ${isError ? 'text-rose-300' : 'text-slate-400'}`;
  }

  function showJobId(jobId) {
    lastJobId = jobId || '';
    if (jobChip) {
      jobChip.textContent = lastJobId || '—';
      jobChip.classList.toggle('opacity-40', !lastJobId);
    }
    if (copyJobBtn) {
      copyJobBtn.classList.toggle('hidden', !lastJobId);
      if (lastJobId) copyJobBtn.dataset.jobId = lastJobId;
      else delete copyJobBtn.dataset.jobId;
    }
    if (openChatBtn) openChatBtn.classList.toggle('hidden', !lastSessionId);
    if (openObsBtn) openObsBtn.classList.toggle('hidden', !lastJobId);
  }

  function renderSessions() {
    if (!sessionList) return;
    const rows = loadEducationSessions();
    if (!rows.length) {
      sessionList.innerHTML =
        '<div class="text-xs text-slate-500 italic px-2 py-6 text-center">No Education Jobs yet. Ask above to mint a standing Job.</div>';
      return;
    }
    sessionList.innerHTML = rows
      .map((r) => {
        const topic = escapeHtml(r.topic || 'Untitled topic');
        const jobId = escapeHtml(r.job_id || '');
        const when = escapeHtml(r.created_at || '');
        const style = escapeHtml(r.teach_style || '');
        const wiki = r.wiki_path ? `<div class="text-[10px] text-slate-500 font-mono truncate">${escapeHtml(r.wiki_path)}</div>` : '';
        return `
          <article class="rounded-xl border border-slate-800 bg-slate-900/60 p-3 space-y-2" data-edu-job="${jobId}" data-edu-session="${escapeHtml(r.session_id || '')}">
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <h3 class="text-xs font-semibold text-slate-100 truncate">${topic}</h3>
                ${style ? `<p class="text-[11px] text-slate-400 truncate">${style}</p>` : ''}
                ${wiki}
              </div>
              <span class="text-[10px] font-mono text-indigo-300 shrink-0">${jobId}</span>
            </div>
            ${String(r.status || '') === 'needs_approval' ? '<div class="text-[10px] font-semibold text-amber-300">Needs approval</div>' : ''}
            <div class="text-[10px] text-slate-500">${when}</div>
            <div class="flex flex-wrap gap-1.5">
              <button type="button" class="edu-open-chat px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-[10px] text-slate-200" data-session-id="${escapeHtml(r.session_id || '')}">${String(r.status || '') === 'needs_approval' ? 'Approve in Chat' : 'Open in Chat'}</button>
              <button type="button" class="edu-open-obs px-2 py-1 rounded-lg bg-indigo-950/70 hover:bg-indigo-900/80 border border-indigo-800/60 text-[10px] text-indigo-200" data-job-id="${jobId}">Open in Observe</button>
              <button type="button" class="edu-copy-job px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-[10px] text-slate-300" data-job-id="${jobId}">Copy job_id</button>
            </div>
          </article>`;
      })
      .join('');

    sessionList.querySelectorAll('.edu-open-chat').forEach((btn) => {
      btn.addEventListener('click', () => openInChat(btn.getAttribute('data-session-id') || ''));
    });
    sessionList.querySelectorAll('.edu-open-obs').forEach((btn) => {
      btn.addEventListener('click', () => openInObserve(btn.getAttribute('data-job-id') || ''));
    });
    sessionList.querySelectorAll('.edu-copy-job').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-job-id') || '';
        if (!id) return;
        await copyToClipboard(id);
        toast(`Copied ${id}`, 'success');
      });
    });
    safeCreateIcons(sessionList);
  }

  function openInChat(sessionId) {
    const sid = sessionId || lastSessionId;
    if (typeof callbacks.switchTab === 'function') callbacks.switchTab('chat');
    const chatCtrl = typeof callbacks.getChatCtrl === 'function' ? callbacks.getChatCtrl() : null;
    if (chatCtrl && sid && typeof chatCtrl.selectSession === 'function') {
      chatCtrl.selectSession(sid);
    }
  }

  function openInObserve(jobId) {
    const id = jobId || lastJobId;
    if (typeof callbacks.switchTab === 'function') callbacks.switchTab('observability');
    const input = $('standingJourneyJobIdInput');
    if (input && id) {
      input.value = id;
    }
    const obsCtrl = typeof callbacks.getObsCtrl === 'function' ? callbacks.getObsCtrl() : null;
    if (obsCtrl && typeof obsCtrl.loadStandingJourney === 'function') {
      obsCtrl.loadStandingJourney();
    } else {
      const loadBtn = $('standingJourneyLoadBtn');
      if (loadBtn) loadBtn.click();
    }
  }

  function setSelectedWiki(path, title) {
    selectedWiki = { path: path || '', title: title || '' };
    if (selectedWikiPath) selectedWikiPath.textContent = selectedWiki.path || 'None selected (optional)';
    if (selectedWikiTitle) selectedWikiTitle.textContent = selectedWiki.title || '';
  }

  async function searchWiki(q) {
    if (!wikiHits) return;
    const query = String(q || '').trim();
    if (!query) {
      wikiHits.innerHTML = '<div class="text-[11px] text-slate-500 px-1">Type to search Wiki notes…</div>';
      return;
    }
    try {
      const res = await fetch(`/api/wiki/search?q=${encodeURIComponent(query)}&limit=8`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const hits = Array.isArray(data) ? data : data.hits || data.results || [];
      if (!hits.length) {
        wikiHits.innerHTML = '<div class="text-[11px] text-slate-500 px-1">No Wiki hits.</div>';
        return;
      }
      wikiHits.innerHTML = hits
        .map((h) => {
          const path = escapeHtml(h.path || h.rel_path || '');
          const title = escapeHtml(h.title || path);
          return `<button type="button" class="edu-wiki-hit w-full text-left px-2.5 py-1.5 rounded-lg hover:bg-slate-800 border border-transparent hover:border-slate-700 transition" data-path="${path}" data-title="${title}">
            <div class="text-[11px] font-medium text-slate-200 truncate">${title}</div>
            <div class="text-[10px] font-mono text-slate-500 truncate">${path}</div>
          </button>`;
        })
        .join('');
      wikiHits.querySelectorAll('.edu-wiki-hit').forEach((btn) => {
        btn.addEventListener('click', () => {
          setSelectedWiki(btn.getAttribute('data-path') || '', btn.getAttribute('data-title') || '');
          toast('Wiki note selected for grounding', 'info');
        });
      });
    } catch (err) {
      console.error('[Education Studio] Wiki search failed:', err);
      wikiHits.innerHTML = '<div class="text-[11px] text-rose-300 px-1">Wiki search failed.</div>';
    }
  }

  async function ensureSession(topic = '') {
    // REQ-EDU-SHELL-002a: never reuse Chat/phase activeSessionId (nested ::phase:: hangs mint).
    const agentId = state.selectedAgentId || 'assistant';
    const title = topic
      ? `Education: ${String(topic).trim().slice(0, 80)}`
      : 'Education Studio';
    const res = await fetch('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent_id: agentId, title }),
    });
    if (!res.ok) throw new Error(`session create HTTP ${res.status}`);
    const sess = await res.json();
    lastSessionId = sess.id;
    // Do not clobber Chat's activeSessionId with Education mint sessions.
    if (Array.isArray(state.sessions)) state.sessions.unshift(sess);
    return sess.id;
  }

  async function drainSseForJobId(response, hooks = {}) {
    const onJobMinted = typeof hooks.onJobMinted === 'function' ? hooks.onJobMinted : null;
    const onApprovalRequired = typeof hooks.onApprovalRequired === 'function' ? hooks.onApprovalRequired : null;
    const onEvent = typeof hooks.onEvent === 'function' ? hooks.onEvent : null;
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let currentEvent = 'message';
    let jobId = '';
    let successRule = '';
    let mintedNotified = false;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) {
          currentEvent = 'message';
          continue;
        }
        if (trimmed.startsWith('event:')) {
          currentEvent = trimmed.slice(6).trim();
          continue;
        }
        if (!trimmed.startsWith('data:')) continue;
        const jsonStr = trimmed.slice(5).trim();
        if (!jsonStr || jsonStr === '[DONE]') continue;
        try {
          const ev = JSON.parse(jsonStr);
          const type = ev.type || currentEvent;
          if (onEvent) onEvent(ev, type);
          const found = extractJobIdFromSsePayload(ev);
          if (found && (type === 'job_created' || type === 'phase_start' || !jobId)) {
            jobId = found;
          }
          if (ev.success_rule) successRule = String(ev.success_rule);
          // REQ-HITL-ORIGIN-003: notify on mint but DO NOT cancel the SSE — origin thread stays live for HITL.
          if (jobId && !mintedNotified && (type === 'job_created' || type === 'phase_start')) {
            mintedNotified = true;
            if (onJobMinted) onJobMinted({ jobId, successRule, event: ev, type });
          }
          if (type === 'approval_required' || ev.status === 'approval_required' || ev.approval_id) {
            if (onApprovalRequired) onApprovalRequired({ jobId, event: ev, type });
          }
        } catch {
          /* ignore partial */
        }
      }
    }
    return { jobId, successRule };
  }




  async function refreshEducationApprovals() {
    // REQ-HITL-ORIGIN-002: mark Education Jobs that have pending phase/parent approvals.
    const rows = loadEducationSessions();
    if (!rows.length) return;
    const agentId = state.selectedAgentId || 'assistant';
    let changed = false;
    for (const row of rows) {
      const sid = String(row.session_id || '').trim();
      if (!sid) continue;
      try {
        const url = `/api/approvals/pending?session_id=${encodeURIComponent(sid)}&agent_id=${encodeURIComponent(agentId)}`;
        const res = await fetch(url);
        if (!res.ok) continue;
        const pending = await res.json();
        const needs = Array.isArray(pending) && pending.length > 0;
        const nextStatus = needs ? 'needs_approval' : (row.status === 'needs_approval' ? 'running' : row.status);
        if (nextStatus !== row.status) {
          row.status = nextStatus;
          changed = true;
        }
      } catch {
        /* ignore */
      }
    }
    if (changed) {
      saveEducationSessions(rows);
      renderSessions();
    }
  }

  function syncModeButtons() {
    const map = [
      [modePrimingBtn, EDUCATION_MODES.priming],
      [modeDualBtn, EDUCATION_MODES.dual_coding],
      [modeConstructionBtn, EDUCATION_MODES.construction],
      [modeCustomBtn, EDUCATION_MODES.custom],
    ];
    map.forEach(([btn, mode]) => {
      if (!btn) return;
      const on = selectedMode === mode;
      btn.setAttribute('aria-pressed', on ? 'true' : 'false');
      btn.classList.toggle('bg-sky-700', on);
      btn.classList.toggle('text-white', on);
      btn.classList.toggle('border-sky-500', on);
      btn.classList.toggle('bg-slate-800', !on);
      btn.classList.toggle('text-slate-300', !on);
    });
  }

  function setMode(mode) {
    const next = String(mode || EDUCATION_MODES.custom);
    selectedMode = Object.values(EDUCATION_MODES).includes(next) ? next : EDUCATION_MODES.custom;
    syncModeButtons();
    if (teachInput && !String(teachInput.value || '').trim()) {
      if (selectedMode === EDUCATION_MODES.priming) {
        teachInput.placeholder = 'Priming: schema / outline / prerequisites / goals';
      } else if (selectedMode === EDUCATION_MODES.dual_coding) {
        teachInput.placeholder = 'Dual Coding: prose + Mermaid for each concept';
      } else if (selectedMode === EDUCATION_MODES.construction) {
        teachInput.placeholder = 'Construction: generate study artifact to 00_Inbox via wiki_note_*';
      }
    }
  }



  async function submitAsk() {
    const topic = (topicInput && topicInput.value || '').trim();
    const teachStyle = (teachInput && teachInput.value || '').trim();
    if (!topic) {
      setStatus('Topic is required.', true);
      toast('Enter a topic to learn', 'error');
      return;
    }
    // CARD-243: next Ask pressures known miss from durable learner model (not random strong)
    let pressureItems = [];
    try {
      const agentId = state.selectedAgentId || 'assistant';
      let weakRes = await fetch(`/api/education/quiz/next?agent_id=${encodeURIComponent(agentId)}&limit=3&topic=${encodeURIComponent(topic)}`);
      if (weakRes.ok) {
        const weakData = await weakRes.json();
        pressureItems = Array.isArray(weakData.items) ? weakData.items : [];
      }
      if (!pressureItems.length) {
        weakRes = await fetch(`/api/education/quiz/next?agent_id=${encodeURIComponent(agentId)}&limit=3`);
        if (weakRes.ok) {
          const weakData = await weakRes.json();
          pressureItems = Array.isArray(weakData.items) ? weakData.items : [];
        }
      }
      pressureItems = pressureItems.filter((it) => {
        const g = String(it.grade || '').toLowerCase();
        return g === 'miss' || Number(it.miss_count || 0) > 0;
      });
    } catch (e) {
      console.warn('[Education Studio] learner pressure prefetch failed', e);
    }
    const ask = buildEducationAsk({
      topic,
      teachStyle,
      wikiPath: selectedWiki.path,
      wikiTitle: selectedWiki.title,
      mode: selectedMode,
      pressureItems,
    });
    askBtn && (askBtn.disabled = true);
    setStatus('Minting standing Education Job via Chat path…');
    showJobId('');
    // Long-lived stream: abort only if mint never arrives. Cleared once job_id is known.
    const ac = typeof AbortController !== 'undefined' ? new AbortController() : null;
    const mintTimeoutMs = 45000;
    let timer = ac ? setTimeout(() => ac.abort(), mintTimeoutMs) : null;
    try {
      const sessionId = await ensureSession(topic);
      lastSessionId = sessionId;
      const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(
          buildChatStreamPayload({
            agentId: state.selectedAgentId || 'assistant',
            sessionId,
            content: ask,
            selfVerify: !!state.verifyEnabled,
            approvalAutoRun: state.approvalAutoRun,
          }),
        ),
        signal: ac ? ac.signal : undefined,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      // REQ-JOB-CHROME-001..003: keep feeding Chat's Job phase strip from Education SSE.
      const getChatCtrl = () => (typeof callbacks.getChatCtrl === 'function' ? callbacks.getChatCtrl() : null);

      // Accumulate chrome events so we can replay after selectSession wipes the Chat DOM. [CARD-240 AC]
      const chromeReplay = [];

      const openOriginChatForHitl = async (phaseHint = null) => {
        // REQ-HITL-ORIGIN-001: park operator on parent/origin session so phase HITL projects here.
        if (typeof callbacks.switchTab === 'function') callbacks.switchTab('chat');
        const chatCtrl = getChatCtrl();
        if (chatCtrl && typeof chatCtrl.selectSession === 'function') {
          // selectSession resets strip + inline chrome — await then replay accumulated events.
          await chatCtrl.selectSession(sessionId);
        }
        const ctrl = getChatCtrl();
        const replay = chromeReplay.slice();
        if (phaseHint && phaseHint.event) {
          const t = phaseHint.type || 'job_created';
          if (!replay.some((r) => r.type === t && r.ev === phaseHint.event)) {
            replay.push({ type: t, ev: phaseHint.event });
          }
        }
        for (const item of replay) {
          forwardJobPhaseChromeEvent(ctrl, item.type, item.ev);
        }
        if (ctrl && typeof ctrl.remountInlineJobChrome === 'function') {
          ctrl.remountInlineJobChrome();
        }
      };

      const { jobId, successRule } = await drainSseForJobId(res, {
        // Live grape-vine chrome + strip while Education SSE stays open (CARD-239 keep-alive / CARD-240 AC).
        onEvent: (ev, type) => {
          if (isJobPhaseChromeEvent(type)) {
            chromeReplay.push({ type, ev });
            if (chromeReplay.length > 80) chromeReplay.splice(0, chromeReplay.length - 80);
          }
          forwardJobPhaseChromeEvent(getChatCtrl(), type, ev);
        },
        onJobMinted: ({ jobId: jid, successRule: sr, event, type }) => {
          if (timer) {
            clearTimeout(timer);
            timer = null;
          }
          lastSessionId = sessionId;
          showJobId(jid);
          upsertEducationSession({
            job_id: jid,
            session_id: sessionId,
            topic,
            teach_style: teachStyle,
            wiki_path: selectedWiki.path,
            success_rule: sr,
            created_at: new Date().toISOString(),
            status: 'running',
          });
          renderSessions();
          setStatus(`Standing Job minted: ${jid} — staying on origin thread for HITL…`);
          toast(`Education Job ${jid} minted`, 'success');
          askBtn && (askBtn.disabled = false);
          // Fire-and-forget async open; strip re-applied after selectSession reset.
          Promise.resolve(openOriginChatForHitl({ event, type })).catch((err) => {
            console.error('[Education Studio] origin chat open failed:', err);
          });
        },
        onApprovalRequired: ({ jobId: jid, event, type }) => {
          const id = jid || lastJobId;
          if (id) {
            upsertEducationSession({
              job_id: id,
              session_id: sessionId,
              topic,
              teach_style: teachStyle,
              wiki_path: selectedWiki.path,
              status: 'needs_approval',
            });
            renderSessions();
          }
          setStatus('Needs approval — Approve in the Education origin Chat (not a phase orphan).');
          toast('Approval needed in Chat', 'info');
          Promise.resolve(openOriginChatForHitl({ event, type: type || 'approval_required' })).catch((err) => {
            console.error('[Education Studio] origin chat open failed:', err);
          });
        },
      });


      if (!jobId) {
        setStatus('Ask completed but no job_id was minted (check outcome shaping / orchestrator).', true);
        toast('No standing Job minted', 'error');
        return;
      }
      lastSessionId = sessionId;
      showJobId(jobId);
      const prev = loadEducationSessions().find((r) => r.job_id === jobId);
      upsertEducationSession({
        job_id: jobId,
        session_id: sessionId,
        topic,
        teach_style: teachStyle,
        wiki_path: selectedWiki.path,
        success_rule: successRule,
        created_at: (prev && prev.created_at) || new Date().toISOString(),
        status: (prev && prev.status === 'needs_approval') ? 'needs_approval' : 'completed',
      });
      renderSessions();
      if (!(prev && prev.status === 'needs_approval')) {
        setStatus(`Education run finished for ${jobId}`);
      }
    } catch (err) {
      console.error('[Education Studio] Ask failed:', err);
      const aborted = err && (err.name === 'AbortError' || /aborted/i.test(String(err.message || '')));
      setStatus(
        aborted
          ? `Ask timed out after ${mintTimeoutMs / 1000}s waiting for job_id. Try again.`
          : `Ask failed: ${err.message || err}`,
        true,
      );
      toast(aborted ? 'Education ask timed out' : 'Education ask failed', 'error');
    } finally {
      if (timer) clearTimeout(timer);
      if (askBtn) askBtn.disabled = false;
    }
  }



  if (wikiSearchInput) {
    wikiSearchInput.addEventListener('input', () => {
      clearTimeout(wikiSearchTimer);
      wikiSearchTimer = setTimeout(() => searchWiki(wikiSearchInput.value), 220);
    });
  }
  if (modePrimingBtn) modePrimingBtn.addEventListener('click', () => setMode(EDUCATION_MODES.priming));
  if (modeDualBtn) modeDualBtn.addEventListener('click', () => setMode(EDUCATION_MODES.dual_coding));
  if (modeConstructionBtn) modeConstructionBtn.addEventListener('click', () => setMode(EDUCATION_MODES.construction));
  if (modeCustomBtn) modeCustomBtn.addEventListener('click', () => setMode(EDUCATION_MODES.custom));
  setMode(EDUCATION_MODES.custom);

  if (askBtn) askBtn.addEventListener('click', (e) => { e.preventDefault(); submitAsk(); });
  if (copyJobBtn) {
    copyJobBtn.addEventListener('click', async () => {
      const id = copyJobBtn.dataset.jobId || lastJobId;
      if (!id) return;
      await copyToClipboard(id);
      toast(`Copied ${id}`, 'success');
    });
  }
  if (openChatBtn) openChatBtn.addEventListener('click', () => openInChat(lastSessionId));
  if (openObsBtn) openObsBtn.addEventListener('click', () => openInObserve(lastJobId));
  if (refreshBtn) refreshBtn.addEventListener('click', () => { renderSessions(); toast('Sessions refreshed', 'info'); });

  setSelectedWiki('', '');
  showJobId('');

  // --- Quiz / Due reviews [CARD-242] + learner pressure [CARD-243] ---
  const extractQuizBtn = $('educationExtractQuizBtn');
  const nextQuizBtn = $('educationNextQuizBtn');
  const pressureAskBtn = $('educationPressureAskBtn');
  const learnerSummaryEl = $('educationLearnerSummary');
  const refreshDueBtn = $('educationRefreshDueBtn');
  const runRetentionBtn = $('educationRunRetentionBtn');
  const quizPromptEl = $('educationQuizPrompt');
  const quizAnswerInput = $('educationQuizAnswerInput');
  const quizGradeBtn = $('educationQuizGradeBtn');
  const quizGradeResult = $('educationQuizGradeResult');
  const dueListEl = $('educationDueList');
  let activeQuizItem = null;

  function setQuizItem(item) {
    activeQuizItem = item || null;
    if (quizPromptEl) {
      quizPromptEl.textContent = activeQuizItem
        ? `Q: ${activeQuizItem.prompt || ''} (${activeQuizItem.item_id || ''})`
        : 'No quiz item loaded.';
    }
    if (quizAnswerInput) quizAnswerInput.value = '';
    if (quizGradeResult) quizGradeResult.textContent = '';
  }

  async function refreshLearnerSummary() {
    if (!learnerSummaryEl) return;
    try {
      const agentId = state.selectedAgentId || 'assistant';
      const res = await fetch(`/api/education/learner?agent_id=${encodeURIComponent(agentId)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const weak = data.weakness_count || 0;
      const strong = data.strength_count || 0;
      const top = Array.isArray(data.items) && data.items[0] ? data.items[0] : null;
      learnerSummaryEl.textContent = top
        ? `Learner: ${weak} weak / ${strong} strong — next pressure: ${top.item_id || ''} (${top.grade || ''}, misses=${top.miss_count || 0})`
        : `Learner: ${weak} weak / ${strong} strong — no items yet`;
    } catch (err) {
      console.error('[Education Studio] learner summary failed:', err);
      learnerSummaryEl.textContent = 'Learner model unavailable';
    }
  }

  async function loadNextQuiz() {
    const agentId = state.selectedAgentId || 'assistant';
    const res = await fetch(`/api/education/quiz/next?agent_id=${encodeURIComponent(agentId)}&limit=1`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const items = Array.isArray(data.items) ? data.items : [];
    if (!items.length) {
      setQuizItem(null);
      toast('No mastery items to quiz', 'info');
      return null;
    }
    setQuizItem(items[0]);
    toast(`Next quiz pressures ${items[0].grade || 'item'} ${items[0].item_id || ''}`, 'success');
    await refreshDueList();
    await refreshLearnerSummary();
    return items[0];
  }

  async function refreshDueList() {
    if (!dueListEl) return;
    try {
      const agentId = state.selectedAgentId || 'assistant';
      const res = await fetch(`/api/education/mastery/due?agent_id=${encodeURIComponent(agentId)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const items = Array.isArray(data.items) ? data.items : [];
      if (!items.length) {
        dueListEl.innerHTML = '<div class="text-[11px] text-slate-500 px-1">No due reviews.</div>';
        return;
      }
      dueListEl.innerHTML = items
        .map((it) => {
          const id = escapeHtml(it.item_id || '');
          const topic = escapeHtml(it.topic || '');
          const due = escapeHtml(it.next_due || '');
          const prompt = escapeHtml(it.prompt || '');
          return `<button type="button" class="edu-due-item w-full text-left px-2 py-1.5 rounded-lg hover:bg-slate-800 border border-transparent hover:border-slate-700" data-item-id="${id}">
            <div class="text-[11px] font-medium text-slate-200 truncate">${topic}</div>
            <div class="text-[10px] text-slate-400 truncate">${prompt}</div>
            <div class="text-[10px] font-mono text-amber-300/80">due ${due}</div>
          </button>`;
        })
        .join('');
      dueListEl.querySelectorAll('.edu-due-item').forEach((btn) => {
        btn.addEventListener('click', () => {
          const id = btn.getAttribute('data-item-id') || '';
          const found = items.find((x) => x.item_id === id);
          if (found) setQuizItem(found);
        });
      });
    } catch (err) {
      console.error('[Education Studio] due list failed:', err);
      dueListEl.innerHTML = '<div class="text-[11px] text-rose-300 px-1">Due list failed.</div>';
    }
  }

  if (extractQuizBtn) {
    extractQuizBtn.addEventListener('click', async () => {
      const wikiPath = selectedWiki.path || '';
      if (!wikiPath) {
        toast('Select a Wiki note first (Priming/Dual)', 'error');
        return;
      }
      try {
        const agentId = state.selectedAgentId || 'assistant';
        const res = await fetch('/api/education/quiz/extract', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            agent_id: agentId,
            wiki_path: wikiPath,
            topic: selectedWiki.title || (topicInput && topicInput.value) || '',
            persist: true,
          }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const items = Array.isArray(data.items) ? data.items : [];
        if (!items.length) {
          toast('No Quiz Q/A found in note', 'info');
          setQuizItem(null);
          return;
        }
        toast(`Extracted ${items.length} quiz item(s)`, 'success');
        // Prefer weak/due from learner model over first-extracted [CARD-243]
        try {
          await loadNextQuiz();
        } catch (e) {
          setQuizItem(items[0]);
          await refreshDueList();
          await refreshLearnerSummary();
        }
      } catch (err) {
        console.error('[Education Studio] extract quiz failed:', err);
        toast('Extract quiz failed', 'error');
      }
    });
  }

  if (quizGradeBtn) {
    quizGradeBtn.addEventListener('click', async () => {
      if (!activeQuizItem) {
        toast('Load a quiz item first', 'error');
        return;
      }
      const answer = quizAnswerInput ? quizAnswerInput.value : '';
      try {
        const agentId = state.selectedAgentId || 'assistant';
        const res = await fetch('/api/education/quiz/grade', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            agent_id: agentId,
            item_id: activeQuizItem.item_id,
            answer,
            topic: activeQuizItem.topic,
            wiki_path: activeQuizItem.wiki_path,
            prompt: activeQuizItem.prompt,
            expected_answer: activeQuizItem.expected_answer,
          }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (quizGradeResult) {
          quizGradeResult.textContent = data.correct
            ? `Pass — next due ${data.next_due || ''}`
            : `Miss — next due ${data.next_due || ''} (1-3-7-30)`;
          quizGradeResult.className = `text-[10px] self-center ${data.correct ? 'text-emerald-300' : 'text-amber-300'}`;
        }
        toast(data.correct ? 'Pass (binary grade)' : 'Miss scheduled on 1-3-7-30', data.correct ? 'success' : 'info');
        await refreshDueList();
        await refreshLearnerSummary();
      } catch (err) {
        console.error('[Education Studio] grade failed:', err);
        toast('Grade failed', 'error');
      }
    });
  }

  if (refreshDueBtn) refreshDueBtn.addEventListener('click', () => refreshDueList());

  if (nextQuizBtn) {
    nextQuizBtn.addEventListener('click', async () => {
      try {
        await loadNextQuiz();
      } catch (err) {
        console.error('[Education Studio] next quiz failed:', err);
        toast('Next quiz failed', 'error');
      }
    });
  }

  if (pressureAskBtn) {
    pressureAskBtn.addEventListener('click', async () => {
      try {
        const agentId = state.selectedAgentId || 'assistant';
        const topic = (topicInput && topicInput.value) || (activeQuizItem && activeQuizItem.topic) || '';
        const res = await fetch('/api/education/ask/pressure', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            agent_id: agentId,
            topic,
            teach_style: (teachInput && teachInput.value) || '',
            wiki_path: selectedWiki.path || '',
            wiki_title: selectedWiki.title || '',
            mode: selectedMode,
            limit: 3,
          }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (topicInput && data.weak_items && data.weak_items[0] && !topicInput.value) {
          topicInput.value = data.weak_items[0].topic || topicInput.value;
        }
        // Stash pressure into teach style so submitAsk buildEducationAsk can include it if needed;
        // primarily we mint via chat using the server-built ask through a one-shot stream.
        if (!data.ask) {
          toast('No pressure ask built', 'info');
          return;
        }
        // Use submit path: temporarily override by streaming the pressure ask directly.
        const chatCtrl = typeof callbacks.getChatCtrl === 'function' ? callbacks.getChatCtrl() : null;
        const sessionRes = await fetch('/api/sessions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ agent_id: agentId, title: `Education pressure: ${topic || 'weak items'}` }),
        });
        if (!sessionRes.ok) throw new Error(`session HTTP ${sessionRes.status}`);
        const session = await sessionRes.json();
        const sessionId = session.id || session.session_id;
        const payload = buildChatStreamPayload({
          content: data.ask,
          sessionId,
          agentId,
        });
        const streamRes = await fetch('/api/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!streamRes.ok) throw new Error(`stream HTTP ${streamRes.status}`);
        // Minimal SSE read for job_created
        const reader = streamRes.body.getReader();
        const decoder = new TextDecoder();
        let buf = '';
        let jobId = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          const parts = buf.split('\n\n');
          buf = parts.pop() || '';
          for (const chunk of parts) {
            const lines = chunk.split('\n');
            let ev = 'message';
            let dataLine = '';
            for (const ln of lines) {
              if (ln.startsWith('event:')) ev = ln.slice(6).trim();
              if (ln.startsWith('data:')) dataLine += ln.slice(5).trim();
            }
            if (!dataLine) continue;
            let parsed = null;
            try { parsed = JSON.parse(dataLine); } catch { parsed = null; }
            if (ev === 'job_created' || (parsed && (parsed.job_id || parsed.jobId))) {
              jobId = extractJobIdFromSsePayload(parsed) || jobId;
            }
            if (jobId) break;
          }
          if (jobId) break;
        }
        if (jobId) {
          showJobId(jobId);
          upsertEducationSession({
            job_id: jobId,
            session_id: sessionId,
            topic: topic || 'Learner pressure',
            teach_style: 'Pressure known miss (CARD-243)',
            status: 'minted',
          });
          renderSessions();
          toast(`Pressure Ask minted Job ${jobId}`, 'success');
          if (chatCtrl && typeof chatCtrl.selectSession === 'function') {
            await chatCtrl.selectSession(sessionId);
          }
        } else {
          toast('Pressure Ask streamed (no job_id yet)', 'info');
        }
        await refreshLearnerSummary();
      } catch (err) {
        console.error('[Education Studio] pressure ask failed:', err);
        toast('Pressure Ask failed', 'error');
      }
    });
  }

  if (runRetentionBtn) {
    runRetentionBtn.addEventListener('click', async () => {
      try {
        const agentId = state.selectedAgentId || 'assistant';
        const forceId = (activeQuizItem && activeQuizItem.item_id) || null;
        const res = await fetch('/api/education/retention/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ agent_id: agentId, force_due_item_id: forceId }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const ids = (data && data.result && data.result.minted_job_ids) || [];
        if (ids.length) {
          toast(`Retention Routine minted Job ${ids[0]}`, 'success');
          showJobId(ids[0]);
          upsertEducationSession({
            job_id: ids[0],
            session_id: data.session_id || '',
            topic: (activeQuizItem && activeQuizItem.topic) || 'Retrieval review',
            teach_style: 'Retrieval review (Routine→Job)',
            status: 'minted',
          });
          renderSessions();
        } else {
          toast((data && data.result && data.result.reason) || 'Nothing due to resurface', 'info');
        }
        await refreshDueList();
      } catch (err) {
        console.error('[Education Studio] retention run failed:', err);
        toast('Retention Routine failed', 'error');
      }
    });
  }

  refreshDueList();

  // --- Elaboration / explain-it-back [CARD-244] ---
  const elabPromptEl = $('educationElaborationPrompt');
  const elabAnswerInput = $('educationElaborationAnswerInput');
  const elabGradeBtn = $('educationElaborationGradeBtn');
  const elabGradeResult = $('educationElaborationGradeResult');
  const extractElabBtn = $('educationExtractElaborationBtn');
  const nextElabBtn = $('educationNextElaborationBtn');
  let activeElaborationItem = null;

  function renderElaborationItem(item) {
    activeElaborationItem = item || null;
    if (elabPromptEl) {
      if (!item) {
        elabPromptEl.textContent = 'No elaboration item loaded.';
      } else {
        const concepts = (item.required_concepts || []).join(', ');
        elabPromptEl.textContent = `${item.prompt || ''}${concepts ? `  [concepts: ${concepts}]` : ''}  (${item.item_id || ''})`;
      }
    }
    if (elabAnswerInput) elabAnswerInput.value = '';
    if (elabGradeResult) elabGradeResult.textContent = '';
  }

  if (extractElabBtn) {
    extractElabBtn.addEventListener('click', async () => {
      const wikiPath = (selectedWiki && selectedWiki.path) || '';
      if (!wikiPath) {
        toast('Select a Wiki note first', 'error');
        return;
      }
      try {
        const agentId = state.selectedAgentId || 'assistant';
        const res = await fetch('/api/education/elaboration/extract', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            agent_id: agentId,
            wiki_path: wikiPath,
            topic: (selectedWiki && selectedWiki.title) || (topicInput && topicInput.value) || '',
            persist: true,
          }),
        });
        const data = await res.json();
        const items = (data && data.items) || [];
        if (!items.length) {
          toast('No elaboration items found in note', 'info');
          return;
        }
        renderElaborationItem(items[0]);
        toast(`Extracted ${items.length} elaboration item(s)`, 'success');
        await refreshLearnerSummary();
      } catch (err) {
        console.error('[Education Studio] extract elaboration failed:', err);
        toast('Extract elaboration failed', 'error');
      }
    });
  }

  if (nextElabBtn) {
    nextElabBtn.addEventListener('click', async () => {
      try {
        const agentId = state.selectedAgentId || 'assistant';
        const res = await fetch(`/api/education/elaboration/next?agent_id=${encodeURIComponent(agentId)}&limit=1`);
        const data = await res.json();
        const items = (data && data.items) || [];
        if (!items.length) {
          toast('No mastery items for explain-back', 'info');
          return;
        }
        renderElaborationItem(items[0]);
        toast(`Next explain-back: ${items[0].item_id || ''}`, 'success');
        await refreshLearnerSummary();
      } catch (err) {
        console.error('[Education Studio] next elaboration failed:', err);
        toast('Next elaboration failed', 'error');
      }
    });
  }

  if (elabGradeBtn) {
    elabGradeBtn.addEventListener('click', async () => {
      if (!activeElaborationItem) {
        toast('Load an elaboration item first', 'error');
        return;
      }
      const answer = elabAnswerInput ? elabAnswerInput.value : '';
      try {
        const agentId = state.selectedAgentId || 'assistant';
        const res = await fetch('/api/education/elaboration/grade', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            agent_id: agentId,
            item_id: activeElaborationItem.item_id,
            answer,
            topic: activeElaborationItem.topic,
            wiki_path: activeElaborationItem.wiki_path,
            prompt: activeElaborationItem.prompt,
            expected_answer: activeElaborationItem.expected_answer,
            required_concepts: activeElaborationItem.required_concepts || [],
            write_wiki: true,
            write_memory: true,
          }),
        });
        const data = await res.json();
        if (elabGradeResult) {
          elabGradeResult.textContent = data.correct
            ? `Pass — next due ${data.next_due || ''} (wiki/memory write-back)`
            : `Miss — next due ${data.next_due || ''} (ledger + resurface path)`;
          elabGradeResult.className = `text-[10px] self-center ${data.correct ? 'text-emerald-300' : 'text-amber-300'}`;
        }
        toast(
          data.correct ? 'Elaboration pass (binary external)' : 'Elaboration miss — ledger updated',
          data.correct ? 'success' : 'info',
        );
        await refreshLearnerSummary();
        await refreshDueList();
      } catch (err) {
        console.error('[Education Studio] elaboration grade failed:', err);
        toast('Elaboration grade failed', 'error');
      }
    });
  }
  // --- Construction / generative study artifacts [CARD-245] ---
  const generateConstructionBtn = $('educationGenerateConstructionBtn');
  const constructionResultEl = $('educationConstructionResult');
  const constructionPathEl = $('educationConstructionPath');
  if (generateConstructionBtn) {
    generateConstructionBtn.addEventListener('click', async () => {
      const topic = topicInput ? topicInput.value.trim() : '';
      if (!topic) {
        toast('Topic required for Construction', 'error');
        return;
      }
      const wikiPathRaw = selectedWikiPath ? String(selectedWikiPath.textContent || '').trim() : '';
      const wikiPath = wikiPathRaw && !/None selected/i.test(wikiPathRaw) ? wikiPathRaw : '';
      const teachStyle = teachInput ? teachInput.value.trim() : '';
      try {
        generateConstructionBtn.disabled = true;
        if (constructionResultEl) constructionResultEl.textContent = 'Generating...';
        const res = await fetch('/api/education/construction/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            agent_id: 'assistant',
            topic,
            wiki_path: wikiPath || null,
            teach_style: teachStyle || 'generate durable study artifact',
            search_first: true,
          }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          const detail = data && data.detail;
          const msg = (detail && detail.error) || (typeof detail === 'string' ? detail : '') || res.statusText;
          throw new Error(msg || 'construction generate failed');
        }
        const path = data.path || '';
        if (constructionPathEl) {
          constructionPathEl.textContent = path
            ? ('Inbox: ' + path + ' | tools: ' + ((data.tools_used || []).join(', ')))
            : 'Generate returned no path';
        }
        if (constructionResultEl) {
          constructionResultEl.textContent = data.inbox
            ? 'Staged in 00_Inbox (wiki_note_create)'
            : 'Created (check path)';
          constructionResultEl.className = 'text-[10px] self-center text-emerald-300';
        }
        toast('Construction note: ' + (path || data.title || 'ok'), 'success');
        if (selectedMode !== EDUCATION_MODES.construction) setMode(EDUCATION_MODES.construction);
      } catch (err) {
        console.error('[Education Studio] construction generate failed:', err);
        if (constructionResultEl) {
          constructionResultEl.textContent = 'Generate failed';
          constructionResultEl.className = 'text-[10px] self-center text-rose-300';
        }
        toast('Construction generate failed', 'error');
      } finally {
        generateConstructionBtn.disabled = false;
      }
    });
  }


  refreshLearnerSummary();

  renderSessions();

  return {
    loadEducationStudio: () => {
      renderSessions();
      safeCreateIcons();
      refreshEducationApprovals();
    },
    renderSessions,
    submitAsk,
    buildEducationAsk,
  };
}

