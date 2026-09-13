/**
 * Projects Studio — list, create, select, delete, directory tree & artifact viewer [REQ-SDLC-050..052, REQ-PROJ-010..014].
 */

import { $ } from '../dom.js';
import { fetchJSON } from '../services/api.js';

/** @param {string} rel */
export function normalizeBrowseRel(rel) {
  const raw = String(rel || '.').replace(/\\/g, '/').trim();
  if (!raw || raw === '.' || raw === './') return '.';
  return raw.replace(/^\.\//, '').replace(/\/+$/, '') || '.';
}

/** @param {string} rel */
export function parentBrowseRel(rel) {
  const n = normalizeBrowseRel(rel);
  if (n === '.') return null;
  const parts = n.split('/').filter(Boolean);
  if (parts.length <= 1) return '.';
  return parts.slice(0, -1).join('/');
}

/** @param {Array<{ name?: string, is_dir?: boolean, type?: string }>} entries */
export function filterFoldersOnly(entries) {
  return (entries || []).filter((e) => {
    if (!e) return false;
    if (e.is_dir === false) return false;
    return e.is_dir === true || e.type === 'dir' || !!e.rel || !!e.path;
  });
}


export function initProjectsStudio(state, callbacks = {}) {
  const toast = callbacks.showToast || (() => {});

  let currentCategory = 'all';
  let currentPath = '.';
  let selectedFilePath = null;
  let cachedEntries = [];
  let filterQuery = '';
  let activeProject = null;
  let browseCwd = '.';

  function escapeHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function rPlaceholder() {
    return 'D:\\Projects\\Active';
  }

  function refreshIcons() {
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  }

  async function loadProjects() {
    try {
      const rootRes = await fetchJSON('/api/settings/projects_root');
      const rootInput = $('projectsRootInput');
      if (rootInput) {
        rootInput.value = rootRes.projects_root || '';
        rootInput.placeholder = rootRes.placeholder || rPlaceholder();
      }

      await loadFolderBrowser('.');

      const data = await fetchJSON('/api/projects');
      if (data.selected && data.selected.slug) {
        const projects = data.projects || [];
        activeProject = projects.find((p) => p.slug === data.selected.slug) || data.selected;
        updateActiveHeader(activeProject);
        await loadTree(currentPath, currentCategory);
      } else {
        activeProject = null;
        updateActiveHeader(null);
        clearWorkspace();
      }
    } catch (err) {
      toast(String(err.message || err), 'error');
    }
  }

  function updateActiveHeader(project) {
    const activeName = $('projectsActiveName');
    const activeBadge = $('projectsActiveBadge');
    if (activeName) {
      activeName.textContent = project ? (project.name || project.slug) : 'None';
      activeName.title = project ? (project.path || project.slug) : 'No project selected';
    }
    if (activeBadge) {
      if (project) {
        activeBadge.classList.remove('hidden');
      } else {
        activeBadge.classList.add('hidden');
      }
    }
  }


  function renderList(data) {
    // Legacy flat list kept for callers that still pass {projects}; CARD-300 prefers browseFolders.
    const list = $('projectsList');
    const meta = $('projectsMeta');
    const countBadge = $('projectsCountBadge');

    if (meta) {
      meta.textContent = data.projects_root
        ? `Root: ${data.projects_root}`
        : 'Set projects_root to browse folders.';
    }

    const projects = data.projects || [];
    if (countBadge && !data.folders) {
      countBadge.textContent = String(projects.length);
    }

    if (!list) return;

    if (!projects.length) {
      list.innerHTML =
        '<p class="text-xs text-slate-500 italic p-3 text-center">No folders here. Use Up/Root or create a project slug above.</p>';
      return;
    }

    const selectedPath = (data.selected && data.selected.path) || '';
    list.innerHTML = '';
    projects.forEach((p) => {
      const row = document.createElement('div');
      const isSel = (selectedPath && p.path === selectedPath) || (activeProject && p.slug === activeProject.slug);
      row.className =
        'flex items-center justify-between gap-2 px-3 py-2 rounded-lg border transition ' +
        (isSel ? 'border-brand-500 bg-brand-950/40 shadow-sm' : 'border-slate-800 bg-slate-900/40 hover:bg-slate-900/70');
      row.innerHTML = `
        <div class="min-w-0">
          <div class="text-xs font-semibold text-slate-100 truncate">${escapeHtml(p.name || p.slug)}</div>
          <div class="text-[10px] font-mono text-slate-500 truncate">${escapeHtml(p.path || '')}</div>
        </div>
        <div class="flex items-center gap-1.5 flex-shrink-0">
          <button type="button" data-act="enter" data-rel="${escapeHtml(p.rel || p.slug)}" class="px-2 py-1 text-[11px] font-semibold rounded-md bg-[#141721] border border-white/[0.08] text-slate-200">Open</button>
          <button type="button" data-act="set-active" data-slug="${escapeHtml(p.slug)}" data-path="${escapeHtml(p.path || '')}" class="px-2.5 py-1 text-[11px] font-semibold rounded-md ${isSel ? 'bg-emerald-700/80 text-white' : 'bg-brand-600 text-white'}">${isSel ? 'Active' : 'Set Active'}</button>
        </div>`;
      list.appendChild(row);
    });
    refreshIcons();
  }

  function renderFolderBrowser(data) {
    const list = $('projectsList');
    const meta = $('projectsMeta');
    const countBadge = $('projectsCountBadge');
    const cwdEl = $('projectsBrowseCwd');
    const upBtn = $('projectsBrowseUpBtn');

    browseCwd = normalizeBrowseRel(data.cwd || '.');
    if (cwdEl) cwdEl.textContent = browseCwd === '.' ? (data.projects_root || '.') : browseCwd;
    if (upBtn) upBtn.disabled = !data.parent && browseCwd === '.';

    if (meta) {
      meta.textContent = data.projects_root
        ? `Root: ${data.projects_root} · browsing ${browseCwd}`
        : 'Set projects_root to browse folders.';
    }

    const folders = filterFoldersOnly(data.folders || []);
    if (countBadge) countBadge.textContent = String(folders.length);
    if (!list) return;

    if (!folders.length) {
      list.innerHTML =
        '<p class="text-xs text-slate-500 italic p-3 text-center">No folders here. Up/Root to navigate, or Create a project slug.</p>';
      return;
    }

    const selectedPath = (data.selected && data.selected.path) || '';
    list.innerHTML = '';
    folders.forEach((f) => {
      const isSel = selectedPath && f.path === selectedPath;
      const row = document.createElement('div');
      row.className =
        'flex items-center justify-between gap-2 px-3 py-2 rounded-lg border transition ' +
        (isSel ? 'border-brand-500 bg-brand-950/40 shadow-sm' : 'border-slate-800 bg-slate-900/40 hover:bg-slate-900/70');
      row.innerHTML = `
        <button type="button" data-act="enter" data-rel="${escapeHtml(f.rel)}" class="min-w-0 flex-1 text-left flex items-center gap-2">
          <i data-lucide="folder" class="w-3.5 h-3.5 text-amber-400 flex-shrink-0"></i>
          <span class="text-xs font-semibold text-slate-100 truncate">${escapeHtml(f.name)}</span>
        </button>
        <button type="button" data-act="set-active" data-slug="${escapeHtml(f.name)}" data-path="${escapeHtml(f.path || '')}" class="px-2.5 py-1 text-[11px] font-semibold rounded-md ${isSel ? 'bg-emerald-700/80 text-white cursor-default' : 'bg-brand-600 hover:bg-brand-500 text-white'}" ${isSel ? 'disabled' : ''}>${isSel ? 'Active' : 'Set Active'}</button>`;
      list.appendChild(row);
    });
    refreshIcons();
  }

  async function loadFolderBrowser(rel = browseCwd) {
    try {
      const q = encodeURIComponent(normalizeBrowseRel(rel));
      const data = await fetchJSON(`/api/projects/browse?path=${q}`);
      if (!data.success && data.error) {
        toast(String(data.error), 'error');
      }
      renderFolderBrowser(data);
      if (data.selected && data.selected.slug) {
        activeProject = data.selected;
        updateActiveHeader(activeProject);
      }
    } catch (err) {
      toast(String(err.message || err), 'error');
    }
  }


  async function loadTree(path = '.', category = currentCategory) {
    if (!activeProject) {
      clearWorkspace();
      return;
    }
    const treeList = $('projectsTreeList');
    if (!treeList) return;

    try {
      treeList.innerHTML = '<div class="p-3 text-xs text-slate-400 italic">Scanning files...</div>';
      const query = category && category !== 'all'
        ? `?category=${encodeURIComponent(category)}`
        : `?path=${encodeURIComponent(path || '.')}`;
      const data = await fetchJSON(`/api/projects/files/list${query}`);
      currentPath = data.path || '.';
      cachedEntries = data.entries || [];
      renderTreeEntries();
    } catch (err) {
      treeList.innerHTML = `<div class="p-3 text-xs text-rose-400">Failed to load files: ${escapeHtml(err.message || err)}</div>`;
    }
  }

  function renderTreeEntries() {
    const treeList = $('projectsTreeList');
    if (!treeList) return;

    treeList.innerHTML = '';

    // Parent navigation row if inside a subfolder and not in a specific category filter
    if (currentPath && currentPath !== '.' && (!currentCategory || currentCategory === 'all')) {
      const parentRow = document.createElement('div');
      parentRow.className = 'flex items-center space-x-2 px-2 py-1.5 rounded text-slate-400 hover:text-white hover:bg-slate-900 cursor-pointer transition';
      parentRow.innerHTML = `
        <i data-lucide="corner-left-up" class="w-3.5 h-3.5 text-slate-500"></i>
        <span class="text-xs">.. [Parent Folder]</span>
      `;
      parentRow.addEventListener('click', () => {
        const segments = currentPath.split('/');
        segments.pop();
        const parent = segments.join('/') || '.';
        loadTree(parent, 'all');
      });
      treeList.appendChild(parentRow);
    }

    const q = (filterQuery || '').trim().toLowerCase();
    const filtered = cachedEntries.filter((e) => {
      if (!q) return true;
      return e.name.toLowerCase().includes(q) || e.path.toLowerCase().includes(q);
    });

    if (!filtered.length) {
      const msg = q
        ? `No files match "${escapeHtml(q)}"`
        : `No files found in this folder.`;
      treeList.innerHTML += `<div class="p-3 text-xs text-slate-500 italic text-center">${msg}</div>`;
      refreshIcons();
      return;
    }

    filtered.forEach((entry) => {
      const row = document.createElement('div');
      const isFile = entry.type === 'file';
      const isSelected = selectedFilePath && entry.path === selectedFilePath;

      row.className =
        'flex items-center space-x-2 px-2 py-1.5 rounded cursor-pointer transition select-none ' +
        (isSelected
          ? 'bg-brand-950/80 text-brand-200 font-medium border border-brand-700/50'
          : 'text-slate-300 hover:text-white hover:bg-slate-900/70');

      let iconName = 'file';
      let iconColor = 'text-slate-400';

      if (!isFile) {
        iconName = 'folder';
        iconColor = 'text-amber-400';
      } else {
        const ext = (entry.ext || '').toLowerCase();
        if (ext === '.md') {
          iconName = 'file-text';
          iconColor = 'text-brand-400';
        } else if (['.py', '.ps1', '.sh', '.js', '.ts'].includes(ext)) {
          iconName = 'code';
          iconColor = 'text-indigo-400';
        } else if (['.json', '.yaml', '.yml', '.toml'].includes(ext)) {
          iconName = 'file-code';
          iconColor = 'text-amber-300';
        }
      }

      row.innerHTML = `
        <i data-lucide="${iconName}" class="w-3.5 h-3.5 ${iconColor} flex-shrink-0"></i>
        <span class="truncate text-xs">${escapeHtml(entry.name)}</span>
      `;

      row.addEventListener('click', async () => {
        if (!isFile) {
          await loadTree(entry.path, 'all');
        } else {
          await loadFileContent(entry.path);
        }
      });

      treeList.appendChild(row);
    });

    refreshIcons();
  }

  function closeReadingPane() {
    const viewerPane = $('projectsViewerPane');
    if (viewerPane) {
      if (window.innerWidth < 768) {
        viewerPane.classList.add('hidden');
        viewerPane.classList.remove('flex');
      } else {
        const emptyEl = $('projectsEmptyNotice');
        const mdEl = $('projectsMarkdownContent');
        const codeEl = $('projectsCodeContent');
        const pathEl = $('projectsViewerPath');
        const metaEl = $('projectsViewerMeta');
        const copyBtn = $('projectsCopyPathBtn');
        if (emptyEl) emptyEl.classList.remove('hidden');
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
    }
    selectedFilePath = null;
    renderTreeEntries();
  }

  async function loadFileContent(filePath) {
    if (!filePath) return;
    selectedFilePath = filePath;
    renderTreeEntries(); // Update selected highlight

    // On mobile, pop open the reading pane overlay over the tree
    const viewerPane = $('projectsViewerPane');
    if (viewerPane && window.innerWidth < 768) {
      viewerPane.classList.remove('hidden');
      viewerPane.classList.add('flex');
    }

    const pathEl = $('projectsViewerPath');
    const metaEl = $('projectsViewerMeta');
    const copyBtn = $('projectsCopyPathBtn');
    const mdEl = $('projectsMarkdownContent');
    const codeEl = $('projectsCodeContent');
    const emptyEl = $('projectsEmptyNotice');

    if (pathEl) pathEl.textContent = filePath;
    if (copyBtn) copyBtn.classList.remove('hidden');

    try {
      if (metaEl) metaEl.textContent = 'Loading...';
      const data = await fetchJSON(`/api/projects/files/read?path=${encodeURIComponent(filePath)}`);

      if (metaEl) {
        const chars = data.chars || 0;
        metaEl.textContent = `${chars.toLocaleString()} chars${data.truncated ? ' (truncated)' : ''}`;
      }

      if (emptyEl) emptyEl.classList.add('hidden');

      if (data.is_markdown) {
        if (codeEl) codeEl.classList.add('hidden');
        if (mdEl) {
          mdEl.classList.remove('hidden');
          const content = data.content || '';
          if (window.marked && typeof window.marked.parse === 'function') {
            mdEl.innerHTML = window.marked.parse(content);
          } else {
            mdEl.innerHTML = `<pre class="whitespace-pre-wrap">${escapeHtml(content)}</pre>`;
          }
        }
      } else {
        if (mdEl) mdEl.classList.add('hidden');
        if (codeEl) {
          codeEl.classList.remove('hidden');
          codeEl.textContent = data.content || '';
        }
      }
    } catch (err) {
      if (metaEl) metaEl.textContent = 'Error';
      if (emptyEl) emptyEl.classList.add('hidden');
      if (mdEl) mdEl.classList.add('hidden');
      if (codeEl) {
        codeEl.classList.remove('hidden');
        codeEl.textContent = `Failed to read file: ${err.message || err}`;
      }
      toast(String(err.message || err), 'error');
    }
  }

  function clearWorkspace() {
    const treeList = $('projectsTreeList');
    const emptyNotice = $('projectsEmptyNotice');
    const mdEl = $('projectsMarkdownContent');
    const codeEl = $('projectsCodeContent');
    const pathEl = $('projectsViewerPath');
    const metaEl = $('projectsViewerMeta');
    const copyBtn = $('projectsCopyPathBtn');

    if (treeList) {
      treeList.innerHTML = '<div class="p-4 text-xs text-slate-500 italic text-center">No active project selected.<br>Set a project active to explore files.</div>';
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
    const viewerPane = $('projectsViewerPane');
    if (viewerPane && window.innerWidth < 768) {
      viewerPane.classList.add('hidden');
      viewerPane.classList.remove('flex');
    }
    if (pathEl) pathEl.textContent = 'Select an artifact to inspect';
    if (metaEl) metaEl.textContent = '';
    if (copyBtn) copyBtn.classList.add('hidden');
    selectedFilePath = null;
  }

  // --- EVENT LISTENERS ---

  // Save root
  const saveRootBtn = $('projectsRootSaveBtn');
  if (saveRootBtn) {
    saveRootBtn.addEventListener('click', async () => {
      const input = $('projectsRootInput');
      try {
        await fetchJSON('/api/settings/projects_root', {
          method: 'PUT',
          body: JSON.stringify({ path: (input && input.value) || '' }),
        });
        toast('projects_root saved', 'success');
        await loadProjects();
      } catch (err) {
        toast(String(err.message || err), 'error');
      }
    });
  }

  // Create project
  const createBtn = $('projectsCreateBtn');
  if (createBtn) {
    createBtn.addEventListener('click', async () => {
      const input = $('projectsSlugInput');
      const slug = (input && input.value || '').trim();
      if (!slug) {
        toast('Slug is required', 'error');
        return;
      }
      try {
        await fetchJSON('/api/projects', {
          method: 'POST',
          body: JSON.stringify({ slug }),
        });
        if (input) input.value = '';
        toast(`Created project ${slug}`, 'success');
        await loadProjects();
      } catch (err) {
        toast(String(err.message || err), 'error');
      }
    });
  }

  // Project folder browser actions [CARD-300]
  const list = $('projectsList');
  if (list && !list.dataset.card300Bound) {
    list.dataset.card300Bound = '1';
    list.addEventListener('click', async (event) => {
      const btn = event.target.closest('button[data-act]');
      if (!btn) return;
      const slug = btn.dataset.slug || btn.getAttribute('data-slug');
      const act = btn.dataset.act || btn.getAttribute('data-act');
      const pathAttr = btn.dataset.path || btn.getAttribute('data-path') || '';
      const rel = btn.dataset.rel || btn.getAttribute('data-rel') || '.';
      try {
        if (act === 'enter') {
          await loadFolderBrowser(rel);
          return;
        }
        if (act === 'set-active' || act === 'open') {
          const res = await fetchJSON('/api/projects/selected', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(pathAttr ? { slug, path: pathAttr } : { slug }),
          });
          activeProject = (res && res.selected) || { slug, path: pathAttr };
          updateActiveHeader(activeProject);
          toast(`Active project set: ${activeProject.slug || slug}`, 'success');
          const drawer = $('projectsDrawer');
          if (drawer) drawer.classList.add('hidden');
          await loadTree('.', currentCategory);
          await loadFolderBrowser(browseCwd);
        } else if (act === 'delete') {
          const ok = window.confirm(`Delete project "${slug}"? This cannot be undone.`);
          if (!ok) return;
          await fetchJSON(`/api/projects/${encodeURIComponent(slug)}?confirm=true`, {
            method: 'DELETE',
          });
          toast(`Deleted ${slug}`, 'success');
          await loadProjects();
        }
      } catch (err) {
        toast(String(err.message || err), 'error');
      }
    });
  }

  const browseUpBtn = $('projectsBrowseUpBtn');
  if (browseUpBtn && !browseUpBtn.dataset.card300Bound) {
    browseUpBtn.dataset.card300Bound = '1';
    browseUpBtn.addEventListener('click', async () => {
      const parent = parentBrowseRel(browseCwd);
      await loadFolderBrowser(parent == null ? '.' : parent);
    });
  }
  const browseRootBtn = $('projectsBrowseRootBtn');
  if (browseRootBtn && !browseRootBtn.dataset.card300Bound) {
    browseRootBtn.dataset.card300Bound = '1';
    browseRootBtn.addEventListener('click', async () => {
      await loadFolderBrowser('.');
    });
  }


  // Toggle Projects Drawer
  const toggleDrawerBtn = $('projectsToggleDrawerBtn');
  if (toggleDrawerBtn) {
    toggleDrawerBtn.addEventListener('click', () => {
      const drawer = $('projectsDrawer');
      if (drawer) {
        drawer.classList.toggle('hidden');
      }
    });
  }

  // Refresh Button
  const refreshBtn = $('projectsRefreshBtn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', async () => {
      try {
        await loadProjects();
        if (selectedFilePath) {
          await loadFileContent(selectedFilePath);
        }
        toast('Refreshed project workspace', 'success');
      } catch (err) {
        toast(String(err.message || err), 'error');
      }
    });
  }

  // Category Filter Pills
  const categoryPills = $('projectsCategoryPills');
  if (categoryPills) {
    categoryPills.addEventListener('click', async (event) => {
      const btn = event.target.closest('button[data-cat]');
      if (!btn) return;
      const cat = btn.dataset.cat;
      currentCategory = cat;

      categoryPills.querySelectorAll('button[data-cat]').forEach((b) => {
        if (b === btn) {
          b.className = 'proj-cat-pill active px-2.5 py-1 rounded-lg bg-brand-600 text-white font-semibold transition';
        } else {
          b.className = 'proj-cat-pill px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium transition';
        }
      });

      await loadTree('.', currentCategory);
    });
  }

  // Tree Search Filter
  const treeFilterInput = $('projectsTreeFilter');
  if (treeFilterInput) {
    treeFilterInput.addEventListener('input', (e) => {
      filterQuery = e.target.value || '';
      renderTreeEntries();
    });
  }

  // Copy Path Button
  const copyPathBtn = $('projectsCopyPathBtn');
  if (copyPathBtn) {
    copyPathBtn.addEventListener('click', async () => {
      if (!selectedFilePath) return;
      try {
        await navigator.clipboard.writeText(selectedFilePath);
        const textEl = $('projectsCopyPathText');
        if (textEl) {
          const orig = textEl.textContent;
          textEl.textContent = 'Copied!';
          setTimeout(() => {
            textEl.textContent = orig;
          }, 1500);
        }
      } catch {
        toast(`Copied: ${selectedFilePath}`, 'info');
      }
    });
  }

  // Close Reading Pane Button
  const viewerCloseBtn = $('projectsViewerCloseBtn');
  if (viewerCloseBtn) {
    viewerCloseBtn.addEventListener('click', () => {
      closeReadingPane();
    });
  }

  return {
    loadProjects,
    loadTree,
    loadFileContent,
    closeReadingPane,
  };
}
