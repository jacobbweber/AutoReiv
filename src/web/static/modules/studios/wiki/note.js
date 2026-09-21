/**
 * Wiki Studio: Note Operations & Frontmatter Submodule [REQ-FE-001, CARD-141, CARD-399]
 * Manages note content loading, markdown preview vs editor view switching,
 * note saving/deleting, and the collapsible YAML frontmatter inspector.
 */

import { $, $queryAll, isMobile, safeCreateIcons } from '../../dom.js';
import { escapeHtml } from '../../utils/formatters.js';
import { copyToClipboard } from '../../utils/clipboard.js';
import { showToast } from '../../ui/toast.js';

let currentActiveNotePath = '';
export let activeWikiNotePath = '';
let isFmExpanded = false;
let fmViewMode = 'rendered'; // 'rendered' | 'raw'
let currentRawFrontmatter = '';

/**
 * Returns the currently active wiki note relative path.
 * @returns {string}
 */
export function getActiveWikiNotePath() {
  return currentActiveNotePath;
}

/**
 * Sets the currently active wiki note relative path.
 * @param {string} path
 */
export function setActiveWikiNotePath(path) {
  currentActiveNotePath = path || '';
  activeWikiNotePath = currentActiveNotePath;
}

/**
 * Expands or collapses the Frontmatter Inspector card [CARD-141].
 * @param {boolean} expanded
 */
export function setFmExpanded(expanded) {
  isFmExpanded = !!expanded;
  const wikiFmBody = $('wikiFmBody');
  const wikiToggleFmIcon = $('wikiToggleFmIcon');
  if (wikiFmBody) wikiFmBody.classList.toggle('hidden', !isFmExpanded);
  if (wikiToggleFmIcon) {
    wikiToggleFmIcon.classList.toggle('rotate-180', isFmExpanded);
  }
}

/**
 * Switches the Frontmatter Inspector view between rendered fields and raw YAML.
 * @param {'rendered'|'raw'} mode
 */
export function setFmMode(mode) {
  fmViewMode = mode === 'raw' ? 'raw' : 'rendered';
  const fmRenderedView = $('fmRenderedView');
  const fmRawView = $('fmRawView');
  const fmModeRenderedBtn = $('fmModeRenderedBtn');
  const fmModeRawBtn = $('fmModeRawBtn');

  if (fmRenderedView) fmRenderedView.classList.toggle('hidden', fmViewMode === 'raw');
  if (fmRawView) fmRawView.classList.toggle('hidden', fmViewMode !== 'raw');

  if (fmModeRenderedBtn && fmModeRawBtn) {
    if (fmViewMode === 'rendered') {
      fmModeRenderedBtn.classList.add('bg-indigo-600', 'text-white');
      fmModeRenderedBtn.classList.remove('text-slate-400');
      fmModeRawBtn.classList.remove('bg-indigo-600', 'text-white');
      fmModeRawBtn.classList.add('text-slate-400');
    } else {
      fmModeRawBtn.classList.add('bg-indigo-600', 'text-white');
      fmModeRawBtn.classList.remove('text-slate-400');
      fmModeRenderedBtn.classList.remove('bg-indigo-600', 'text-white');
      fmModeRenderedBtn.classList.add('text-slate-400');
    }
  }
}

/**
 * Toggles note view between rendered markdown preview and raw textarea editor.
 * @param {'preview'|'edit'} mode
 * @param {object} callbacks - Optional renderer callbacks.
 */
