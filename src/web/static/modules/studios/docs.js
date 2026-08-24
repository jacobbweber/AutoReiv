/**
 * System Documentation & Architecture Specs Studio Module [REQ-FE-001, REQ-SKIL-005, REQ-DOCS-001 - REQ-DOCS-004]
 */

import { $, $query, $queryAll, $on, safeCreateIcons } from '../dom.js';
import { escapeHtml } from '../utils/formatters.js';
import { copyToClipboard } from '../utils/clipboard.js';


export function initDocsStudio(state, callbacks = {}) {
  const docsNavTree = $('docsNavTree');
  const docsSearchInput = $('docsSearchInput');
  const activeDocTitle = $('activeDocTitle');
  const activeDocPath = $('activeDocPath');
  const copyDocPathBtn = $('copyDocPathBtn');
  const docViewerContent = $('docViewerContent');
  const refreshDocsNavBtn = $('refreshDocsNavBtn');

  // Mermaid Modal
  const mermaidZoomModal = $('mermaidZoomModal');
  const mermaidModalCard = $('mermaidModalCard');
  const mermaidModalTitle = $('mermaidModalTitle');
  const mermaidViewport = $('mermaidViewport');
  const mermaidCanvas = $('mermaidCanvas');
  const mermaidZoomLevel = $('mermaidZoomLevel');
  const mermaidZoomInBtn = $('mermaidZoomInBtn');
  const mermaidZoomOutBtn = $('mermaidZoomOutBtn');
  const mermaidZoomResetBtn = $('mermaidZoomResetBtn');
  const mermaidFullscreenBtn = $('mermaidFullscreenBtn');
  const mermaidCloseModalBtn = $('mermaidCloseModalBtn');

  let cachedDocsNav = null;
  let activeDocPathStr = '';
  const collapsedCategoryTitles = new Set();

  const ptz = {
    scale: 1.0,
    panX: 0,
    panY: 0,
    isDragging: false,
    startX: 0,
    startY: 0,
  };

  function updateMermaidTransform() {
    if (!mermaidCanvas) return;
    mermaidCanvas.style.transform = `translate(${ptz.panX}px, ${ptz.panY}px) scale(${ptz.scale})`;
    if (mermaidZoomLevel) {
      mermaidZoomLevel.textContent = `${Math.round(ptz.scale * 100)}%`;
    }
  }

  function resetMermaidPTZ() {
    ptz.scale = 1.0;
    ptz.panX = 0;
    ptz.panY = 0;
    updateMermaidTransform();
  }

  function openMermaidInspector(svgHtml, title = 'Architecture Diagram') {
    if (!mermaidZoomModal || !mermaidCanvas) return;
    mermaidCanvas.innerHTML = svgHtml;
    if (mermaidModalTitle) mermaidModalTitle.textContent = title;
    resetMermaidPTZ();
    mermaidZoomModal.classList.remove('hidden');
    safeCreateIcons();
  }

  function closeMermaidInspector() {
    if (!mermaidZoomModal) return;
    mermaidZoomModal.classList.add('hidden');
  }

  if (mermaidCloseModalBtn) mermaidCloseModalBtn.addEventListener('click', closeMermaidInspector);

  if (mermaidZoomInBtn) {
    mermaidZoomInBtn.addEventListener('click', () => {
      ptz.scale = Math.min(5.0, Math.round((ptz.scale + 0.25) * 100) / 100);
      updateMermaidTransform();
    });
  }

  if (mermaidZoomOutBtn) {
    mermaidZoomOutBtn.addEventListener('click', () => {
      ptz.scale = Math.max(0.2, Math.round((ptz.scale - 0.25) * 100) / 100);
      updateMermaidTransform();
    });
  }

  if (mermaidZoomResetBtn) mermaidZoomResetBtn.addEventListener('click', resetMermaidPTZ);

  if (mermaidFullscreenBtn) {
    mermaidFullscreenBtn.addEventListener('click', () => {
      if (mermaidModalCard) {
        const isFull = mermaidModalCard.classList.toggle('max-w-none');
        mermaidModalCard.classList.toggle('h-screen', isFull);
        mermaidModalCard.classList.toggle('rounded-none', isFull);
        mermaidModalCard.classList.toggle('h-[85vh]', !isFull);
        mermaidModalCard.classList.toggle('max-w-6xl', !isFull);
        mermaidModalCard.classList.toggle('rounded-2xl', !isFull);
      }
    });
  }

  if (mermaidViewport) {
    mermaidViewport.addEventListener('wheel', (e) => {
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
      ptz.scale = Math.max(0.2, Math.min(5.0, Math.round(ptz.scale * zoomFactor * 100) / 100));
      updateMermaidTransform();
    }, { passive: false });

    mermaidViewport.addEventListener('mousedown', (e) => {
      if (e.button !== 0) return;
      ptz.isDragging = true;
      ptz.startX = e.clientX - ptz.panX;
      ptz.startY = e.clientY - ptz.panY;
      mermaidViewport.classList.add('cursor-grabbing');
    });

    window.addEventListener('mousemove', (e) => {
      if (!ptz.isDragging) return;
      ptz.panX = e.clientX - ptz.startX;
      ptz.panY = e.clientY - ptz.startY;
      updateMermaidTransform();
    });

    window.addEventListener('mouseup', () => {
      if (ptz.isDragging) {
        ptz.isDragging = false;
        if (mermaidViewport) mermaidViewport.classList.remove('cursor-grabbing');
      }
    });

    mermaidZoomModal?.addEventListener('click', (e) => {
      if (e.target === mermaidZoomModal) closeMermaidInspector();
    });

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && mermaidZoomModal && !mermaidZoomModal.classList.contains('hidden')) {
        closeMermaidInspector();
      }
    });
  }

  async function loadSystemDocsNav() {
    if (!docsNavTree) return;
    try {
      const res = await fetch('/api/system-info/topics');
      if (!res.ok) throw new Error('Failed to fetch system info topics');
      const data = await res.json();
      cachedDocsNav = data.categories || [];
      renderDocsNav(cachedDocsNav, docsSearchInput ? docsSearchInput.value : '');
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load system info topics:', err);
      docsNavTree.innerHTML = `<p class="text-xs text-rose-400 p-2">Failed to load system info index.</p>`;
    }
  }

  function renderDocsNav(categories, filterText = '') {
    if (!docsNavTree || !categories) return;
    docsNavTree.innerHTML = '';
    const query = filterText.toLowerCase().trim();

    categories.forEach(cat => {
      const matchingTopics = (cat.topics || []).filter(t => {
        if (!query) return true;
        return (
          t.title.toLowerCase().includes(query) ||
          t.summary.toLowerCase().includes(query) ||
          t.id.toLowerCase().includes(query) ||
          cat.title.toLowerCase().includes(query)
        );
      });

      if (matchingTopics.length === 0 && query) return;

      const isCategoryExpanded = query ? true : !collapsedCategoryTitles.has(cat.title);

      const catContainer = document.createElement('div');
      catContainer.className = 'space-y-1';

      const catHeader = document.createElement('button');
      catHeader.type = 'button';
      catHeader.className = 'w-full flex items-center justify-between text-slate-400 hover:text-white font-bold uppercase tracking-wider text-[10px] px-2 py-1.5 rounded-lg hover:bg-slate-800/60 transition group text-left';
      catHeader.innerHTML = `
        <div class="flex items-center space-x-1.5 min-w-0 truncate">
          <i data-lucide="${isCategoryExpanded ? 'chevron-down' : 'chevron-right'}" class="w-3 h-3 text-slate-500 group-hover:text-slate-300 transition-transform flex-shrink-0"></i>
          <i data-lucide="${cat.icon || 'layers'}" class="w-3.5 h-3.5 text-brand-400 flex-shrink-0"></i>
          <span class="truncate">${escapeHtml(cat.title)}</span>
        </div>
        <span class="text-slate-600 font-mono text-[10px]">(${matchingTopics.length})</span>
      `;

      catHeader.addEventListener('click', () => {
        if (collapsedCategoryTitles.has(cat.title)) {
          collapsedCategoryTitles.delete(cat.title);
        } else {
          collapsedCategoryTitles.add(cat.title);
        }
        renderDocsNav(categories, filterText);
      });

      catContainer.appendChild(catHeader);

      const catBody = document.createElement('div');
      catBody.className = `space-y-1 pl-2 border-l border-slate-800/80 ml-2.5 ${isCategoryExpanded ? '' : 'hidden'}`;

      matchingTopics.forEach(topic => {
        const isActive = topic.id === activeDocPathStr;
        const topicBtn = document.createElement('button');
        topicBtn.type = 'button';
        topicBtn.dataset.topicId = topic.id;
        topicBtn.className = `doc-nav-item w-full text-left px-2.5 py-2 rounded-lg text-xs transition block flex flex-col space-y-0.5 ${isActive ? 'bg-brand-600/30 text-brand-200 font-semibold border border-brand-500/40 shadow-sm' : 'text-slate-300 hover:text-white hover:bg-slate-800/70 border border-transparent'}`;
        topicBtn.innerHTML = `
          <div class="flex items-center space-x-1.5 min-w-0 truncate">
            <i data-lucide="${topic.icon || 'file-text'}" class="w-3.5 h-3.5 text-amber-400 flex-shrink-0"></i>
            <span class="truncate font-medium">${escapeHtml(topic.title)}</span>
          </div>
          <p class="text-[10px] text-slate-400 line-clamp-1 pl-5 font-normal">${escapeHtml(topic.summary)}</p>
        `;
        topicBtn.addEventListener('click', () => loadSystemInfoTopic(topic.id));
        catBody.appendChild(topicBtn);
      });

      catContainer.appendChild(catBody);
      docsNavTree.appendChild(catContainer);
    });

    safeCreateIcons();

    const firstTopicId = categories.length > 0 && categories[0].topics && categories[0].topics.length > 0 
      ? categories[0].topics[0].id 
      : 'platform-overview';
    const targetTopicId = activeDocPathStr || firstTopicId;
    if (targetTopicId && (!docViewerContent || docViewerContent.innerHTML.includes('Loading') || docViewerContent.innerHTML.includes('Select a') || !activeDocPathStr)) {
      loadSystemInfoTopic(targetTopicId);
    }
  }

  async function loadSystemInfoTopic(topicId) {
    if (!docViewerContent) return;
    activeDocPathStr = topicId;

    const docsDrawerPane = $('docsDrawerPane');
    const docsDrawerBackdrop = $('docsDrawerBackdrop');
    if (window.innerWidth < 768) {
      if (docsDrawerPane) docsDrawerPane.classList.add('-translate-x-full');
      if (docsDrawerBackdrop) docsDrawerBackdrop.classList.add('hidden');
    }

    $queryAll('.doc-nav-item').forEach(btn => {
      if (btn.dataset.topicId === topicId) {
        btn.className = 'doc-nav-item w-full text-left px-2.5 py-2 rounded-lg text-xs transition block flex flex-col space-y-0.5 bg-brand-600/30 text-brand-200 font-semibold border border-brand-500/40 shadow-sm';
      } else {
        btn.className = 'doc-nav-item w-full text-left px-2.5 py-2 rounded-lg text-xs transition block flex flex-col space-y-0.5 text-slate-300 hover:text-white hover:bg-slate-800/70 border border-transparent';
      }
    });


    if (activeDocPath) activeDocPath.textContent = `#${topicId}`;
    if (activeDocTitle) activeDocTitle.textContent = topicId.replace(/-/g, ' ').toUpperCase();

    docViewerContent.innerHTML = `
      <div class="p-8 text-center text-slate-400">
        <i data-lucide="loader-2" class="w-8 h-8 mx-auto mb-2 text-brand-400 animate-spin"></i>
        <p class="text-xs">Loading system manual topic...</p>
      </div>
    `;
    safeCreateIcons();

    try {
      const res = await fetch(`/api/system-info/topic/${encodeURIComponent(topicId)}`);
      if (!res.ok) throw new Error('Failed to load topic content');
      const data = await res.json();

      if (activeDocTitle) activeDocTitle.textContent = data.title || topicId;

      if (callbacks.renderMarkdown) {
        await callbacks.renderMarkdown(docViewerContent, data.content);
      } else if (window.marked) {
        docViewerContent.innerHTML = window.marked.parse(data.content || '');
      } else {
        docViewerContent.innerHTML = `<pre class="whitespace-pre-wrap font-mono text-xs text-slate-200">${escapeHtml(data.content)}</pre>`;
      }

      safeCreateIcons();
    } catch (err) {
      console.error('[AutoReiv UI] Failed to fetch topic content:', err);
      docViewerContent.innerHTML = `
        <div class="p-6 rounded-xl bg-rose-950/40 border border-rose-900 text-rose-300 text-xs">
          <p class="font-bold mb-1">Failed to load topic</p>
          <p class="font-mono">${escapeHtml(err.message)}</p>
        </div>
      `;
    }
  }

  if (docsSearchInput) {
    docsSearchInput.addEventListener('input', () => {
      if (cachedDocsNav) {
        renderDocsNav(cachedDocsNav, docsSearchInput.value);
      }
    });
  }

  if (refreshDocsNavBtn) {
    refreshDocsNavBtn.addEventListener('click', () => {
      loadSystemDocsNav();
    });
  }

  if (copyDocPathBtn) {
    copyDocPathBtn.addEventListener('click', async () => {
      if (activeDocPathStr) {
        await copyToClipboard(window.location.origin + '/#topic=' + activeDocPathStr);
        const span = copyDocPathBtn.querySelector('span');
        if (span) span.textContent = 'Copied!';
        setTimeout(() => {
          if (span) span.textContent = 'Copy Link';
        }, 2000);
      }
    });
  }

  return {
    loadSystemDocsNav,
    loadSystemInfoTopic,
    openMermaidInspector,
    closeMermaidInspector,
  };
}
