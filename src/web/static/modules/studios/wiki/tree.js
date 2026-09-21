/**
 * Wiki Studio: Vault Tree & Hierarchy Submodule [REQ-FE-001, CARD-177, CARD-399]
 * Manages vault hierarchy rendering, collapsible folders, note tree buttons,
 * tree search filter, and tree refresh.
 */

import { $, $queryAll, safeCreateIcons } from '../../dom.js';
import { escapeHtml } from '../../utils/formatters.js';
import {
  activeWikiFolderPath,
  getActiveWikiFolderPath,
  setActiveWikiFolderPath,
  deleteWikiFolder,
  selectWikiFolder,
  renderFolderOverview,
} from './folder.js';

export {
  activeWikiFolderPath,
  getActiveWikiFolderPath,
  setActiveWikiFolderPath,
  deleteWikiFolder,
  selectWikiFolder,
  renderFolderOverview,
};

const expandedWikiFolders = new Set();
let cachedWikiTree = null;

/**
 * Returns the currently expanded folder set.
 * @returns {Set<string>}
 */
export function getExpandedWikiFolders() {
  return expandedWikiFolders;
}

/**
 * Returns the cached wiki tree object.
 * @returns {object|null}
 */
export function getCachedWikiTree() {
  return cachedWikiTree;
}

/**
 * Creates an interactive tree item button for a single note.
 * @param {object} note
 * @param {object} options
 * @returns {HTMLButtonElement}
 */
export function createNoteTreeButton(note, { onNoteSelect = null, getActiveNotePath = null } = {}) {
  const currentPath = typeof getActiveNotePath === 'function' ? getActiveNotePath() : '';
  const isActive = note.path === currentPath;
  const itemBtn = document.createElement('button');
  itemBtn.type = 'button';
  itemBtn.dataset.path = note.path;
  itemBtn.className = `wiki-note-item w-full text-left px-2 py-1 rounded-md text-xs transition truncate flex items-center justify-between ${
    isActive
      ? 'bg-brand-600/30 text-brand-300 font-semibold border border-brand-500/30'
      : 'text-slate-300 hover:text-white hover:bg-slate-800/70'
  }`;
  itemBtn.innerHTML = `
    <div class="flex items-center space-x-1.5 min-w-0 truncate">
      <i data-lucide="file-text" class="w-3 h-3 text-slate-400 flex-shrink-0"></i>
      <span class="truncate text-[11px]">${escapeHtml(note.title || 'Untitled Note')}</span>
    </div>
  `;
  itemBtn.addEventListener('click', () => {
    if (typeof onNoteSelect === 'function') {
      onNoteSelect(note.path);
    }
  });
  return itemBtn;
}

/**
 * Renders the full hierarchical wiki navigation tree [REQ-WIKI-020, REQ-WIKI-021].
 * @param {object} tree
 * @param {string} filterText
 * @param {object} options
 */
