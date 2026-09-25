/**
 * Chat Studio: Dual-Pane Workbench Controller [CARD-138, CARD-306, CARD-397]
 * Manages side-by-side artifact inspection, preview/raw tabs, badge counts, and export.
 */

import { $, safeCreateIcons } from '../../dom.js';

export function countDomSessionArtifacts(messagesContainer) {
  if (!messagesContainer) return 0;
  const ids = new Set();
  messagesContainer.querySelectorAll('.open-artifact-btn[data-artifact-id]').forEach((btn) => {
    const id = (btn.getAttribute('data-artifact-id') || '').trim();
    if (id) ids.add(id);
  });
  return ids.size;
}

export function updateWorkbenchArtifactBadge(count, { workbenchArtifactBadge, workbenchToggleBtn } = {}) {
  if (!workbenchArtifactBadge) return;
  const n = Math.max(0, Number(count) || 0);
  if (n > 0) {
    workbenchArtifactBadge.textContent = n > 99 ? '99+' : String(n);
    workbenchArtifactBadge.classList.remove('hidden');
    workbenchArtifactBadge.classList.add('flex');
    workbenchArtifactBadge.setAttribute('aria-hidden', 'false');
    if (workbenchToggleBtn) {
      workbenchToggleBtn.setAttribute('aria-label', `Toggle Workbench Canvas, ${n} artifact${n === 1 ? '' : 's'}`);
    }
  } else {
    workbenchArtifactBadge.textContent = '';
    workbenchArtifactBadge.classList.add('hidden');
    workbenchArtifactBadge.classList.remove('flex');
    workbenchArtifactBadge.setAttribute('aria-hidden', 'true');
    if (workbenchToggleBtn) {
      workbenchToggleBtn.setAttribute('aria-label', 'Toggle Workbench Canvas');
    }
  }
}

export async function refreshWorkbenchArtifactCount({
  activeSessionId,
  messagesContainer,
  workbenchArtifactBadge,
  workbenchToggleBtn,
  fetchFn = null,
} = {}) {
  const fn = fetchFn || (typeof window !== 'undefined' ? window.fetch : globalThis.fetch);
  let count = 0;
  if (activeSessionId && fn) {
    try {
      const res = await fn(`/api/sessions/${encodeURIComponent(activeSessionId)}/artifacts`);
      if (res && res.ok) {
        const data = await res.json();
        if (Array.isArray(data.artifacts)) count = data.artifacts.length;
      }
    } catch {
      // ignore network errors; fall back to DOM count
    }
  }
  count = Math.max(count, countDomSessionArtifacts(messagesContainer));
  updateWorkbenchArtifactBadge(count, { workbenchArtifactBadge, workbenchToggleBtn });
  return count;
}

const WORKBENCH_ELEMENT_IDS = [
  'chatWorkbenchPane', 'workbenchArtifactTitle', 'workbenchArtifactMeta', 'workbenchContentPreview',
  'workbenchContentRaw', 'workbenchTabPreview', 'workbenchTabRaw', 'workbenchToggleBtn', 'workbenchCloseBtn',
  'workbenchMobileBackBtn', 'workbenchCopyBtn', 'workbenchSaveWikiBtn', 'workbenchArtifactBadge', 'messagesContainer',
];

/** The real template elements initWorkbench needs [CARD-472]. */
export function collectWorkbenchElements() {
  return Object.fromEntries(WORKBENCH_ELEMENT_IDS.map((id) => [id, $(id)]));
}

