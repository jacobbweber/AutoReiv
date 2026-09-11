/**
 * Education Studio shell [CARD-237 / REQ-EDU-SHELL-001..004]
 *
 * Interface-only Studio: Wiki-backed ask → standing Chat Job mint (CARD-236 path)
 * + Education Jobs session list (open in Chat / Observe). Shell + Job mint only.
 */

import { $, escapeHtml, safeCreateIcons } from '../dom.js';
import { showToast } from '../ui/toast.js';
import { copyToClipboard } from '../utils/clipboard.js';
import { buildChatStreamPayload } from './chat.js';

export const EDUCATION_SESSIONS_KEY = 'autoreiv.education.sessions.v1';
export const EDUCATION_ASK_MARKER = '[Education Studio]';

/**
 * Build an outcome-shaped standing ask for CARD-236 Job mint.
 * @param {{ topic: string, teachStyle?: string, wikiPath?: string, wikiTitle?: string }} opts
 */
export function buildEducationAsk(opts = {}) {
  const topic = String(opts.topic || '').trim();
  const teachStyle = String(opts.teachStyle || '').trim() || 'clear, stepwise explanation with one concrete example';
  const wikiPath = String(opts.wikiPath || '').trim();
  const wikiTitle = String(opts.wikiTitle || '').trim();
  const wikiBit = wikiPath
    ? ` Ground the teaching in my Wiki note "${wikiTitle || wikiPath}" (${wikiPath}).`
    : ' Ground the teaching in my existing Wiki notes when relevant.';
  return (
    `${EDUCATION_ASK_MARKER} Teach me about "${topic}".` +
    wikiBit +
    ` How to teach me: ${teachStyle}.` +
    ` Write a short study note back to Wiki summarizing what I should retain.` +
    ` Done-when: a study note exists in Wiki for "${topic}" and I can open it.`
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
 * @param {object} state
 * @param {{ showToast?: Function, switchTab?: Function, getChatCtrl?: Function, getObsCtrl?: Function }} callbacks
 */
export function initEducationStudio(state, callbacks = {}) {
  const toast = callbacks.showToast || showToast;
  const topicInput = $('educationTopicInput');
  const teachInput = $('educationTeachStyleInput');
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

  async function submitAsk() {
    const topic = (topicInput && topicInput.value || '').trim();
    const teachStyle = (teachInput && teachInput.value || '').trim();
    if (!topic) {
      setStatus('Topic is required.', true);
      toast('Enter a topic to learn', 'error');
      return;
    }
    const ask = buildEducationAsk({
      topic,
      teachStyle,
      wikiPath: selectedWiki.path,
      wikiTitle: selectedWiki.title,
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

      const openOriginChatForHitl = () => {
        // REQ-HITL-ORIGIN-001: park operator on parent/origin session so phase HITL projects here.
        if (typeof callbacks.switchTab === 'function') callbacks.switchTab('chat');
        const chatCtrl = typeof callbacks.getChatCtrl === 'function' ? callbacks.getChatCtrl() : null;
        if (chatCtrl && typeof chatCtrl.selectSession === 'function') {
          chatCtrl.selectSession(sessionId);
        }
      };

      const { jobId, successRule } = await drainSseForJobId(res, {
        onJobMinted: ({ jobId: jid, successRule: sr }) => {
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
          openOriginChatForHitl();
        },
        onApprovalRequired: ({ jobId: jid }) => {
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
          openOriginChatForHitl();
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