export function renderWikiTree(
  tree,
  filterText = '',
  { onNoteSelect = null, onClearActiveNote = null, getActiveNotePath = null } = {}
) {
  const wikiNavTree = $('wikiNavTree');
  const wikiSearchInput = $('wikiSearchInput');
  if (!wikiNavTree || !tree) return;
  wikiNavTree.innerHTML = '';
  const currentQuery = (wikiSearchInput ? wikiSearchInput.value : filterText).toLowerCase().trim();

  // 1. INBOX Section
  const rawInbox = tree.inbox || [];
  const inboxNotes = Array.isArray(rawInbox) ? rawInbox : Object.values(rawInbox).flat();
  const matchingInbox = inboxNotes.filter((n) => {
    if (!currentQuery) return true;
    const titleMatch = (n.title || '').toLowerCase().includes(currentQuery);
    const tagMatch = (n.tags || []).some((t) => t && String(t).toLowerCase().includes(currentQuery));
    return titleMatch || tagMatch;
  });
  const totalInboxNotes = inboxNotes.length;

  const inboxWrapper = document.createElement('div');
  inboxWrapper.className = 'space-y-1';
  const isInboxExpanded = currentQuery ? true : expandedWikiFolders.has('inbox');

  inboxWrapper.innerHTML = `
    <div class="wiki-folder-row w-full flex items-center justify-between text-slate-400 hover:text-white font-bold uppercase tracking-wider text-[10px] px-2 py-1.5 rounded-lg hover:bg-slate-800/60 transition group cursor-pointer border border-transparent select-none" data-folder-path="00_Inbox">
      <div class="flex items-center space-x-1.5 min-w-0 truncate flex-1">
        <button type="button" class="wiki-chevron-btn p-0.5 hover:bg-slate-700/50 rounded" title="Toggle collapse">
          <i data-lucide="${isInboxExpanded ? 'chevron-down' : 'chevron-right'}" class="w-3 h-3 text-slate-500 group-hover:text-slate-300 transition-transform"></i>
        </button>
        <i data-lucide="inbox" class="w-3.5 h-3.5 text-amber-400"></i>
        <span class="truncate">inbox (Staging)</span>
      </div>
      <span class="text-slate-600 font-mono text-[10px]">(${totalInboxNotes})</span>
    </div>
    <div class="wiki-inbox-body space-y-1 pl-2 border-l border-slate-800/80 ml-2.5 ${isInboxExpanded ? '' : 'hidden'}"></div>
  `;

  inboxWrapper.querySelector('.wiki-chevron-btn')?.addEventListener('click', (e) => {
    e.stopPropagation();
    if (expandedWikiFolders.has('inbox')) expandedWikiFolders.delete('inbox');
    else expandedWikiFolders.add('inbox');
    renderWikiTree(tree, currentQuery, { onNoteSelect, onClearActiveNote, getActiveNotePath });
  });

  inboxWrapper.querySelector('.wiki-folder-row')?.addEventListener('click', () => {
    if (!expandedWikiFolders.has('inbox')) {
      expandedWikiFolders.add('inbox');
      renderWikiTree(tree, currentQuery, { onNoteSelect, onClearActiveNote, getActiveNotePath });
    }
    selectWikiFolder('00_Inbox', 'inbox (Staging)', inboxNotes, true, { onNoteSelect, onClearActiveNote });
  });

  const inboxBody = inboxWrapper.querySelector('.wiki-inbox-body');
  if (matchingInbox.length === 0) {
    inboxBody.innerHTML = '<p class="text-[10px] text-slate-600 italic px-2 py-1">No staged notes</p>';
  } else {
    matchingInbox.forEach((n) => {
      inboxBody.appendChild(createNoteTreeButton(n, { onNoteSelect, getActiveNotePath }));
    });
  }
  wikiNavTree.appendChild(inboxWrapper);

  // 2. NOTES (Warehouse) Section
  const notesTree = tree.notes || {};
  const allWarehouseNotes = [];
  Object.values(notesTree).forEach((dom) => {
    Object.values(dom || {}).forEach((topicNotes) => {
      if (topicNotes) allWarehouseNotes.push(...topicNotes);
    });
  });

  const notesWrapper = document.createElement('div');
  notesWrapper.className = 'space-y-1';
  const isNotesExpanded = currentQuery ? true : expandedWikiFolders.has('notes');

  notesWrapper.innerHTML = `
    <div class="wiki-folder-row w-full flex items-center justify-between text-slate-400 hover:text-white font-bold uppercase tracking-wider text-[10px] px-2 py-1.5 rounded-lg hover:bg-slate-800/60 transition group cursor-pointer border border-transparent select-none" data-folder-path="01_Notes">
      <div class="flex items-center space-x-1.5 min-w-0 truncate flex-1">
        <button type="button" class="wiki-chevron-btn p-0.5 hover:bg-slate-700/50 rounded" title="Toggle collapse">
          <i data-lucide="${isNotesExpanded ? 'chevron-down' : 'chevron-right'}" class="w-3 h-3 text-slate-500 group-hover:text-slate-300 transition-transform"></i>
        </button>
        <i data-lucide="book-marked" class="w-3.5 h-3.5 text-brand-400"></i>
        <span class="truncate">notes (Warehouse)</span>
      </div>
      <span class="text-slate-600 font-mono text-[10px]">(${allWarehouseNotes.length})</span>
    </div>
    <div class="wiki-notes-body space-y-1 pl-2 border-l border-slate-800/80 ml-2.5 ${isNotesExpanded ? '' : 'hidden'}"></div>
  `;

  notesWrapper.querySelector('.wiki-chevron-btn')?.addEventListener('click', (e) => {
    e.stopPropagation();
    if (expandedWikiFolders.has('notes')) expandedWikiFolders.delete('notes');
    else expandedWikiFolders.add('notes');
    renderWikiTree(tree, currentQuery, { onNoteSelect, onClearActiveNote, getActiveNotePath });
  });

  notesWrapper.querySelector('.wiki-folder-row')?.addEventListener('click', () => {
    if (!expandedWikiFolders.has('notes')) {
      expandedWikiFolders.add('notes');
      renderWikiTree(tree, currentQuery, { onNoteSelect, onClearActiveNote, getActiveNotePath });
    }
    selectWikiFolder('01_Notes', 'notes (Warehouse)', allWarehouseNotes, true, { onNoteSelect, onClearActiveNote });
  });

  const notesBody = notesWrapper.querySelector('.wiki-notes-body');
  Object.entries(notesTree).forEach(([domain, topicMap]) => {
    const domainKey = `notes_${domain}`;
    const isDomainExpanded = currentQuery ? true : expandedWikiFolders.has(domainKey);

    const allDomainNotes = [];
    Object.values(topicMap || {}).forEach((arr) => {
      if (arr) allDomainNotes.push(...arr);
    });

    const domainRelPath = `01_Notes/${domain}`;
    const domainWrapper = document.createElement('div');
    domainWrapper.className = 'space-y-0.5';
    domainWrapper.innerHTML = `
      <div class="wiki-folder-row w-full text-left px-2 py-1 rounded-md text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 flex items-center justify-between transition group cursor-pointer border border-transparent select-none" data-folder-path="${escapeHtml(domainRelPath)}">
        <div class="flex items-center space-x-1.5 min-w-0 truncate flex-1">
          <button type="button" class="wiki-chevron-btn p-0.5 hover:bg-slate-700/50 rounded" title="Toggle collapse">
            <i data-lucide="${isDomainExpanded ? 'chevron-down' : 'chevron-right'}" class="w-3 h-3 text-slate-500 group-hover:text-slate-300 transition-transform"></i>
          </button>
          <i data-lucide="graduation-cap" class="w-3.5 h-3.5 text-amber-400"></i>
          <span class="truncate text-[11px] font-mono">${escapeHtml(domain)}</span>
        </div>
        <div class="flex items-center space-x-1.5 shrink-0 ml-1">
          <span class="text-[10px] font-mono text-slate-500">(${allDomainNotes.length})</span>
          <button type="button" class="wiki-folder-delete-btn p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-slate-700/60 opacity-0 group-hover:opacity-100 transition" title="Delete domain '${escapeHtml(domain)}'">
            <i data-lucide="trash-2" class="w-3 h-3"></i>
          </button>
        </div>
      </div>
      <div class="domain-topics-body space-y-0.5 pl-3 border-l border-slate-800/80 ml-2 ${isDomainExpanded ? '' : 'hidden'}"></div>
    `;

    domainWrapper.querySelector('.wiki-chevron-btn')?.addEventListener('click', (e) => {
      e.stopPropagation();
      if (expandedWikiFolders.has(domainKey)) expandedWikiFolders.delete(domainKey);
      else expandedWikiFolders.add(domainKey);
      renderWikiTree(tree, currentQuery, { onNoteSelect, onClearActiveNote, getActiveNotePath });
    });

    domainWrapper.querySelector('.wiki-folder-row')?.addEventListener('click', () => {
      if (!expandedWikiFolders.has(domainKey)) {
        expandedWikiFolders.add(domainKey);
        renderWikiTree(tree, currentQuery, { onNoteSelect, onClearActiveNote, getActiveNotePath });
      }
      selectWikiFolder(domainRelPath, `🎓 ${domain}`, allDomainNotes, false, { onNoteSelect, onClearActiveNote });
    });

    domainWrapper.querySelector('.wiki-folder-delete-btn')?.addEventListener('click', (e) => {
      e.stopPropagation();
      deleteWikiFolder(domainRelPath, {
        onReloadVault: () => loadWikiVault({ onNoteSelect, onClearActiveNote, getActiveNotePath }),
        getActiveNotePath,
      });
    });

    const topicsBody = domainWrapper.querySelector('.domain-topics-body');
    Object.entries(topicMap || {}).forEach(([topic, noteList]) => {
      const topicNotes = noteList || [];
      const matching = topicNotes.filter((n) => {
        if (!currentQuery) return true;
        const titleMatch = (n.title || '').toLowerCase().includes(currentQuery);
        const tagMatch = (n.tags || []).some((t) => t && String(t).toLowerCase().includes(currentQuery));
        const taxMatch = domain.toLowerCase().includes(currentQuery) || topic.toLowerCase().includes(currentQuery);
        return titleMatch || tagMatch || taxMatch;
      });
      if (matching.length === 0 && currentQuery) return;

      const topicKey = `topic_${domain}_${topic}`;
      const isTopicExpanded = currentQuery ? true : expandedWikiFolders.has(topicKey);

      const topicRelPath = `01_Notes/${domain}/${topic}`;
      const topicWrapper = document.createElement('div');
      topicWrapper.className = 'space-y-0.5';
      topicWrapper.innerHTML = `
        <div class="wiki-folder-row w-full text-left px-2 py-1 rounded-md text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800/80 flex items-center justify-between transition group cursor-pointer border border-transparent select-none" data-folder-path="${escapeHtml(topicRelPath)}">
          <div class="flex items-center space-x-1.5 min-w-0 truncate flex-1">
            <button type="button" class="wiki-chevron-btn p-0.5 hover:bg-slate-700/50 rounded" title="Toggle collapse">
              <i data-lucide="${isTopicExpanded ? 'chevron-down' : 'chevron-right'}" class="w-3 h-3 text-slate-500 group-hover:text-slate-300 transition-transform"></i>
            </button>
            <i data-lucide="${isTopicExpanded ? 'folder-open' : 'folder'}" class="w-3.5 h-3.5 text-sky-400"></i>
            <span class="truncate text-[11px] font-mono">${escapeHtml(topic)}</span>
          </div>
          <div class="flex items-center space-x-1.5 shrink-0 ml-1">
            <span class="text-[10px] font-mono text-slate-500">(${topicNotes.length})</span>
            <button type="button" class="wiki-folder-delete-btn p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-slate-700/60 opacity-0 group-hover:opacity-100 transition" title="Delete topic '${escapeHtml(topic)}'">
              <i data-lucide="trash-2" class="w-3 h-3"></i>
            </button>
          </div>
        </div>
        <div class="topic-notes-body space-y-0.5 pl-3 border-l border-slate-800/80 ml-2.5 ${isTopicExpanded ? '' : 'hidden'}"></div>
      `;

      topicWrapper.querySelector('.wiki-chevron-btn')?.addEventListener('click', (e) => {
        e.stopPropagation();
        if (expandedWikiFolders.has(topicKey)) expandedWikiFolders.delete(topicKey);
        else expandedWikiFolders.add(topicKey);
        renderWikiTree(tree, currentQuery, { onNoteSelect, onClearActiveNote, getActiveNotePath });
      });

      topicWrapper.querySelector('.wiki-folder-row')?.addEventListener('click', () => {
        if (!expandedWikiFolders.has(topicKey)) {
          expandedWikiFolders.add(topicKey);
          renderWikiTree(tree, currentQuery, { onNoteSelect, onClearActiveNote, getActiveNotePath });
        }
        selectWikiFolder(topicRelPath, `📁 ${topic}`, topicNotes, false, { onNoteSelect, onClearActiveNote });
      });

      topicWrapper.querySelector('.wiki-folder-delete-btn')?.addEventListener('click', (e) => {
        e.stopPropagation();
        deleteWikiFolder(topicRelPath, {
          onReloadVault: () => loadWikiVault({ onNoteSelect, onClearActiveNote, getActiveNotePath }),
          getActiveNotePath,
        });
      });

      const notesListBody = topicWrapper.querySelector('.topic-notes-body');
      matching.forEach((n) => {
        notesListBody.appendChild(createNoteTreeButton(n, { onNoteSelect, getActiveNotePath }));
      });
      topicsBody.appendChild(topicWrapper);
    });

    notesBody.appendChild(domainWrapper);
  });

  if (allWarehouseNotes.length === 0) {
    notesBody.innerHTML = '<p class="text-[10px] text-slate-600 italic px-2 py-1">No categorized notes</p>';
  }
  wikiNavTree.appendChild(notesWrapper);

  // 3. RESOURCES Section
  const resTree = tree.resources || {};
  const allResNotes = [];
  Object.values(resTree || {}).forEach((arr) => {
    if (arr) allResNotes.push(...arr);
  });

  const resWrapper = document.createElement('div');
  resWrapper.className = 'space-y-1';
  const isResExpanded = currentQuery ? true : expandedWikiFolders.has('resources');

  resWrapper.innerHTML = `
    <div class="wiki-folder-row w-full flex items-center justify-between text-slate-400 hover:text-white font-bold uppercase tracking-wider text-[10px] px-2 py-1.5 rounded-lg hover:bg-slate-800/60 transition group cursor-pointer border border-transparent select-none" data-folder-path="02_Resources">
      <div class="flex items-center space-x-1.5 min-w-0 truncate flex-1">
        <button type="button" class="wiki-chevron-btn p-0.5 hover:bg-slate-700/50 rounded" title="Toggle collapse">
          <i data-lucide="${isResExpanded ? 'chevron-down' : 'chevron-right'}" class="w-3 h-3 text-slate-500 group-hover:text-slate-300 transition-transform"></i>
        </button>
        <i data-lucide="archive" class="w-3.5 h-3.5 text-purple-400"></i>
        <span>resources (Aids/Templates)</span>
      </div>
      <span class="text-slate-600 font-mono text-[10px]">(${allResNotes.length})</span>
    </div>
    <div class="wiki-res-body space-y-1 pl-2 border-l border-slate-800/80 ml-2.5 ${isResExpanded ? '' : 'hidden'}"></div>
  `;

  resWrapper.querySelector('.wiki-chevron-btn')?.addEventListener('click', (e) => {
    e.stopPropagation();
    if (expandedWikiFolders.has('resources')) expandedWikiFolders.delete('resources');
    else expandedWikiFolders.add('resources');
    renderWikiTree(tree, currentQuery, { onNoteSelect, onClearActiveNote, getActiveNotePath });
  });

  resWrapper.querySelector('.wiki-folder-row')?.addEventListener('click', () => {
    if (!expandedWikiFolders.has('resources')) {
      expandedWikiFolders.add('resources');
      renderWikiTree(tree, currentQuery, { onNoteSelect, onClearActiveNote, getActiveNotePath });
    }
    selectWikiFolder('02_Resources', 'resources (Aids/Templates)', allResNotes, true, { onNoteSelect, onClearActiveNote });
  });

  const resBody = resWrapper.querySelector('.wiki-res-body');
  Object.keys(resTree).forEach((sub) => {
    const subKey = `resources_${sub}`;
    const isSubExpanded = currentQuery ? true : expandedWikiFolders.has(subKey);
    const notes = resTree[sub] || [];
    const matching = notes.filter((n) => !currentQuery || (n.title || '').toLowerCase().includes(currentQuery));
    if (matching.length === 0 && currentQuery) return;

    const subRelPath = `02_Resources/${sub}`;
    const subWrapper = document.createElement('div');
    subWrapper.className = 'space-y-0.5';
    subWrapper.innerHTML = `
      <div class="wiki-folder-row w-full text-left px-2 py-1 rounded-md text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800/80 flex items-center justify-between transition group cursor-pointer border border-transparent select-none" data-folder-path="${escapeHtml(subRelPath)}">
        <div class="flex items-center space-x-1.5 min-w-0 truncate flex-1">
          <button type="button" class="wiki-chevron-btn p-0.5 hover:bg-slate-700/50 rounded" title="Toggle collapse">
            <i data-lucide="${isSubExpanded ? 'chevron-down' : 'chevron-right'}" class="w-3 h-3 text-slate-500 group-hover:text-slate-300 transition-transform"></i>
          </button>
          <i data-lucide="${isSubExpanded ? 'folder-open' : 'folder'}" class="w-3.5 h-3.5 text-purple-400"></i>
          <span class="font-mono text-purple-300 text-[11px] truncate">${escapeHtml(sub)}</span>
        </div>
        <div class="flex items-center space-x-1.5 shrink-0 ml-1">
          <span class="text-[9px] text-slate-600 font-mono">(${notes.length})</span>
          <button type="button" class="wiki-folder-delete-btn p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-slate-700/60 opacity-0 group-hover:opacity-100 transition" title="Delete resource folder '${escapeHtml(sub)}'">
            <i data-lucide="trash-2" class="w-3 h-3"></i>
          </button>
        </div>
      </div>
      <div class="res-sub-body space-y-0.5 pl-3 border-l border-slate-800/80 ml-2.5 ${isSubExpanded ? '' : 'hidden'}"></div>
    `;

    subWrapper.querySelector('.wiki-chevron-btn')?.addEventListener('click', (e) => {
      e.stopPropagation();
      if (expandedWikiFolders.has(subKey)) expandedWikiFolders.delete(subKey);
      else expandedWikiFolders.add(subKey);
      renderWikiTree(tree, currentQuery, { onNoteSelect, onClearActiveNote, getActiveNotePath });
    });

    subWrapper.querySelector('.wiki-folder-row')?.addEventListener('click', () => {
      if (!expandedWikiFolders.has(subKey)) {
        expandedWikiFolders.add(subKey);
        renderWikiTree(tree, currentQuery, { onNoteSelect, onClearActiveNote, getActiveNotePath });
      }
      selectWikiFolder(subRelPath, `📦 ${sub}`, notes, false, { onNoteSelect, onClearActiveNote });
    });

    subWrapper.querySelector('.wiki-folder-delete-btn')?.addEventListener('click', (e) => {
      e.stopPropagation();
      deleteWikiFolder(subRelPath, {
        onReloadVault: () => loadWikiVault({ onNoteSelect, onClearActiveNote, getActiveNotePath }),
        getActiveNotePath,
      });
    });

    const subListBody = subWrapper.querySelector('.res-sub-body');
    matching.forEach((n) => {
      subListBody.appendChild(createNoteTreeButton(n, { onNoteSelect, getActiveNotePath }));
    });
    resBody.appendChild(subWrapper);
  });

  if (allResNotes.length === 0) {
    resBody.innerHTML =
      '<p class="text-[10px] text-slate-600 italic px-2 py-1">No reference manuals or templates</p>';
  }
  wikiNavTree.appendChild(resWrapper);

  // 4. ARCHIVE Section
  const rawArchive = tree.archive || tree['03_Archive'] || [];
  const archiveNotes = Array.isArray(rawArchive) ? rawArchive : Object.values(rawArchive).flat();
  const matchingArchive = archiveNotes.filter((n) => {
    if (!currentQuery) return true;
    const titleMatch = (n.title || '').toLowerCase().includes(currentQuery);
    const tagMatch = (n.tags || []).some((t) => t && String(t).toLowerCase().includes(currentQuery));
    return titleMatch || tagMatch;
  });
  const totalArchiveNotes = archiveNotes.length;

  const archiveWrapper = document.createElement('div');
  archiveWrapper.className = 'space-y-1';
  const isArchiveExpanded = currentQuery ? true : expandedWikiFolders.has('archive');

  archiveWrapper.innerHTML = `
    <div class="wiki-folder-row w-full flex items-center justify-between text-slate-400 hover:text-white font-bold uppercase tracking-wider text-[10px] px-2 py-1.5 rounded-lg hover:bg-slate-800/60 transition group cursor-pointer border border-transparent select-none" data-folder-path="03_Archive">
      <div class="flex items-center space-x-1.5 min-w-0 truncate flex-1">
        <button type="button" class="wiki-chevron-btn p-0.5 hover:bg-slate-700/50 rounded" title="Toggle collapse">
          <i data-lucide="${isArchiveExpanded ? 'chevron-down' : 'chevron-right'}" class="w-3 h-3 text-slate-500 group-hover:text-slate-300 transition-transform"></i>
        </button>
        <i data-lucide="archive" class="w-3.5 h-3.5 text-slate-400"></i>
        <span class="truncate">archive (Preserved)</span>
      </div>
      <span class="text-slate-600 font-mono text-[10px]">(${totalArchiveNotes})</span>
    </div>
    <div class="wiki-archive-body space-y-1 pl-2 border-l border-slate-800/80 ml-2.5 ${isArchiveExpanded ? '' : 'hidden'}"></div>
  `;

  archiveWrapper.querySelector('.wiki-chevron-btn')?.addEventListener('click', (e) => {
    e.stopPropagation();
    if (expandedWikiFolders.has('archive')) expandedWikiFolders.delete('archive');
    else expandedWikiFolders.add('archive');
    renderWikiTree(tree, currentQuery, { onNoteSelect, onClearActiveNote, getActiveNotePath });
  });

  archiveWrapper.querySelector('.wiki-folder-row')?.addEventListener('click', () => {
    if (!expandedWikiFolders.has('archive')) {
      expandedWikiFolders.add('archive');
      renderWikiTree(tree, currentQuery, { onNoteSelect, onClearActiveNote, getActiveNotePath });
    }
    selectWikiFolder('03_Archive', 'archive (Preserved)', archiveNotes, true, { onNoteSelect, onClearActiveNote });
  });

  const archiveBody = archiveWrapper.querySelector('.wiki-archive-body');
  if (matchingArchive.length === 0) {
    archiveBody.innerHTML = '<p class="text-[10px] text-slate-600 italic px-2 py-1">No archived notes</p>';
  } else {
    matchingArchive.forEach((n) => {
      archiveBody.appendChild(createNoteTreeButton(n, { onNoteSelect, getActiveNotePath }));
    });
  }
  wikiNavTree.appendChild(archiveWrapper);

  const currentFolderPath = getActiveWikiFolderPath();
  if (currentFolderPath) {
    $queryAll('.wiki-folder-row').forEach((row) => {
      if (row.dataset.folderPath === currentFolderPath) {
        row.classList.add('bg-sky-950/60', 'text-sky-200', 'border-sky-500/50');
      } else {
        row.classList.remove('bg-sky-950/60', 'text-sky-200', 'border-sky-500/50');
      }
    });
  } else {
    const activeNotePath = typeof getActiveNotePath === 'function' ? getActiveNotePath() : '';
    if (!activeNotePath) {
      let firstNote = matchingInbox[0];
      if (!firstNote && tree.notes) {
        for (const dom of Object.values(tree.notes)) {
          for (const list of Object.values(dom)) {
            if (list && list.length > 0) {
              firstNote = list[0];
              break;
            }
          }
          if (firstNote) break;
        }
      }
      if (!firstNote && tree.resources) {
        for (const list of Object.values(tree.resources)) {
          if (list && list.length > 0) {
            firstNote = list[0];
            break;
          }
        }
      }
      if (firstNote && firstNote.path && typeof onNoteSelect === 'function') {
        onNoteSelect(firstNote.path);
      }
    }
  }

  safeCreateIcons();
}