export function initWorkbench(elements, {
  renderMarkdownFn = null,
  copyToClipboardFn = null,
  showToastFn = null,
  exportMessageToWikiFn = null,
  getActiveSessionId = () => null,
  fetchFn = null,
} = {}) {
  const {
    chatWorkbenchPane,
    workbenchArtifactTitle,
    workbenchArtifactMeta,
    workbenchContentPreview,
    workbenchContentRaw,
    workbenchTabPreview,
    workbenchTabRaw,
    workbenchToggleBtn,
    workbenchCloseBtn,
    workbenchMobileBackBtn,
    workbenchCopyBtn,
    workbenchSaveWikiBtn,
    workbenchArtifactBadge,
    messagesContainer,
  } = elements;

  let activeWorkbenchArtifact = {
    title: 'Document Artifact',
    meta: 'Markdown Artifact',
    content: '',
    raw: '',
  };
  let activeWorkbenchTab = 'preview';

  function setWorkbenchTab(tab) {
    activeWorkbenchTab = tab;
    if (workbenchTabPreview && workbenchTabRaw) {
      if (tab === 'preview') {
        workbenchTabPreview.className = 'px-2 py-0.5 rounded bg-brand-600 text-white font-medium transition';
        workbenchTabRaw.className = 'px-2 py-0.5 rounded text-slate-400 hover:text-white transition';
        if (workbenchContentPreview) workbenchContentPreview.classList.remove('hidden');
        if (workbenchContentRaw) workbenchContentRaw.classList.add('hidden');
      } else {
        workbenchTabRaw.className = 'px-2 py-0.5 rounded bg-brand-600 text-white font-medium transition';
        workbenchTabPreview.className = 'px-2 py-0.5 rounded text-slate-400 hover:text-white transition';
        if (workbenchContentPreview) workbenchContentPreview.classList.add('hidden');
        if (workbenchContentRaw) workbenchContentRaw.classList.remove('hidden');
      }
    }
  }

  function openWorkbench(artifact = {}) {
    activeWorkbenchArtifact = {
      title: artifact.title || 'Document Artifact',
      meta: artifact.meta || 'Markdown Artifact',
      content: artifact.content || '',
      raw: artifact.raw || artifact.content || '',
    };
    if (workbenchArtifactTitle) workbenchArtifactTitle.textContent = activeWorkbenchArtifact.title;
    if (workbenchArtifactMeta) workbenchArtifactMeta.textContent = activeWorkbenchArtifact.meta;

    if (workbenchContentPreview) {
      if (activeWorkbenchArtifact.content) {
        if (typeof renderMarkdownFn === 'function') {
          renderMarkdownFn(workbenchContentPreview, activeWorkbenchArtifact.content);
        } else {
          workbenchContentPreview.textContent = activeWorkbenchArtifact.content;
        }
      } else {
        workbenchContentPreview.innerHTML = `
          <div class="h-full flex flex-col items-center justify-center text-center p-8 space-y-2 text-slate-500" data-card="306">
            <p class="text-sm font-semibold text-slate-300">Workbench is empty</p>
            <p class="text-xs text-slate-500 max-w-sm">Open a message artifact button, or a row from this session&apos;s artifact shelf. Tool results that save artifacts appear here with a real id.</p>
          </div>
        `;
      }
    }
    if (workbenchContentRaw) {
      workbenchContentRaw.textContent = activeWorkbenchArtifact.raw;
    }

    setWorkbenchTab('preview');

    if (chatWorkbenchPane) {
      chatWorkbenchPane.classList.remove('hidden');
      chatWorkbenchPane.classList.add('flex');
    }
    safeCreateIcons();
  }

  function closeWorkbench() {
    if (chatWorkbenchPane) {
      chatWorkbenchPane.classList.add('hidden');
      chatWorkbenchPane.classList.remove('flex');
    }
  }

  // One opener for every "View Full Report" card: fetch, then open [CARD-472]
  async function openArtifactById(artifactId) {
    const id = String(artifactId || '').trim();
    const fn = fetchFn || (typeof window !== 'undefined' ? window.fetch : globalThis.fetch);
    let art = null;
    try {
      const res = id && fn ? await fn(`/api/artifacts/${encodeURIComponent(id)}`) : null;
      if (res && res.ok) art = ((await res.json()) || {}).artifact || null;
    } catch {
      art = null;
    }
    if (!art) {
      if (typeof showToastFn === 'function') showToastFn('Artifact not found', 'error');
      return false;
    }
    openWorkbench({ title: art.title || 'Session Artifact', meta: `Session artifact · ${art.id || id}`, content: art.content || art.summary || '' });
    return true;
  }

  // Setup DOM event listeners
  if (workbenchToggleBtn) {
    workbenchToggleBtn.addEventListener('click', () => {
      if (chatWorkbenchPane && !chatWorkbenchPane.classList.contains('hidden')) {
        closeWorkbench();
      } else {
        openWorkbench(activeWorkbenchArtifact);
      }
    });
  }

  if (workbenchCloseBtn) workbenchCloseBtn.addEventListener('click', closeWorkbench);
  if (workbenchMobileBackBtn) workbenchMobileBackBtn.addEventListener('click', closeWorkbench);
  if (workbenchTabPreview) workbenchTabPreview.addEventListener('click', () => setWorkbenchTab('preview'));
  if (workbenchTabRaw) workbenchTabRaw.addEventListener('click', () => setWorkbenchTab('raw'));

  if (workbenchCopyBtn) {
    workbenchCopyBtn.addEventListener('click', () => {
      const text = activeWorkbenchArtifact.raw || activeWorkbenchArtifact.content || '';
      if (typeof copyToClipboardFn === 'function') {
        copyToClipboardFn(text);
      }
      if (typeof showToastFn === 'function') {
        showToastFn('Artifact copied to clipboard', 'success');
      }
    });
  }

  if (workbenchSaveWikiBtn) {
    workbenchSaveWikiBtn.addEventListener('click', () => {
      const content = activeWorkbenchArtifact.raw || activeWorkbenchArtifact.content || '';
      if (typeof exportMessageToWikiFn === 'function') {
        exportMessageToWikiFn(content);
      } else if (typeof showToastFn === 'function') {
        showToastFn('Saving artifact to Wiki...', 'info');
      }
    });
  }

  // Initial state: collapsed
  closeWorkbench();
  updateWorkbenchArtifactBadge(0, { workbenchArtifactBadge, workbenchToggleBtn });

  return {
    openWorkbench,
    closeWorkbench,
    openArtifactById,
    setWorkbenchTab,
    refreshWorkbenchArtifactCount: () => refreshWorkbenchArtifactCount({
      activeSessionId: getActiveSessionId(),
      messagesContainer,
      workbenchArtifactBadge,
      workbenchToggleBtn,
      fetchFn,
    }),
    getActiveArtifact: () => activeWorkbenchArtifact,
    getActiveTab: () => activeWorkbenchTab,
  };
}
