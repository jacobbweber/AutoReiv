/**
 * Wiki Studio: Folder Operations & Overview Submodule [REQ-FE-001, CARD-177, CARD-399]
 * Manages folder selection, folder overview card grid, and folder deletion.
 */

import { $, $queryAll, isMobile, safeCreateIcons } from '../../dom.js';
import { escapeHtml } from '../../utils/formatters.js';
import { showToast } from '../../ui/toast.js';

export let activeWikiFolderPath = '';

/**
 * Returns the currently active folder path.
 * @returns {string}
 */
export function getActiveWikiFolderPath() {
  return activeWikiFolderPath;
}

/**
 * Sets the active folder path.
 * @param {string} path
 */
export function setActiveWikiFolderPath(path) {
  activeWikiFolderPath = path || '';
}

/**
 * Deletes a wiki folder and all child notes after user confirmation [CARD-177, REQ-WIKI-024].
 * @param {string} folderRelPath
 * @param {object} options
 */
export async function deleteWikiFolder(
  folderRelPath,
  { onReloadVault = null, onResetActiveState = null, getActiveNotePath = null } = {}
) {
  if (!folderRelPath) return;
  if (!confirm(`Are you sure you want to delete folder '${folderRelPath}' and all notes inside it?`)) return;

  try {
    const res = await fetch(`/api/wiki/folder?path=${encodeURIComponent(folderRelPath)}`, {
      method: 'DELETE',
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || 'Failed to delete folder');

    showToast(`Deleted folder '${folderRelPath}'`, 'info');

    const currentNotePath = typeof getActiveNotePath === 'function' ? getActiveNotePath() : '';
    if (activeWikiFolderPath === folderRelPath || (currentNotePath && currentNotePath.startsWith(folderRelPath))) {
      activeWikiFolderPath = '';
      if (typeof onResetActiveState === 'function') {
        onResetActiveState();
      } else {
        const wikiFolderActionsGroup = $('wikiFolderActionsGroup');
        const wikiNoteActionsGroup = $('wikiNoteActionsGroup');
        const wikiFrontmatterCard = $('wikiFrontmatterCard');
        const activeWikiTitle = $('activeWikiTitle');
        const activeWikiPath = $('activeWikiPath');
        const wikiViewerContent = $('wikiViewerContent');

        if (wikiFolderActionsGroup) wikiFolderActionsGroup.classList.add('hidden');
        if (wikiNoteActionsGroup) wikiNoteActionsGroup.classList.remove('hidden');
        if (wikiFrontmatterCard) wikiFrontmatterCard.classList.add('hidden');
        if (activeWikiTitle) activeWikiTitle.textContent = 'Wiki Vault';
        if (activeWikiPath) activeWikiPath.textContent = 'Select a note or folder';
        if (wikiViewerContent) {
          wikiViewerContent.innerHTML = `<div class="p-8 text-center text-slate-400"><p class="text-sm">Folder deleted.</p></div>`;
        }
      }
    }

    if (typeof onReloadVault === 'function') {
      await onReloadVault();
    }
  } catch (err) {
    console.error('[AutoReiv UI] Failed to delete folder:', err);
    showToast('Failed to delete folder: ' + err.message, 'error');
  }
}

/**
 * Selects a wiki folder and displays its overview card grid [CARD-177, REQ-WIKI-024].
 * @param {string} folderRelPath
 * @param {string} folderTitle
 * @param {Array} notesList
 * @param {boolean} isRoot
 * @param {object} options
 */
export function selectWikiFolder(
  folderRelPath,
  folderTitle,
  notesList = [],
  isRoot = false,
  { onNoteSelect = null, onClearActiveNote = null } = {}
) {
  activeWikiFolderPath = folderRelPath;
  if (typeof onClearActiveNote === 'function') {
    onClearActiveNote();
  }

  // Clear active note highlights
  $queryAll('.wiki-note-item').forEach((btn) => {
    btn.className =
      'wiki-note-item w-full text-left px-2 py-1 rounded-md text-xs transition truncate block flex items-center justify-between text-slate-300 hover:text-white hover:bg-slate-800/70';
  });

  // Update folder row highlights
  $queryAll('.wiki-folder-row').forEach((row) => {
    if (row.dataset.folderPath === folderRelPath) {
      row.classList.add('bg-sky-950/60', 'text-sky-200', 'border-sky-500/50');
    } else {
      row.classList.remove('bg-sky-950/60', 'text-sky-200', 'border-sky-500/50');
    }
  });

  // Close mobile drawer if open
  const wikiDrawerPane = $('wikiDrawerPane');
  const wikiDrawerBackdrop = $('wikiDrawerBackdrop');
  if (isMobile()) {
    if (wikiDrawerPane) wikiDrawerPane.classList.add('-translate-x-full');
    if (wikiDrawerBackdrop) wikiDrawerBackdrop.classList.add('hidden');
  }

  const activeWikiTitle = $('activeWikiTitle');
  const activeWikiPath = $('activeWikiPath');
  const wikiNoteActionsGroup = $('wikiNoteActionsGroup');
  const wikiFolderActionsGroup = $('wikiFolderActionsGroup');
  const wikiDeleteFolderBtn = $('wikiDeleteFolderBtn');
  const wikiRootFolderBadge = $('wikiRootFolderBadge');
  const wikiFrontmatterCard = $('wikiFrontmatterCard');
  const wikiEditorTextarea = $('wikiEditorTextarea');
  const wikiViewerContent = $('wikiViewerContent');

  if (activeWikiTitle) activeWikiTitle.textContent = folderTitle;
  if (activeWikiPath) activeWikiPath.textContent = folderRelPath;

  // Switch action groups
  if (wikiNoteActionsGroup) wikiNoteActionsGroup.classList.add('hidden');
  if (wikiFolderActionsGroup) wikiFolderActionsGroup.classList.remove('hidden');

  if (wikiDeleteFolderBtn) {
    wikiDeleteFolderBtn.classList.toggle('hidden', isRoot);
  }
  if (wikiRootFolderBadge) {
    wikiRootFolderBadge.classList.toggle('hidden', !isRoot);
  }

  if (wikiFrontmatterCard) wikiFrontmatterCard.classList.add('hidden');
  if (wikiEditorTextarea) wikiEditorTextarea.classList.add('hidden');
  if (wikiViewerContent) wikiViewerContent.classList.remove('hidden');

  renderFolderOverview(folderRelPath, folderTitle, notesList, isRoot, { onNoteSelect });
}

/**
 * Renders the folder overview banner and child notes card grid [CARD-177].
 * @param {string} folderRelPath
 * @param {string} folderTitle
 * @param {Array} notesList
 * @param {boolean} isRoot
 * @param {object} options
 */
export function renderFolderOverview(
  folderRelPath,
  folderTitle,
  notesList = [],
  isRoot = false,
  { onNoteSelect = null } = {}
) {
  const wikiViewerContent = $('wikiViewerContent');
  if (!wikiViewerContent) return;
  const count = notesList.length;

  const actionBadge = isRoot
    ? `<div class="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800/90 border border-slate-700 text-slate-400 text-xs font-mono">
         <i data-lucide="shield" class="w-4 h-4 text-amber-400"></i>
         <span>Protected Root Folder</span>
       </div>`
    : `<button type="button" id="wikiOverviewDeleteFolderBtn" class="px-3 py-1.5 bg-rose-600/20 hover:bg-rose-600 text-rose-300 hover:text-white border border-rose-500/40 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition shadow-sm">
         <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
         <span>Delete Folder</span>
       </button>`;

  const notesGrid =
    count === 0
      ? `<div class="p-8 text-center text-slate-500 text-xs italic border border-dashed border-slate-800 rounded-xl bg-slate-900/30">
           No notes in this folder.
         </div>`
      : `<div class="space-y-3">
           <div class="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-400 border-b border-slate-800/80 pb-2">
             <span>Notes (${count})</span>
             <span class="text-[10px] font-mono text-slate-500">Click to open</span>
           </div>
           <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
             ${notesList
               .map(
                 (note) => `
               <button type="button" class="wiki-overview-note-btn text-left p-3 rounded-xl bg-slate-900/70 hover:bg-slate-800 border border-slate-800 hover:border-brand-500/50 transition group flex flex-col justify-between space-y-2 shadow-sm" data-path="${escapeHtml(note.path)}">
                 <div class="flex items-start space-x-2.5 min-w-0">
                   <div class="w-7 h-7 rounded-lg bg-brand-950/60 border border-brand-500/20 flex items-center justify-center text-brand-400 group-hover:text-brand-300 flex-shrink-0 mt-0.5">
                     <i data-lucide="file-text" class="w-3.5 h-3.5"></i>
                   </div>
                   <div class="min-w-0 flex-1">
                     <p class="text-xs font-semibold text-slate-200 group-hover:text-white truncate">${escapeHtml(note.title || 'Untitled')}</p>
                     <p class="text-[10px] font-mono text-slate-500 truncate mt-0.5">${escapeHtml(note.path)}</p>
                   </div>
                 </div>
                 ${note.summary ? `<p class="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">${escapeHtml(note.summary)}</p>` : ''}
                 ${
                   note.tags && note.tags.length
                     ? `<div class="flex flex-wrap gap-1 pt-1">
                          ${note.tags
                            .slice(0, 3)
                            .map(
                              (t) =>
                                `<span class="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 text-[9px] font-mono border border-slate-700/60">#${escapeHtml(t)}</span>`
                            )
                            .join('')}
                          ${note.tags.length > 3 ? `<span class="text-[9px] text-slate-500 font-mono">+${note.tags.length - 3}</span>` : ''}
                        </div>`
                     : ''
                 }
               </button>
             `
               )
               .join('')}
           </div>
         </div>`;

  wikiViewerContent.innerHTML = `
    <div class="max-w-4xl mx-auto space-y-6 animate-fade-in">
      <!-- Folder Hero Banner -->
      <div class="p-5 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-slate-950 border border-slate-800/90 shadow-md">
        <div class="flex items-center justify-between flex-wrap gap-4">
          <div class="space-y-1">
            <div class="flex items-center space-x-2.5">
              <i data-lucide="${isRoot ? 'folder-git-2' : 'folder'}" class="w-5 h-5 ${isRoot ? 'text-purple-400' : 'text-sky-400'}"></i>
              <h2 class="text-base font-bold text-white tracking-tight">${escapeHtml(folderTitle)}</h2>
              <span class="px-2 py-0.5 rounded-full text-[11px] font-mono font-medium bg-slate-800 border border-slate-700 text-slate-300">
                ${count} note${count === 1 ? '' : 's'}
              </span>
            </div>
            <p class="text-[11px] font-mono text-slate-500">${escapeHtml(folderRelPath)}</p>
          </div>
          <div>
            ${actionBadge}
          </div>
        </div>
      </div>

      <!-- Notes in this folder -->
      ${notesGrid}
    </div>
  `;

  safeCreateIcons();

  wikiViewerContent.querySelectorAll('.wiki-overview-note-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const path = btn.dataset.path;
      if (path && typeof onNoteSelect === 'function') {
        onNoteSelect(path);
      }
    });
  });

  const overviewDelBtn = $('wikiOverviewDeleteFolderBtn');
  if (overviewDelBtn) {
    overviewDelBtn.addEventListener('click', () => {
      deleteWikiFolder(folderRelPath, {
        onReloadVault: typeof onNoteSelect === 'function' ? onNoteSelect : null,
      });
    });
  }
}