/**
 * Loads the complete wiki vault tree and triggers rendering [REQ-WIKI-020].
 * @param {object} options
 */
export async function loadWikiVault({
  onNoteSelect = null,
  onClearActiveNote = null,
  getActiveNotePath = null,
  filterText = '',
} = {}) {
  const wikiNavTree = $('wikiNavTree');
  const wikiSearchInput = $('wikiSearchInput');
  if (!wikiNavTree) return;
  try {
    const res = await fetch('/api/wiki/tree');
    if (!res.ok) throw new Error('Failed to load wiki tree');
    cachedWikiTree = await res.json();
    const query = filterText || (wikiSearchInput ? wikiSearchInput.value : '');
    renderWikiTree(cachedWikiTree, query, { onNoteSelect, onClearActiveNote, getActiveNotePath });
  } catch (err) {
    console.error('[AutoReiv UI] Failed to load wiki tree:', err);
    wikiNavTree.innerHTML = `<p class="text-xs text-rose-400 p-2">Failed to load wiki tree: ${escapeHtml(err.message)}</p>`;
  }
}

/**
 * Wires tree search input, tree refresh button, and folder delete action button.
 * @param {object} options
 */
export function setupWikiTreeOperations({
  onNoteSelect = null,
  onClearActiveNote = null,
  getActiveNotePath = null,
} = {}) {
  const wikiSearchInput = $('wikiSearchInput');
  const refreshWikiTreeBtn = $('refreshWikiTreeBtn');
  const wikiDeleteFolderBtn = $('wikiDeleteFolderBtn');

  if (wikiSearchInput) {
    wikiSearchInput.addEventListener('input', () => {
      if (cachedWikiTree) {
        renderWikiTree(cachedWikiTree, wikiSearchInput.value, {
          onNoteSelect,
          onClearActiveNote,
          getActiveNotePath,
        });
      }
    });
  }

  if (refreshWikiTreeBtn) {
    refreshWikiTreeBtn.addEventListener('click', () => {
      loadWikiVault({ onNoteSelect, onClearActiveNote, getActiveNotePath });
    });
  }

  if (wikiDeleteFolderBtn) {
    wikiDeleteFolderBtn.addEventListener('click', () => {
      const folderPath = getActiveWikiFolderPath();
      if (folderPath) {
        deleteWikiFolder(folderPath, {
          onReloadVault: () => loadWikiVault({ onNoteSelect, onClearActiveNote, getActiveNotePath }),
          getActiveNotePath,
        });
      }
    });
  }
}
