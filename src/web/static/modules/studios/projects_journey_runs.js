/**
 * Projects Studio Live-QA Journey Runs & File Viewer Helpers [CARD-634, CARD-716].
 */

import { $, escapeHtml, isMobile } from '../dom.js';
import { fetchJSON } from '../services/api.js';

function refreshIcons() {
  if (typeof window !== 'undefined' && window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

export function formatJourneyWhen(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return String(iso);
    return d.toLocaleString();
  } catch {
    return String(iso);
  }
}

export async function renderJourneyRunsList() {
  const list = $('projectsJourneyRunsList');
  if (!list) return;
  list.innerHTML = '<div class="text-xs text-slate-500 italic p-2">Loading journey runs…</div>';
  try {
    const data = await fetchJSON('/api/projects/journey-runs?limit=40');
    const runs = data.runs || [];
    if (!runs.length) {
      list.innerHTML = '<div class="text-xs text-slate-500 italic p-2">No journey reports on this machine yet.</div>';
      return;
    }
    list.innerHTML = runs
      .map((r) => {
        const ok = String(r.overall || '').toLowerCase() === 'pass';
        const fail = String(r.overall || '').toLowerCase() === 'fail';
        const badge = fail
          ? 'bg-rose-950/80 text-rose-300 border-rose-800'
          : ok
            ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800'
            : 'bg-slate-800 text-slate-300 border-slate-700';
        const when = formatJourneyWhen(r.mtime || r.started_at);
        const step = r.failing_step ? escapeHtml(r.failing_step) : '—';
        return `<button type="button" class="projects-journey-run w-full text-left p-2.5 rounded-xl bg-[#08090c]/70 hover:bg-white/[0.04] border border-white/[0.06] transition" data-card-folder="${escapeHtml(r.card || '')}">
          <div class="flex items-center justify-between gap-2">
            <span class="text-xs font-mono font-semibold text-white truncate">${escapeHtml(r.card || '')}</span>
            <span class="px-1.5 py-0.5 rounded text-[10px] uppercase font-bold border ${badge}">${escapeHtml(r.overall || 'unknown')}</span>
          </div>
          <div class="text-[10px] text-slate-400 mt-1 flex flex-wrap gap-x-3 gap-y-0.5">
            <span>${escapeHtml(when)}</span>
            <span>failing step: ${step}</span>
          </div>
        </button>`;
      })
      .join('');
    refreshIcons();
  } catch (err) {
    list.innerHTML = `<div class="text-xs text-rose-300 p-2">${escapeHtml(String(err.message || err))}</div>`;
  }
}

export async function renderJourneyRunDetail(cardFolder) {
  const detail = $('projectsJourneyRunDetail');
  const title = $('projectsJourneyRunDetailTitle');
  const summary = $('projectsJourneyRunDetailSummary');
  const shots = $('projectsJourneyRunScreenshots');
  if (!detail || !cardFolder) return;
  detail.classList.remove('hidden');
  if (title) title.textContent = cardFolder;
  if (summary) summary.textContent = 'Loading…';
  if (shots) shots.innerHTML = '';
  try {
    const data = await fetchJSON(`/api/projects/journey-runs/${encodeURIComponent(cardFolder)}`);
    if (summary) summary.textContent = data.summary || data.report?.summary_md || '(no summary)';
    if (shots) {
      const list = data.screenshots || [];
      if (!list.length) {
        shots.innerHTML = '<span class="text-[11px] text-slate-500 italic">No screenshots in this folder.</span>';
      } else {
        shots.innerHTML = list
          .map(
            (s) =>
              `<span class="text-[11px] font-mono px-2 py-1 rounded-lg bg-white/[0.04] border border-white/[0.08] text-slate-200" title="${escapeHtml(s.path || '')}">${escapeHtml(s.name || '')}</span>`,
          )
          .join('');
      }
    }
    refreshIcons();
  } catch (err) {
    if (summary) summary.textContent = String(err.message || err);
  }
}

export function resetViewerReadingPane({ clearTree = false } = {}) {
  const treeList = $('projectsTreeList');
  const emptyNotice = $('projectsEmptyNotice');
  const mdEl = $('projectsMarkdownContent');
  const codeEl = $('projectsCodeContent');
  const pathEl = $('projectsViewerPath');
  const metaEl = $('projectsViewerMeta');
  const copyBtn = $('projectsCopyPathBtn');
  const viewerPane = $('projectsViewerPane');

  if (clearTree && treeList) {
    treeList.innerHTML =
      '<div class="p-4 text-xs text-slate-500 italic text-center">No active project selected.<br>Set a project active to explore files.</div>';
  }
  if (viewerPane && isMobile()) {
    viewerPane.classList.add('hidden');
    viewerPane.classList.remove('flex');
  }
  if (emptyNotice) emptyNotice.classList.remove('hidden');
  if (mdEl) {
    mdEl.classList.add('hidden');
    mdEl.innerHTML = '';
  }
  if (codeEl) {
    codeEl.classList.add('hidden');
    codeEl.textContent = '';
  }
  if (pathEl) pathEl.textContent = 'Select an artifact to inspect';
  if (metaEl) metaEl.textContent = '';
  if (copyBtn) copyBtn.classList.add('hidden');
}

export async function renderApprovedCommandsList() {
  const list = $('projectsApprovedCommandsList');
  if (!list) return;
  try {
    const data = await fetchJSON('/api/projects/approved-commands');
    const slug = data && data.slug;
    const commands = (data && data.commands) || [];
    if (!slug) {
      list.innerHTML = '<div class="text-xs text-slate-500 italic p-2">Select a project to view remembered commands.</div>';
      return;
    }
    if (!commands.length) {
      list.innerHTML = '<div class="text-xs text-slate-500 italic p-2">No remembered commands for the active project.</div>';
      return;
    }
    list.innerHTML = commands
      .map(
        (cmd) => `<div class="flex flex-wrap items-center justify-between gap-2 px-3 py-2 rounded-lg border border-white/[0.06] bg-[#08090c]/70">
          <code class="text-xs font-mono text-teal-300 break-all">${escapeHtml(cmd)}</code>
          <button type="button" data-revoke-command="${escapeHtml(cmd)}" class="px-2 py-1 rounded-md bg-rose-900/70 hover:bg-rose-800 text-[11px] font-semibold text-white transition">Remove</button>
        </div>`,
      )
      .join('');
    refreshIcons();
  } catch (err) {
    list.innerHTML = `<div class="text-xs text-rose-300 p-2">${escapeHtml(String(err.message || err))}</div>`;
  }
}

export async function revokeApprovedCommand(command) {
  const q = encodeURIComponent(String(command || ''));
  await fetchJSON(`/api/projects/approved-commands?command=${q}`, {
    method: 'DELETE',
  });
  await renderApprovedCommandsList();
}

