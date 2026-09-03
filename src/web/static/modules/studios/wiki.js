/**
 * Wiki Studio & Obsidian-Style Mind-Map Module [REQ-FE-001, REQ-WIKI-006, REQ-MIND-003]
 */

import { $, $queryAll, safeCreateIcons } from '../dom.js';
import { escapeHtml } from '../utils/formatters.js';
import { stepSimulation, createSimulationRunner } from '../utils/physics.js';
import { showToast } from '../ui/toast.js';



export function initWikiStudio(state, callbacks = {}) {
  const wikiNavTree = $('wikiNavTree');
  const wikiSearchInput = $('wikiSearchInput');
  const refreshWikiTreeBtn = $('refreshWikiTreeBtn');
  const wikiNewNoteBtn = $('wikiNewNoteBtn');

  const activeWikiTitle = $('activeWikiTitle');
  const activeWikiPath = $('activeWikiPath');
  const wikiModePreviewBtn = $('wikiModePreviewBtn');
  const wikiModeEditBtn = $('wikiModeEditBtn');
  const wikiSaveNoteBtn = $('wikiSaveNoteBtn');
  const wikiDeleteNoteBtn = $('wikiDeleteNoteBtn');

  const wikiFrontmatterCard = $('wikiFrontmatterCard');
  const fmUidBadge = $('fmUidBadge');
  const fmTypeBadge = $('fmTypeBadge');
  const fmStatusBadge = $('fmStatusBadge');
  const fmDomainPill = $('fmDomainPill');
  const fmTopicPill = $('fmTopicPill');
  const fmTelemetryPill = $('fmTelemetryPill');
  const fmSummaryText = $('fmSummaryText');
  const fmTagsContainer = $('fmTagsContainer');

  // Collapsible Frontmatter Elements [CARD-141]
  const wikiToggleFmBtn = $('wikiToggleFmBtn');
  const wikiToggleFmIcon = $('wikiToggleFmIcon');
  const wikiFmSummaryBar = $('wikiFmSummaryBar');
  const wikiFmBody = $('wikiFmBody');
  const fmSummaryPills = $('fmSummaryPills');
  const fmSummaryWordCount = $('fmSummaryWordCount');
  const fmExpandIndicator = $('fmExpandIndicator');
  const wikiCollapseFmBtn = $('wikiCollapseFmBtn');
  const fmModeRenderedBtn = $('fmModeRenderedBtn');
  const fmModeRawBtn = $('fmModeRawBtn');
  const fmRenderedView = $('fmRenderedView');
  const fmRawView = $('fmRawView');
  const fmRawContent = $('fmRawContent');
  const fmCopyRawBtn = $('fmCopyRawBtn');

  let isFmExpanded = false;
  let fmViewMode = 'rendered'; // 'rendered' | 'raw'
  let currentRawFrontmatter = '';

  function setFmExpanded(expanded) {
    isFmExpanded = !!expanded;
    if (wikiFmBody) wikiFmBody.classList.toggle('hidden', !isFmExpanded);
    if (fmExpandIndicator) fmExpandIndicator.textContent = isFmExpanded ? 'Collapse ▴' : 'Expand ▾';
    if (wikiToggleFmIcon) {
      wikiToggleFmIcon.classList.toggle('rotate-180', isFmExpanded);
    }
  }

  function setFmMode(mode) {
    fmViewMode = mode === 'raw' ? 'raw' : 'rendered';
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

  const wikiViewerContent = $('wikiViewerContent');
  const wikiEditorTextarea = $('wikiEditorTextarea');

  // Modals
  const wikiNewNoteModal = $('wikiNewNoteModal');
  const wikiNewNoteCloseBtn = $('wikiNewNoteCloseBtn');
  const wikiNewNoteCancelBtn = $('wikiNewNoteCancelBtn');
  const wikiNewNoteSubmitBtn = $('wikiNewNoteSubmitBtn');
  const newNoteTitleInput = $('newNoteTitleInput');
  const newNoteCategorySelect = $('newNoteCategorySelect');
  const newNoteDomainGroup = $('newNoteDomainGroup');
  const newNoteDomainInput = $('newNoteDomainInput');
  const newNoteTopicInput = $('newNoteTopicInput');
  const newNoteTypeGroup = $('newNoteTypeGroup');
  const newNoteTypeSelect = $('newNoteTypeSelect');
  const newNoteTagsInput = $('newNoteTagsInput');
  const newNoteSummaryInput = $('newNoteSummaryInput');
  const newNoteBodyInput = $('newNoteBodyInput');

  // Mind Map Canvas Elements
  const wikiMindMapViewBtn = $('wikiMindMapViewBtn');
  const wikiMindMapModal = $('wikiMindMapModal');
  const wikiMindMapCloseBtn = $('wikiMindMapCloseBtn');
  const mindMapSearchInput = $('mindMapSearchInput');
  const mmToggleNotes = $('mmToggleNotes');
  const mmToggleTags = $('mmToggleTags');
  const mmToggleDomains = $('mmToggleDomains');
  const mmToggleTopics = $('mmToggleTopics');
  const mmRepulsionSlider = $('mmRepulsionSlider');
  const mmZoomInBtn = $('mmZoomInBtn');
  const mmZoomOutBtn = $('mmZoomOutBtn');
  const mmResetViewBtn = $('mmResetViewBtn');
  const wikiMindMapCanvas = $('wikiMindMapCanvas');
  const mindMapCanvasContainer = $('mindMapCanvasContainer');
  const mindMapTooltip = $('mindMapTooltip');
  const mmStatsNodes = $('mmStatsNodes');
  const mmStatsEdges = $('mmStatsEdges');

  let cachedWikiTree = null;
  let activeWikiNotePath = '';
  const expandedWikiFolders = new Set(['inbox', 'notes', 'resources']);

  let mmRawGraphData = null;
  let mmNodes = [];
  let mmEdges = [];
  let mmTransform = { x: 0, y: 0, scale: 1 };
  let mmDraggingNode = null;
  let mmDragStartPos = { x: 0, y: 0 };
  let mmIsPanning = false;
  let mmPanStart = { x: 0, y: 0 };
  let mmHoveredNode = null;
  let mmRunner = null;
  let mmPhysics = {

    repulsion: 250,
    spring: 0.035,
    linkDist: 100,
    damping: 0.88,
    centerGravity: 0.015,
  };

  async function loadWikiVault() {
    if (!wikiNavTree) return;
    try {
      const res = await fetch('/api/wiki/tree');
      if (!res.ok) throw new Error('Failed to load wiki tree');
      cachedWikiTree = await res.json();
      renderWikiTree(cachedWikiTree, wikiSearchInput ? wikiSearchInput.value : '');
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load wiki tree:', err);
      wikiNavTree.innerHTML = `<p class="text-xs text-rose-400 p-2">Failed to load wiki tree: ${escapeHtml(err.message)}</p>`;
    }
  }

  function renderWikiTree(tree, filterText = '') {
    if (!wikiNavTree || !tree) return;
    wikiNavTree.innerHTML = '';
    const currentQuery = (wikiSearchInput ? wikiSearchInput.value : filterText).toLowerCase().trim();

    expandedWikiFolders.add('inbox');
    expandedWikiFolders.add('notes');
    expandedWikiFolders.add('resources');
    if (tree.resources) {
      Object.keys(tree.resources).forEach((sub) => {
        expandedWikiFolders.add(`resources_${sub}`);
      });
    }

    if (tree.notes) {
      Object.entries(tree.notes).forEach(([domain, topicMap]) => {
        if (topicMap && typeof topicMap === 'object') {
          expandedWikiFolders.add(`notes_${domain}`);
          Object.keys(topicMap).forEach((topic) => {
            expandedWikiFolders.add(`topic_${domain}_${topic}`);
          });
        }
      });
    }

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
      <button type="button" class="wiki-folder-toggle w-full flex items-center justify-between text-slate-400 hover:text-white font-bold uppercase tracking-wider text-[10px] px-2 py-1.5 rounded-lg hover:bg-slate-800/60 transition group text-left">
        <div class="flex items-center space-x-1.5 min-w-0 truncate">
          <i data-lucide="${isInboxExpanded ? 'chevron-down' : 'chevron-right'}" class="w-3 h-3 text-slate-500 group-hover:text-slate-300 transition-transform"></i>
          <i data-lucide="inbox" class="w-3.5 h-3.5 text-amber-400"></i>
          <span>inbox (Staging)</span>
        </div>
        <span class="text-slate-600 font-mono text-[10px]">(${totalInboxNotes})</span>
      </button>
      <div class="wiki-inbox-body space-y-1 pl-2 border-l border-slate-800/80 ml-2.5 ${isInboxExpanded ? '' : 'hidden'}"></div>
    `;

    inboxWrapper.querySelector('.wiki-folder-toggle')?.addEventListener('click', () => {
      if (expandedWikiFolders.has('inbox')) expandedWikiFolders.delete('inbox');
      else expandedWikiFolders.add('inbox');
      renderWikiTree(tree, currentQuery);
    });

    const inboxBody = inboxWrapper.querySelector('.wiki-inbox-body');
    if (matchingInbox.length === 0) {
      inboxBody.innerHTML = '<p class="text-[10px] text-slate-600 italic px-2 py-1">No staged notes</p>';
    } else {
      matchingInbox.forEach((n) => {
        inboxBody.appendChild(createNoteTreeButton(n));
      });
    }
    wikiNavTree.appendChild(inboxWrapper);

    // 2. NOTES (Warehouse) Section
    const notesTree = tree.notes || {};
    let totalWarehouseNotes = 0;
    Object.values(notesTree).forEach((dom) => {
      Object.values(dom || {}).forEach((topicNotes) => (totalWarehouseNotes += (topicNotes || []).length));
    });

    const notesWrapper = document.createElement('div');
    notesWrapper.className = 'space-y-1';
    const isNotesExpanded = currentQuery ? true : expandedWikiFolders.has('notes');

    notesWrapper.innerHTML = `
      <button type="button" class="wiki-folder-toggle w-full flex items-center justify-between text-slate-400 hover:text-white font-bold uppercase tracking-wider text-[10px] px-2 py-1.5 rounded-lg hover:bg-slate-800/60 transition group text-left">
        <div class="flex items-center space-x-1.5 min-w-0 truncate">
          <i data-lucide="${isNotesExpanded ? 'chevron-down' : 'chevron-right'}" class="w-3 h-3 text-slate-500 group-hover:text-slate-300 transition-transform"></i>
          <i data-lucide="book-marked" class="w-3.5 h-3.5 text-brand-400"></i>
          <span>notes (Warehouse)</span>
        </div>
        <span class="text-slate-600 font-mono text-[10px]">(${totalWarehouseNotes})</span>
      </button>
      <div class="wiki-notes-body space-y-1 pl-2 border-l border-slate-800/80 ml-2.5 ${isNotesExpanded ? '' : 'hidden'}"></div>
    `;

    notesWrapper.querySelector('.wiki-folder-toggle')?.addEventListener('click', () => {
      if (expandedWikiFolders.has('notes')) expandedWikiFolders.delete('notes');
      else expandedWikiFolders.add('notes');
      renderWikiTree(tree, currentQuery);
    });

    const notesBody = notesWrapper.querySelector('.wiki-notes-body');
    Object.entries(notesTree).forEach(([domain, topicMap]) => {
      const domainKey = `notes_${domain}`;
      const isDomainExpanded = currentQuery ? true : expandedWikiFolders.has(domainKey);

      let domainCount = 0;
      Object.values(topicMap || {}).forEach((arr) => (domainCount += (arr || []).length));

      const domainWrapper = document.createElement('div');
      domainWrapper.className = 'space-y-0.5';
      domainWrapper.innerHTML = `
        <button type="button" class="w-full text-left px-2 py-1 rounded-md text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 flex items-center justify-between transition group">
          <div class="flex items-center space-x-1.5 min-w-0 truncate">
            <i data-lucide="${isDomainExpanded ? 'chevron-down' : 'chevron-right'}" class="w-3 h-3 text-slate-500 group-hover:text-slate-300 transition-transform"></i>
            <i data-lucide="graduation-cap" class="w-3.5 h-3.5 text-amber-400"></i>
            <span class="truncate text-[11px] font-mono">${escapeHtml(domain)}</span>
          </div>
          <span class="text-[10px] font-mono text-slate-500">(${domainCount})</span>
        </button>
        <div class="domain-topics-body space-y-0.5 pl-3 border-l border-slate-800/80 ml-2 ${isDomainExpanded ? '' : 'hidden'}"></div>
      `;

      domainWrapper.querySelector('button')?.addEventListener('click', () => {
        if (expandedWikiFolders.has(domainKey)) expandedWikiFolders.delete(domainKey);
        else expandedWikiFolders.add(domainKey);
        renderWikiTree(tree, currentQuery);
      });

      const topicsBody = domainWrapper.querySelector('.domain-topics-body');
      Object.entries(topicMap || {}).forEach(([topic, noteList]) => {
        const matching = (noteList || []).filter((n) => {
          if (!currentQuery) return true;
          const titleMatch = (n.title || '').toLowerCase().includes(currentQuery);
          const tagMatch = (n.tags || []).some((t) => t && String(t).toLowerCase().includes(currentQuery));
          const taxMatch = domain.toLowerCase().includes(currentQuery) || topic.toLowerCase().includes(currentQuery);
          return titleMatch || tagMatch || taxMatch;
        });
        if (matching.length === 0 && currentQuery) return;

        const topicKey = `topic_${domain}_${topic}`;
        const isTopicExpanded = currentQuery ? true : expandedWikiFolders.has(topicKey);

        const topicWrapper = document.createElement('div');
        topicWrapper.className = 'space-y-0.5';
        topicWrapper.innerHTML = `
          <button type="button" class="w-full text-left px-2 py-1 rounded-md text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800/80 flex items-center justify-between transition group">
            <div class="flex items-center space-x-1.5 min-w-0 truncate">
              <i data-lucide="${isTopicExpanded ? 'chevron-down' : 'chevron-right'}" class="w-3 h-3 text-slate-500 group-hover:text-slate-300 transition-transform"></i>
              <i data-lucide="${isTopicExpanded ? 'folder-open' : 'folder'}" class="w-3.5 h-3.5 text-sky-400"></i>
              <span class="truncate text-[11px] font-mono">${escapeHtml(topic)}</span>
            </div>
            <span class="text-[10px] font-mono text-slate-500">(${matching.length})</span>
          </button>
          <div class="topic-notes-body space-y-0.5 pl-3 border-l border-slate-800/80 ml-2.5 ${isTopicExpanded ? '' : 'hidden'}"></div>
        `;

        topicWrapper.querySelector('button')?.addEventListener('click', () => {
          if (expandedWikiFolders.has(topicKey)) expandedWikiFolders.delete(topicKey);
          else expandedWikiFolders.add(topicKey);
          renderWikiTree(tree, currentQuery);
        });

        const notesListBody = topicWrapper.querySelector('.topic-notes-body');
        matching.forEach((n) => {
          notesListBody.appendChild(createNoteTreeButton(n));
        });
        topicsBody.appendChild(topicWrapper);
      });

      notesBody.appendChild(domainWrapper);
    });

    if (totalWarehouseNotes === 0) {
      notesBody.innerHTML = '<p class="text-[10px] text-slate-600 italic px-2 py-1">No categorized notes</p>';
    }
    wikiNavTree.appendChild(notesWrapper);

    // 3. RESOURCES Section
    const resTree = tree.resources || {};
    let totalResNotes = 0;
    Object.values(resTree).forEach((arr) => (totalResNotes += (arr || []).length));

    const resWrapper = document.createElement('div');
    resWrapper.className = 'space-y-1';
    const isResExpanded = currentQuery ? true : expandedWikiFolders.has('resources');

    resWrapper.innerHTML = `
      <button type="button" class="wiki-folder-toggle w-full flex items-center justify-between text-slate-400 hover:text-white font-bold uppercase tracking-wider text-[10px] px-2 py-1.5 rounded-lg hover:bg-slate-800/60 transition group text-left">
        <div class="flex items-center space-x-1.5 min-w-0 truncate">
          <i data-lucide="${isResExpanded ? 'chevron-down' : 'chevron-right'}" class="w-3 h-3 text-slate-500 group-hover:text-slate-300 transition-transform"></i>
          <i data-lucide="archive" class="w-3.5 h-3.5 text-purple-400"></i>
          <span>resources (Aids/Templates)</span>
        </div>
        <span class="text-slate-600 font-mono text-[10px]">(${totalResNotes})</span>
      </button>
      <div class="wiki-res-body space-y-1 pl-2 border-l border-slate-800/80 ml-2.5 ${isResExpanded ? '' : 'hidden'}"></div>
    `;

    resWrapper.querySelector('.wiki-folder-toggle')?.addEventListener('click', () => {
      if (expandedWikiFolders.has('resources')) expandedWikiFolders.delete('resources');
      else expandedWikiFolders.add('resources');
      renderWikiTree(tree, currentQuery);
    });

    const resBody = resWrapper.querySelector('.wiki-res-body');
    Object.keys(resTree).forEach((sub) => {
      const subKey = `resources_${sub}`;
      const isSubExpanded = currentQuery ? true : expandedWikiFolders.has(subKey);
      const notes = resTree[sub] || [];
      const matching = notes.filter((n) => !currentQuery || (n.title || '').toLowerCase().includes(currentQuery));
      if (matching.length === 0 && currentQuery) return;

      const subWrapper = document.createElement('div');
      subWrapper.className = 'space-y-0.5';
      subWrapper.innerHTML = `
        <button type="button" class="w-full text-left px-2 py-1 rounded-md text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800/80 flex items-center justify-between transition group">
          <div class="flex items-center space-x-1.5 min-w-0 truncate">
            <i data-lucide="${isSubExpanded ? 'chevron-down' : 'chevron-right'}" class="w-3 h-3 text-slate-500 group-hover:text-slate-300 transition-transform"></i>
            <i data-lucide="${isSubExpanded ? 'folder-open' : 'folder'}" class="w-3.5 h-3.5 text-purple-400"></i>
            <span class="font-mono text-purple-300 text-[11px]">${sub}</span>
          </div>
          <span class="text-[9px] text-slate-600 font-mono">(${matching.length})</span>
        </button>
        <div class="res-sub-body space-y-0.5 pl-3 border-l border-slate-800/80 ml-2.5 ${isSubExpanded ? '' : 'hidden'}"></div>
      `;

      subWrapper.querySelector('button')?.addEventListener('click', () => {
        if (expandedWikiFolders.has(subKey)) expandedWikiFolders.delete(subKey);
        else expandedWikiFolders.add(subKey);
        renderWikiTree(tree, currentQuery);
      });

      const subListBody = subWrapper.querySelector('.res-sub-body');
      matching.forEach((n) => {
        subListBody.appendChild(createNoteTreeButton(n));
      });
      resBody.appendChild(subWrapper);
    });

    if (totalResNotes === 0) {
      resBody.innerHTML =
        '<p class="text-[10px] text-slate-600 italic px-2 py-1">No reference manuals or templates</p>';
    }
    wikiNavTree.appendChild(resWrapper);

    if (!activeWikiNotePath) {
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
      if (firstNote && firstNote.path) {
        loadWikiNote(firstNote.path);
      }
    }

    safeCreateIcons();
  }

  function createNoteTreeButton(note) {
    const isActive = note.path === activeWikiNotePath;
    const itemBtn = document.createElement('button');
    itemBtn.type = 'button';
    itemBtn.dataset.path = note.path;
    itemBtn.className = `wiki-note-item w-full text-left px-2 py-1 rounded-md text-xs transition truncate flex items-center justify-between ${isActive ? 'bg-brand-600/30 text-brand-300 font-semibold border border-brand-500/30' : 'text-slate-300 hover:text-white hover:bg-slate-800/70'}`;
    itemBtn.innerHTML = `
      <div class="flex items-center space-x-1.5 min-w-0 truncate">
        <i data-lucide="file-text" class="w-3 h-3 text-slate-400 flex-shrink-0"></i>
        <span class="truncate text-[11px]">${escapeHtml(note.title || 'Untitled Note')}</span>
      </div>
    `;
    itemBtn.addEventListener('click', () => loadWikiNote(note.path));
    return itemBtn;
  }

  async function loadWikiNote(relPath) {
    if (!wikiViewerContent || !wikiEditorTextarea) return;
    activeWikiNotePath = relPath;

    const wikiDrawerPane = $('wikiDrawerPane');
    const wikiDrawerBackdrop = $('wikiDrawerBackdrop');
    if (window.innerWidth < 768) {
      if (wikiDrawerPane) wikiDrawerPane.classList.add('-translate-x-full');
      if (wikiDrawerBackdrop) wikiDrawerBackdrop.classList.add('hidden');
    }

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
    if (activeWikiTitle)
      activeWikiTitle.textContent = relPath.split('/').pop().replace(/\.md$/, '').replace(/_/g, ' ').toUpperCase();

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
      if (fmRawContent) {
        fmRawContent.textContent = currentRawFrontmatter ? `---\n${currentRawFrontmatter}\n---` : 'No frontmatter found.';
      }

      if (wikiFrontmatterCard && data.meta) {
        const meta = data.meta;
        if (fmUidBadge) fmUidBadge.textContent = meta.uid ? `UID: ${meta.uid}` : '';
        if (fmTypeBadge) fmTypeBadge.textContent = meta.document_type || 'note';
        if (fmStatusBadge) fmStatusBadge.textContent = meta.status || 'draft';
        if (fmDomainPill) fmDomainPill.textContent = meta.domain ? `🎓 ${meta.domain}` : '';
        if (fmTopicPill) fmTopicPill.textContent = meta.topic ? `📖 ${meta.topic}` : '';
        if (fmTelemetryPill)
          fmTelemetryPill.textContent = `Words: ${meta.word_count || 0} | Tokens: ${meta.context_tokens || 0}`;

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

      setWikiViewMode('preview');
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

  function setWikiViewMode(mode) {
    if (mode === 'edit') {
      if (wikiViewerContent) wikiViewerContent.classList.add('hidden');
      if (wikiEditorTextarea) {
        wikiEditorTextarea.classList.remove('hidden');
        wikiEditorTextarea.focus();
      }
      if (wikiModeEditBtn)
        wikiModeEditBtn.className = 'px-2 py-1 text-[11px] font-medium rounded-md bg-brand-600 text-white transition';
      if (wikiModePreviewBtn)
        wikiModePreviewBtn.className =
          'px-2 py-1 text-[11px] font-medium rounded-md text-slate-400 hover:text-slate-200 transition';
    } else {
      if (wikiEditorTextarea) wikiEditorTextarea.classList.add('hidden');
      if (wikiViewerContent) {
        wikiViewerContent.classList.remove('hidden');
        if (callbacks.renderMarkdown && wikiEditorTextarea) {
          callbacks.renderMarkdown(wikiViewerContent, wikiEditorTextarea.value);
        }
      }
      if (wikiModePreviewBtn)
        wikiModePreviewBtn.className =
          'px-2 py-1 text-[11px] font-medium rounded-md bg-brand-600 text-white transition';
      if (wikiModeEditBtn)
        wikiModeEditBtn.className =
          'px-2 py-1 text-[11px] font-medium rounded-md text-slate-400 hover:text-slate-200 transition';
    }
  }

  if (wikiModePreviewBtn) wikiModePreviewBtn.addEventListener('click', () => setWikiViewMode('preview'));
  if (wikiModeEditBtn) wikiModeEditBtn.addEventListener('click', () => setWikiViewMode('edit'));

  if (wikiSaveNoteBtn) {
    wikiSaveNoteBtn.addEventListener('click', async () => {
      if (!activeWikiNotePath || !wikiEditorTextarea) return;
      const content = wikiEditorTextarea.value;
      try {
        const res = await fetch('/api/wiki/note', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            path: activeWikiNotePath,
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
        await loadWikiNote(activeWikiNotePath);
      } catch (err) {
        console.error('[AutoReiv UI] Failed to save note:', err);
        showToast('Failed to save note: ' + err.message, 'error');
      }
    });
  }

  if (wikiDeleteNoteBtn) {
    wikiDeleteNoteBtn.addEventListener('click', async () => {
      if (!activeWikiNotePath) return;
      if (!confirm(`Are you sure you want to delete note '${activeWikiNotePath}'?`)) return;
      try {
        const res = await fetch(`/api/wiki/note?path=${encodeURIComponent(activeWikiNotePath)}`, {
          method: 'DELETE',
        });
        if (!res.ok) throw new Error('Failed to delete note');
        activeWikiNotePath = '';
        if (wikiFrontmatterCard) wikiFrontmatterCard.classList.add('hidden');
        if (wikiViewerContent)
          wikiViewerContent.innerHTML = `<div class="p-8 text-center text-slate-400"><p class="text-sm">Note deleted.</p></div>`;
        showToast('Note deleted', 'info');
        await loadWikiVault();
      } catch (err) {
        console.error('[AutoReiv UI] Failed to delete note:', err);
        showToast('Failed to delete note: ' + err.message, 'error');
      }
    });
  }

  // Frontmatter Inspector Collapse / Expand & Mode Listeners [CARD-141]
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
        await navigator.clipboard.writeText(currentRawFrontmatter);
        showToast('YAML frontmatter copied to clipboard', 'success');
      } catch (err) {
        console.error('Failed to copy YAML:', err);
      }
    });
  }

  if (wikiSearchInput) {
    wikiSearchInput.addEventListener('input', () => {
      if (cachedWikiTree) renderWikiTree(cachedWikiTree, wikiSearchInput.value);
    });
  }

  if (refreshWikiTreeBtn) {
    refreshWikiTreeBtn.addEventListener('click', () => loadWikiVault());
  }

  // New Note Modal
  if (wikiNewNoteBtn) {
    wikiNewNoteBtn.addEventListener('click', () => {
      if (wikiNewNoteModal) {
        wikiNewNoteModal.classList.remove('hidden');
        if (newNoteTitleInput) newNoteTitleInput.value = '';
        if (newNoteSummaryInput) newNoteSummaryInput.value = '';
        if (newNoteTagsInput) newNoteTagsInput.value = '';
        if (newNoteBodyInput) newNoteBodyInput.value = '';
        safeCreateIcons();
      }
    });
  }

  if (wikiNewNoteCloseBtn)
    wikiNewNoteCloseBtn.addEventListener('click', () => wikiNewNoteModal?.classList.add('hidden'));
  if (wikiNewNoteCancelBtn)
    wikiNewNoteCancelBtn.addEventListener('click', () => wikiNewNoteModal?.classList.add('hidden'));

  if (newNoteCategorySelect) {
    newNoteCategorySelect.addEventListener('change', () => {
      const val = newNoteCategorySelect.value;
      if (newNoteDomainGroup) newNoteDomainGroup.classList.toggle('hidden', val === 'inbox' || val === 'resources');
      if (newNoteTypeGroup) newNoteTypeGroup.classList.toggle('hidden', val === 'inbox');
    });
  }

  if (wikiNewNoteSubmitBtn) {
    wikiNewNoteSubmitBtn.addEventListener('click', async () => {
      const title = newNoteTitleInput?.value.trim();
      if (!title) {
        showToast('Please enter a note title.', 'warning');
        return;
      }
      const category = newNoteCategorySelect?.value || 'inbox';
      const domain = newNoteDomainInput?.value.trim() || 'general';
      const topic = newNoteTopicInput?.value.trim() || 'general';
      const document_type = newNoteTypeSelect?.value || 'note';
      const tags = (newNoteTagsInput?.value || '')
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);
      const summary = newNoteSummaryInput?.value.trim() || '';
      const content = newNoteBodyInput?.value.trim() || '';

      try {
        const res = await fetch('/api/wiki/note', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title,
            category,
            domain,
            topic,
            document_type,
            tags,
            summary,
            content,
          }),
        });
        if (!res.ok) throw new Error('Failed to create note');
        const data = await res.json();
        if (wikiNewNoteModal) wikiNewNoteModal.classList.add('hidden');
        showToast(`Note '${title}' created successfully!`, 'success');
        await loadWikiVault();
        if (data.path) await loadWikiNote(data.path);
      } catch (err) {
        console.error('[AutoReiv UI] Failed to create note:', err);
        showToast('Failed to create note: ' + err.message, 'error');
      }
    });
  }


  // Obsidian-Style Mind Map Physics Engine
  async function openMindMap() {
    if (!wikiMindMapModal || !wikiMindMapCanvas) return;
    wikiMindMapModal.classList.remove('hidden');
    safeCreateIcons();

    requestAnimationFrame(() => {
      resizeMindMapCanvas();
    });
    mmTransform = { x: 0, y: 0, scale: 1 };

    try {
      const res = await fetch('/api/wiki/mindmap?include_tags=true&include_taxonomy=true');
      if (!res.ok) throw new Error('Failed to load mind map data');
      mmRawGraphData = await res.json();
      initMindMapGraph();
      startMindMapSimulation();
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load mind map:', err);
    }
  }

  function resizeMindMapCanvas() {
    if (!wikiMindMapCanvas || !mindMapCanvasContainer) return;
    const rect = mindMapCanvasContainer.getBoundingClientRect();
    const w = rect.width > 50 ? rect.width : window.innerWidth > 600 ? window.innerWidth * 0.8 : window.innerWidth - 32;
    const h = rect.height > 50 ? rect.height : Math.max(300, window.innerHeight * 0.75);
    const dpr = window.devicePixelRatio || 1;
    wikiMindMapCanvas.width = w * dpr;
    wikiMindMapCanvas.height = h * dpr;
    wikiMindMapCanvas.style.width = `${w}px`;
    wikiMindMapCanvas.style.height = `${h}px`;
  }

  window.addEventListener('resize', () => {
    if (wikiMindMapModal && !wikiMindMapModal.classList.contains('hidden')) {
      resizeMindMapCanvas();
    }
  });

  function initMindMapGraph() {
    if (!mmRawGraphData) return;
    const searchFilter = (mindMapSearchInput ? mindMapSearchInput.value : '').toLowerCase().trim();
    const showNotes = mmToggleNotes ? mmToggleNotes.checked : true;
    const showTags = mmToggleTags ? mmToggleTags.checked : true;
    const showDomains = mmToggleDomains ? mmToggleDomains.checked : true;
    const showTopics = mmToggleTopics ? mmToggleTopics.checked : true;

    const rawNodes = mmRawGraphData.nodes || [];
    const filteredNodes = rawNodes.filter((n) => {
      if (n.type === 'note' && !showNotes) return false;
      if (n.type === 'tag' && !showTags) return false;
      if (n.type === 'domain' && !showDomains) return false;
      if (n.type === 'topic' && !showTopics) return false;
      return true;
    });

    const activeNodeIdSet = new Set(filteredNodes.map((n) => n.id));
    const rawEdges = mmRawGraphData.edges || [];
    const filteredEdges = rawEdges.filter((e) => activeNodeIdSet.has(e.source) && activeNodeIdSet.has(e.target));

    const existingNodeMap = new Map(mmNodes.map((n) => [n.id, n]));
    const total = filteredNodes.length;

    mmNodes = filteredNodes.map((n, idx) => {
      const existing = existingNodeMap.get(n.id);
      let x, y, vx, vy;

      if (existing) {
        x = existing.x;
        y = existing.y;
        vx = existing.vx;
        vy = existing.vy;
      } else {
        const angle = (idx / Math.max(1, total)) * Math.PI * 2;
        const radius = 100 + (idx % 4) * 60;
        x = Math.cos(angle) * radius + (Math.random() - 0.5) * 20;
        y = Math.sin(angle) * radius + (Math.random() - 0.5) * 20;
        vx = 0;
        vy = 0;
      }

      let r = 8;
      let color = '#6366f1';
      if (n.type === 'note') {
        r = Math.max(8, Math.min(18, 8 + Math.sqrt(n.words || 1)));
        color = '#6366f1';
      } else if (n.type === 'tag') {
        r = Math.max(6, Math.min(14, 6 + (n.count || 1) * 1.5));
        color = '#10b981';
      } else if (n.type === 'domain') {
        r = 16;
        color = '#f59e0b';
      } else if (n.type === 'topic') {
        r = 12;
        color = '#38bdf8';
      }

      const matchesSearch =
        !searchFilter ||
        n.label.toLowerCase().includes(searchFilter) ||
        (n.tags || []).some((t) => t.toLowerCase().includes(searchFilter));

      return {
        ...n,
        x,
        y,
        vx,
        vy,
        radius: r,
        color,
        matchesSearch,
      };
    });

    const nodeById = new Map(mmNodes.map((n) => [n.id, n]));
    mmEdges = filteredEdges
      .map((e) => ({
        ...e,
        sourceNode: nodeById.get(e.source),
        targetNode: nodeById.get(e.target),
      }))
      .filter((e) => e.sourceNode && e.targetNode);

    if (mmStatsNodes) mmStatsNodes.textContent = `${mmNodes.length} nodes`;
    if (mmStatsEdges) mmStatsEdges.textContent = `${mmEdges.length} edges`;
  }

  function initMindMapRunner() {
    if (!mmRunner) {
      mmRunner = createSimulationRunner({
        onTick: tickMindMapPhysics,
        onRender: renderMindMapCanvas,
        getNodes: () => mmNodes,
        energyThreshold: 0.005,
      });
    }
  }

  function startMindMapSimulation() {
    initMindMapRunner();
    mmRunner.start();
  }

  function tickMindMapPhysics() {

    if (mmRepulsionSlider) mmPhysics.repulsion = parseFloat(mmRepulsionSlider.value);
    stepSimulation(mmNodes, mmEdges, mmPhysics);
  }

  function renderMindMapCanvas() {
    if (!wikiMindMapCanvas) return;
    const ctx = wikiMindMapCanvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const width = wikiMindMapCanvas.width / dpr;
    const height = wikiMindMapCanvas.height / dpr;

    ctx.save();
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);

    ctx.fillStyle = '#020617';
    ctx.fillRect(0, 0, width, height);

    ctx.translate(width / 2 + mmTransform.x, height / 2 + mmTransform.y);
    ctx.scale(mmTransform.scale, mmTransform.scale);

    // Draw Edges
    for (let i = 0; i < mmEdges.length; i++) {
      const edge = mmEdges[i];
      const s = edge.sourceNode;
      const t = edge.targetNode;
      if (!s || !t) continue;

      ctx.beginPath();
      ctx.moveTo(s.x, s.y);
      ctx.lineTo(t.x, t.y);

      if (edge.type === 'wikilink') {
        ctx.strokeStyle = 'rgba(129, 140, 248, 0.5)';
        ctx.lineWidth = 1.8;
      } else if (edge.type === 'has_tag') {
        ctx.strokeStyle = 'rgba(16, 185, 129, 0.3)';
        ctx.lineWidth = 1.2;
      } else if (edge.type === 'in_topic') {
        ctx.strokeStyle = 'rgba(56, 189, 248, 0.35)';
        ctx.lineWidth = 1.2;
      } else {
        ctx.strokeStyle = 'rgba(245, 158, 11, 0.35)';
        ctx.lineWidth = 1.4;
      }
      ctx.stroke();
    }

    // Draw Nodes
    for (let i = 0; i < mmNodes.length; i++) {
      const n = mmNodes[i];
      const isHovered = mmHoveredNode && mmHoveredNode.id === n.id;
      const alpha = n.matchesSearch ? 1 : 0.2;

      ctx.save();
      ctx.globalAlpha = alpha;

      if (isHovered) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius + 8, 0, Math.PI * 2);
        ctx.fillStyle = n.color;
        ctx.globalAlpha = 0.25;
        ctx.fill();
        ctx.globalAlpha = alpha;
      }

      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius + 2, 0, Math.PI * 2);
      ctx.strokeStyle = isHovered ? '#ffffff' : n.color;
      ctx.lineWidth = isHovered ? 2.5 : 1.5;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
      ctx.fillStyle = isHovered ? '#ffffff' : n.color;
      ctx.fill();

      ctx.font = isHovered ? 'bold 12px Inter, sans-serif' : '10px Inter, sans-serif';
      ctx.fillStyle = isHovered ? '#ffffff' : '#cbd5e1';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';

      const labelText = n.label.length > 24 ? n.label.slice(0, 22) + '...' : n.label;
      ctx.fillText(labelText, n.x, n.y + n.radius + 5);

      ctx.restore();
    }

    ctx.restore();
  }

  function screenToWorld(clientX, clientY) {
    if (!wikiMindMapCanvas) return { x: 0, y: 0 };
    const rect = wikiMindMapCanvas.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;

    const screenX = clientX - rect.left;
    const screenY = clientY - rect.top;

    const worldX = (screenX - width / 2 - mmTransform.x) / mmTransform.scale;
    const worldY = (screenY - height / 2 - mmTransform.y) / mmTransform.scale;

    return { x: worldX, y: worldY };
  }

  function findNodeAt(worldX, worldY) {
    for (let i = mmNodes.length - 1; i >= 0; i--) {
      const n = mmNodes[i];
      const dx = n.x - worldX;
      const dy = n.y - worldY;
      if (dx * dx + dy * dy <= (n.radius + 6) * (n.radius + 6)) {
        return n;
      }
    }
    return null;
  }

  if (wikiMindMapCanvas) {
    wikiMindMapCanvas.addEventListener('mousedown', (e) => {
      const { x: wx, y: wy } = screenToWorld(e.clientX, e.clientY);
      const hit = findNodeAt(wx, wy);

      if (hit) {
        mmDraggingNode = hit;
        hit.pinned = true;
        mmDragStartPos = { x: e.clientX, y: e.clientY };
      } else {
        mmIsPanning = true;
        mmPanStart = { x: e.clientX - mmTransform.x, y: e.clientY - mmTransform.y };
      }
    });

    wikiMindMapCanvas.addEventListener('mousemove', (e) => {
      const { x: wx, y: wy } = screenToWorld(e.clientX, e.clientY);

      if (mmDraggingNode) {
        mmDraggingNode.x = wx;
        mmDraggingNode.y = wy;
        mmDraggingNode.vx = 0;
        mmDraggingNode.vy = 0;
      } else if (mmIsPanning) {
        mmTransform.x = e.clientX - mmPanStart.x;
        mmTransform.y = e.clientY - mmPanStart.y;
      } else {
        const hit = findNodeAt(wx, wy);
        mmHoveredNode = hit;

        if (hit && mindMapTooltip) {
          mindMapTooltip.classList.remove('hidden');
          mindMapTooltip.style.left = `${e.clientX + 16}px`;
          mindMapTooltip.style.top = `${e.clientY + 16}px`;

          let tooltipHtml = `<div class="font-bold text-white mb-1 flex items-center space-x-1.5">
            <span class="w-2.5 h-2.5 rounded-full" style="background:${hit.color}"></span>
            <span>${escapeHtml(hit.label)}</span>
          </div>`;

          if (hit.type === 'note') {
            tooltipHtml += `<div class="text-[11px] text-slate-400 space-y-0.5 font-mono">
              <p>🎓 Domain: <span class="text-amber-300">${hit.domain || 'general'}</span></p>
              <p>📖 Topic: <span class="text-sky-300">${hit.topic || 'general'}</span></p>
              <p>📊 Words: ${hit.words || 0} | Tokens: ${hit.tokens || 0}</p>
              ${hit.tags && hit.tags.length ? `<p class="text-emerald-400">#${hit.tags.join(' #')}</p>` : ''}
              <p class="text-indigo-300 font-sans mt-1.5 font-semibold">👉 Click to open note in editor</p>
            </div>`;
          } else if (hit.type === 'tag') {
            tooltipHtml += `<p class="text-[11px] text-slate-300">Tag connected to ${hit.count || 1} note(s).</p>`;
          } else if (hit.type === 'domain') {
            tooltipHtml += `<p class="text-[11px] text-slate-300">Degree Domain cluster (${hit.count || 1} notes).</p>`;
          } else if (hit.type === 'topic') {
            tooltipHtml += `<p class="text-[11px] text-slate-300">Class Topic cluster (${hit.count || 1} notes).</p>`;
          }

          mindMapTooltip.innerHTML = tooltipHtml;
        } else if (mindMapTooltip) {
          mindMapTooltip.classList.add('hidden');
        }
      }
    });

    window.addEventListener('mouseup', (e) => {
      if (mmDraggingNode) {
        const distMoved = Math.hypot(e.clientX - mmDragStartPos.x, e.clientY - mmDragStartPos.y);
        const clickedNode = mmDraggingNode;
        mmDraggingNode.pinned = false;
        mmDraggingNode = null;

        if (distMoved < 5 && clickedNode.type === 'note' && clickedNode.path) {
          if (wikiMindMapModal) wikiMindMapModal.classList.add('hidden');
          if (mindMapTooltip) mindMapTooltip.classList.add('hidden');
          if (mmRunner) mmRunner.stop();
          loadWikiNote(clickedNode.path);
        }
      }
      mmIsPanning = false;
    });

    wikiMindMapCanvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.15 : 0.88;
      mmTransform.scale = Math.max(0.2, Math.min(4.0, mmTransform.scale * zoomFactor));
      if (mmRunner) mmRunner.wake();
    });

    let touchStartDist = 0;
    wikiMindMapCanvas.addEventListener(
      'touchstart',
      (e) => {
        if (e.touches.length === 1) {
          const touch = e.touches[0];
          const { x: wx, y: wy } = screenToWorld(touch.clientX, touch.clientY);
          const hit = findNodeAt(wx, wy);

          if (hit) {
            mmDraggingNode = hit;
            hit.pinned = true;
            mmDragStartPos = { x: touch.clientX, y: touch.clientY };
            if (mmRunner) mmRunner.wake();
          } else {
            mmIsPanning = true;
            mmPanStart = { x: touch.clientX - mmTransform.x, y: touch.clientY - mmTransform.y };
          }
        } else if (e.touches.length === 2) {
          touchStartDist = Math.hypot(
            e.touches[0].clientX - e.touches[1].clientX,
            e.touches[0].clientY - e.touches[1].clientY
          );
        }
      },
      { passive: true }
    );

    wikiMindMapCanvas.addEventListener(
      'touchmove',
      (e) => {
        if (e.touches.length === 1) {
          const touch = e.touches[0];
          const { x: wx, y: wy } = screenToWorld(touch.clientX, touch.clientY);

          if (mmDraggingNode) {
            mmDraggingNode.x = wx;
            mmDraggingNode.y = wy;
            mmDraggingNode.vx = 0;
            mmDraggingNode.vy = 0;
            if (mmRunner) mmRunner.wake();
          } else if (mmIsPanning) {
            mmTransform.x = touch.clientX - mmPanStart.x;
            mmTransform.y = touch.clientY - mmPanStart.y;
            if (mmRunner) mmRunner.wake();
          }
        } else if (e.touches.length === 2 && touchStartDist > 0) {
          const dist = Math.hypot(
            e.touches[0].clientX - e.touches[1].clientX,
            e.touches[0].clientY - e.touches[1].clientY
          );
          const factor = dist / touchStartDist;
          mmTransform.scale = Math.max(0.2, Math.min(4.0, mmTransform.scale * (factor > 1 ? 1.03 : 0.97)));
          touchStartDist = dist;
          if (mmRunner) mmRunner.wake();
        }
      },
      { passive: true }
    );

    wikiMindMapCanvas.addEventListener('touchend', () => {
      if (mmDraggingNode) {
        mmDraggingNode.pinned = false;
        mmDraggingNode = null;
      }
      mmIsPanning = false;
      touchStartDist = 0;
    });
  }

  if (wikiMindMapViewBtn) wikiMindMapViewBtn.addEventListener('click', openMindMap);
  if (wikiMindMapCloseBtn) {
    wikiMindMapCloseBtn.addEventListener('click', () => {
      if (wikiMindMapModal) wikiMindMapModal.classList.add('hidden');
      if (mindMapTooltip) mindMapTooltip.classList.add('hidden');
      if (mmRunner) mmRunner.stop();
    });
  }
  if (wikiMindMapModal) {
    wikiMindMapModal.addEventListener('click', (e) => {
      if (e.target === wikiMindMapModal) {
        wikiMindMapModal.classList.add('hidden');
        if (mindMapTooltip) mindMapTooltip.classList.add('hidden');
        if (mmRunner) mmRunner.stop();
      }
    });
  }

  if (mindMapSearchInput) {
    mindMapSearchInput.addEventListener('input', () => {
      initMindMapGraph();
      if (mmRunner) mmRunner.wake();
    });
  }

  [mmToggleNotes, mmToggleTags, mmToggleDomains, mmToggleTopics].forEach((chk) => {
    if (chk)
      chk.addEventListener('change', () => {
        initMindMapGraph();
        if (mmRunner) mmRunner.wake();
      });
  });

  if (mmZoomInBtn)
    mmZoomInBtn.addEventListener('click', () => {
      mmTransform.scale = Math.min(4.0, mmTransform.scale * 1.25);
      if (mmRunner) mmRunner.wake();
    });
  if (mmZoomOutBtn)
    mmZoomOutBtn.addEventListener('click', () => {
      mmTransform.scale = Math.max(0.2, mmTransform.scale * 0.8);
      if (mmRunner) mmRunner.wake();
    });
  if (mmResetViewBtn)
    mmResetViewBtn.addEventListener('click', () => {
      mmTransform = { x: 0, y: 0, scale: 1 };
      if (mmRunner) mmRunner.wake();
    });


  return {
    loadWikiVault,
    loadWikiNote,
    openMindMap,
  };
}

export async function exportMessageToWiki(state, content) {
  const activeAgentTitle = $('activeAgentTitle');
  const agentName = activeAgentTitle ? activeAgentTitle.textContent : 'Agent';
  const title = `${agentName} Note - ${new Date().toISOString().split('T')[0]}`;
  try {
    const res = await fetch('/api/export/wiki', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title,
        content,
        agent_id: state.selectedAgentId || 'assistant',
        session_id: state.activeSessionId,
        category: 'inbox',
        tags: ['single_note', state.selectedAgentId || 'assistant'],
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    showToast('success', `Saved note to Wiki Inbox at '${data.filename || title}'!`);
  } catch (err) {
    console.error('[AutoReiv UI] Failed to export message to wiki:', err);
    showToast('error', 'Failed to save note to Wiki');
  }
}