export function setWikiViewMode(mode, callbacks = {}) {
  const wikiViewerContent = $('wikiViewerContent');
  const wikiEditorTextarea = $('wikiEditorTextarea');
  const wikiModePreviewBtn = $('wikiModePreviewBtn');
  const wikiModeEditBtn = $('wikiModeEditBtn');

  if (mode === 'edit') {
    if (wikiViewerContent) wikiViewerContent.classList.add('hidden');
    if (wikiEditorTextarea) {
      wikiEditorTextarea.classList.remove('hidden');
      wikiEditorTextarea.focus();
    }
    if (wikiModeEditBtn) {
      wikiModeEditBtn.className = 'px-2 py-1 text-[11px] font-medium rounded-md bg-brand-600 text-white transition';
    }
    if (wikiModePreviewBtn) {
      wikiModePreviewBtn.className =
        'px-2 py-1 text-[11px] font-medium rounded-md text-slate-400 hover:text-slate-200 transition';
    }
  } else {
    if (wikiEditorTextarea) wikiEditorTextarea.classList.add('hidden');
    if (wikiViewerContent) {
      wikiViewerContent.classList.remove('hidden');
      if (callbacks.renderMarkdown && wikiEditorTextarea) {
        callbacks.renderMarkdown(wikiViewerContent, wikiEditorTextarea.value);
      }
    }
    if (wikiModePreviewBtn) {
      wikiModePreviewBtn.className =
        'px-2 py-1 text-[11px] font-medium rounded-md bg-brand-600 text-white transition';
    }
    if (wikiModeEditBtn) {
      wikiModeEditBtn.className =
        'px-2 py-1 text-[11px] font-medium rounded-md text-slate-400 hover:text-slate-200 transition';
    }
  }
}

/**
 * Loads a note by relative path, parses frontmatter metadata, and renders markdown.
 * @param {string} relPath
 * @param {object} options
 */
export async function loadWikiNote(
  relPath,
  { callbacks = {}, onFolderDeselect = null } = {}
) {
  const wikiViewerContent = $('wikiViewerContent');
  const wikiEditorTextarea = $('wikiEditorTextarea');
  const activeWikiPath = $('activeWikiPath');
  const activeWikiTitle = $('activeWikiTitle');
  const wikiNoteActionsGroup = $('wikiNoteActionsGroup');
  const wikiFolderActionsGroup = $('wikiFolderActionsGroup');
  const wikiFrontmatterCard = $('wikiFrontmatterCard');

  if (!wikiViewerContent || !wikiEditorTextarea) return;
  currentActiveNotePath = relPath;
  activeWikiNotePath = relPath;

  if (typeof onFolderDeselect === 'function') {
    onFolderDeselect();
  }

  // Switch Toolbar back to Note Actions
  if (wikiFolderActionsGroup) wikiFolderActionsGroup.classList.add('hidden');
  if (wikiNoteActionsGroup) wikiNoteActionsGroup.classList.remove('hidden');

  // Deselect folder rows
  $queryAll('.wiki-folder-row').forEach((row) => {
    row.classList.remove('bg-sky-950/60', 'text-sky-200', 'border-sky-500/50');
  });

  // Close mobile drawer if open
  const wikiDrawerPane = $('wikiDrawerPane');
  const wikiDrawerBackdrop = $('wikiDrawerBackdrop');
  if (isMobile()) {
    if (wikiDrawerPane) wikiDrawerPane.classList.add('-translate-x-full');
    if (wikiDrawerBackdrop) wikiDrawerBackdrop.classList.add('hidden');
  }

  // Highlight active note item in navigation tree
  $queryAll('.wiki-note-item').forEach((btn) => {
    if (btn.dataset.path === relPath) {
      btn.className =
        'wiki-note-item w-full text-left px-2 py-1 rounded-md text-xs transition truncate block flex items-center justify-between bg-brand-600/30 text-brand-300 font-semibold border border-brand-500/30';
    } else {
      btn.className =
        'wiki-note-item w-full text-left px-2 py-1 rounded-md text-xs transition truncate block flex items-center justify-between text-slate-300 hover:text-white hover:bg-slate-800/70';
    }
  });

  if (activeWikiPath) activeWikiPath.textContent = relPath;
  if (activeWikiTitle) {
    activeWikiTitle.textContent = relPath.split('/').pop().replace(/\.md$/, '').replace(/_/g, ' ').toUpperCase();
  }

  wikiViewerContent.innerHTML = `
    <div class="p-8 text-center text-slate-400">
      <i data-lucide="loader-2" class="w-8 h-8 mx-auto mb-2 text-brand-400 animate-spin"></i>
      <p class="text-xs">Loading note...</p>
    </div>
  `;
  safeCreateIcons();

  try {
    const res = await fetch(`/api/wiki/note?path=${encodeURIComponent(relPath)}`);
    if (!res.ok) throw new Error('Failed to load note');
    const data = await res.json();

    if (activeWikiTitle) activeWikiTitle.textContent = data.title || (data.meta && data.meta.title) || relPath;

    currentRawFrontmatter = data.raw_frontmatter || '';
    const fmRawContent = $('fmRawContent');
    if (fmRawContent) {
      fmRawContent.textContent = currentRawFrontmatter ? `---\n${currentRawFrontmatter}\n---` : 'No frontmatter found.';
    }

    if (wikiFrontmatterCard && data.meta) {
      const meta = data.meta;
      const fmUidBadge = $('fmUidBadge');
      const fmTypeBadge = $('fmTypeBadge');
      const fmStatusBadge = $('fmStatusBadge');
      const fmDomainPill = $('fmDomainPill');
      const fmTopicPill = $('fmTopicPill');
      const fmTelemetryPill = $('fmTelemetryPill');
      const fmSummaryPills = $('fmSummaryPills');
      const fmSummaryWordCount = $('fmSummaryWordCount');
      const fmSummaryText = $('fmSummaryText');
      const fmTagsContainer = $('fmTagsContainer');

      if (fmUidBadge) fmUidBadge.textContent = meta.uid ? `UID: ${meta.uid}` : '';
      if (fmTypeBadge) fmTypeBadge.textContent = meta.document_type || 'note';
      if (fmStatusBadge) fmStatusBadge.textContent = meta.status || 'draft';
      if (fmDomainPill) fmDomainPill.textContent = meta.domain ? `🎓 ${meta.domain}` : '';
      if (fmTopicPill) fmTopicPill.textContent = meta.topic ? `📖 ${meta.topic}` : '';
      if (fmTelemetryPill) {
        fmTelemetryPill.textContent = `Words: ${meta.word_count || 0} | Tokens: ${meta.context_tokens || 0}`;
      }

      if (fmSummaryPills) {
        const pillParts = [meta.document_type || 'note', meta.status || 'draft', meta.domain || 'general'];
        if (meta.tags && meta.tags.length) pillParts.push(`${meta.tags.length} tags`);
        fmSummaryPills.textContent = pillParts.join(' • ');
      }
      if (fmSummaryWordCount) {
        fmSummaryWordCount.textContent = `${meta.word_count || 0} words • ${meta.context_tokens || 0} tokens`;
      }

      if (fmSummaryText) {
        fmSummaryText.textContent = meta.summary || 'No summary provided.';
        fmSummaryText.classList.toggle('hidden', !meta.summary);
      }

      if (fmTagsContainer) {
        fmTagsContainer.innerHTML = (meta.tags || [])
          .map(
            (t) =>
              `<span class="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[9px] border border-slate-700">#${escapeHtml(t)}</span>`
          )
          .join('');
      }
      setFmExpanded(false);
      setFmMode('rendered');
      wikiFrontmatterCard.classList.remove('hidden');
    }

    wikiEditorTextarea.value = data.content || '';
    if (callbacks.renderMarkdown) {
      await callbacks.renderMarkdown(wikiViewerContent, data.content || '');
    } else if (window.marked) {
      wikiViewerContent.innerHTML = window.marked.parse(data.content || '');
    } else {
      wikiViewerContent.innerHTML = `<pre class="whitespace-pre-wrap font-mono text-xs text-slate-200">${escapeHtml(data.content)}</pre>`;
    }

    setWikiViewMode('preview', callbacks);
    safeCreateIcons();
  } catch (err) {
    console.error('[AutoReiv UI] Failed to load note content:', err);
    wikiViewerContent.innerHTML = `
      <div class="p-6 rounded-xl bg-rose-950/40 border border-rose-900 text-rose-300 text-xs">
        <p class="font-bold mb-1">Failed to load note</p>
        <p class="font-mono">${escapeHtml(err.message)}</p>
      </div>
    `;
  }
}

/**
 * Wires note listeners for save, delete, view mode switching, and frontmatter interactions.
 * @param {object} options
 */
export function setupWikiNoteOperations({
  callbacks = {},
  onReloadVault = null,
  onFolderDeselect = null,
} = {}) {
  const wikiModePreviewBtn = $('wikiModePreviewBtn');
  const wikiModeEditBtn = $('wikiModeEditBtn');
  const wikiSaveNoteBtn = $('wikiSaveNoteBtn');
  const wikiDeleteNoteBtn = $('wikiDeleteNoteBtn');
  const wikiViewerContent = $('wikiViewerContent');
  const wikiEditorTextarea = $('wikiEditorTextarea');
  const wikiFrontmatterCard = $('wikiFrontmatterCard');

  const wikiToggleFmBtn = $('wikiToggleFmBtn');
  const wikiFmSummaryBar = $('wikiFmSummaryBar');
  const wikiCollapseFmBtn = $('wikiCollapseFmBtn');
  const fmModeRenderedBtn = $('fmModeRenderedBtn');
  const fmModeRawBtn = $('fmModeRawBtn');
  const fmCopyRawBtn = $('fmCopyRawBtn');

  if (wikiModePreviewBtn) {
    wikiModePreviewBtn.addEventListener('click', () => setWikiViewMode('preview', callbacks));
  }
  if (wikiModeEditBtn) {
    wikiModeEditBtn.addEventListener('click', () => setWikiViewMode('edit', callbacks));
  }

  if (wikiSaveNoteBtn) {
    wikiSaveNoteBtn.addEventListener('click', async () => {
      if (!currentActiveNotePath || !wikiEditorTextarea) return;
      const content = wikiEditorTextarea.value;
      try {
        const res = await fetch('/api/wiki/note', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            path: currentActiveNotePath,
            content: content,
          }),
        });
        if (!res.ok) throw new Error('Failed to save note');
        const span = wikiSaveNoteBtn.querySelector('span');
        if (span) span.textContent = 'Saved!';
        setTimeout(() => {
          if (span) span.textContent = 'Save';
        }, 2000);
        showToast('Note saved successfully', 'success');
        await loadWikiNote(currentActiveNotePath, { callbacks, onReloadVault, onFolderDeselect });
      } catch (err) {
        console.error('[AutoReiv UI] Failed to save note:', err);
        showToast('Failed to save note: ' + err.message, 'error');
      }
    });
  }

  if (wikiDeleteNoteBtn) {
    wikiDeleteNoteBtn.addEventListener('click', async () => {
      if (!currentActiveNotePath) return;
      if (!confirm(`Are you sure you want to delete note '${currentActiveNotePath}'?`)) return;
      try {
        const res = await fetch(`/api/wiki/note?path=${encodeURIComponent(currentActiveNotePath)}`, {
          method: 'DELETE',
        });
        if (!res.ok) throw new Error('Failed to delete note');
        currentActiveNotePath = '';
        if (wikiFrontmatterCard) wikiFrontmatterCard.classList.add('hidden');
        if (wikiViewerContent) {
          wikiViewerContent.innerHTML = `<div class="p-8 text-center text-slate-400"><p class="text-sm">Note deleted.</p></div>`;
        }
        showToast('Note deleted', 'info');
        if (typeof onReloadVault === 'function') {
          await onReloadVault();
        }
      } catch (err) {
        console.error('[AutoReiv UI] Failed to delete note:', err);
        showToast('Failed to delete note: ' + err.message, 'error');
      }
    });
  }

  if (wikiToggleFmBtn) {
    wikiToggleFmBtn.addEventListener('click', () => {
      setFmExpanded(!isFmExpanded);
    });
  }

  if (wikiFmSummaryBar) {
    wikiFmSummaryBar.addEventListener('click', () => {
      setFmExpanded(!isFmExpanded);
    });
  }

  if (wikiCollapseFmBtn) {
    wikiCollapseFmBtn.addEventListener('click', () => {
      setFmExpanded(false);
    });
  }

  if (fmModeRenderedBtn) {
    fmModeRenderedBtn.addEventListener('click', () => {
      setFmMode('rendered');
    });
  }

  if (fmModeRawBtn) {
    fmModeRawBtn.addEventListener('click', () => {
      setFmMode('raw');
    });
  }

  if (fmCopyRawBtn) {
    fmCopyRawBtn.addEventListener('click', async () => {
      if (!currentRawFrontmatter) return;
      try {
        await copyToClipboard(currentRawFrontmatter);
        showToast('YAML frontmatter copied to clipboard', 'success');
      } catch (err) {
        console.error('Failed to copy YAML:', err);
      }
    });
  }
}
