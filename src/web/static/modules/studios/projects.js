/**
 * Projects Studio — list, create, select, delete, directory tree & artifact viewer [REQ-SDLC-050..052, REQ-PROJ-010..014].
 */

import { $ } from '../dom.js';
import { fetchJSON } from '../services/api.js';

export function initProjectsStudio(state, callbacks = {}) {
  const toast = callbacks.showToast || (() => {});

  let currentCategory = 'all';
  let currentPath = '.';
  let selectedFilePath = null;
  let cachedEntries = [];
  let filterQuery = '';
  let activeProject = null;

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

      const data = await fetchJSON('/api/projects');
      renderList(data);

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
    const list = $('projectsList');
    const meta = $('projectsMeta');
    const countBadge = $('projectsCountBadge');

    if (meta) {
      meta.textContent = data.projects_root
        ? `Root: ${data.projects_root}`
        : 'Set projects_root to list folders.';
    }

    const projects = data.projects || [];
    if (countBadge) {
      countBadge.textContent = String(projects.length);
    }

    if (!list) return;

    const selectedPath = (data.selected && data.selected.path) || '';
    if (!projects.length) {
      list.innerHTML =
        '<p class="text-xs text-slate-500 italic p-3 text-center">No projects found. Create a project slug above.</p>';
      return;
    }

    list.innerHTML = '';
    projects.forEach((p) => {
      const row = document.createElement('div');
      const isSel = (selectedPath && p.path === selectedPath) || (activeProject && p.slug === activeProject.slug);
      row.className =
        'flex items-center justify-between gap-2 px-3 py-2 rounded-lg border transition ' +
        (isSel ? 'border-brand-500 bg-brand-950/40 shadow-sm' : 'border-slate-800 bg-slate-900/40 hover:bg-slate-900/70');

      const badgeHtml = isSel
        ? `<span class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-950 text-emerald-400 border border-emerald-700/60 flex items-center space-x-1">
             <i data-lucide="check" class="w-3 h-3"></i>
             <span>Active Project</span>
           </span>`
        : '';

      const actionBtnHtml = isSel
        ? `<button data-act="set-active" data-slug="${escapeHtml(p.slug)}" class="px-2.5 py-1 text-[11px] font-semibold rounded-md bg-emerald-700/80 text-white cursor-default" disabled>Active</button>`
        : `<button data-act="set-active" data-slug="${escapeHtml(p.slug)}" class="px-2.5 py-1 text-[11px] font-semibold rounded-md bg-brand-600 hover:bg-brand-500 text-white transition shadow-sm">Set as Active</button>`;

      row.innerHTML = `
        <div class="min-w-0 flex items-center space-x-2">
          <i data-lucide="folder" class="w-4 h-4 ${isSel ? 'text-brand-400' : 'text-slate-400'} flex-shrink-0"></i>
          <div class="min-w-0">
            <div class="flex items-center space-x-2">
              <p class="text-xs font-semibold text-white truncate">${escapeHtml(p.name || p.slug)}</p>
              ${badgeHtml}
            </div>
            <p class="text-[10px] text-slate-500 font-mono truncate">${escapeHtml(p.path)}</p>
          </div>
        </div>
        <div class="flex items-center gap-1.5 flex-shrink-0">
          ${actionBtnHtml}
          <button data-act="delete" data-slug="${escapeHtml(p.slug)}" class="px-2 py-1 text-[11px] rounded-md bg-rose-900/40 hover:bg-rose-900/70 text-rose-300 border border-rose-800/40 transition" title="Delete Project">Delete</button>
        </div>`;
      list.appendChild(row);
    });

    refreshIcons();
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

  async function loadFileContent(filePath) {
    if (!filePath) return;
    selectedFilePath = filePath;
    renderTreeEntries(); // Update selected highlight

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

  // Project List Actions (Set as Active / Delete)
  const list = $('projectsList');
  if (list) {
    list.addEventListener('click', async (event) => {
      const btn = event.target.closest('button[data-act]');
      if (!btn) return;
      const slug = btn.dataset.slug;
      const act = btn.dataset.act;
      try {
        if (act === 'set-active' || act === 'open') {
          await fetchJSON('/api/projects/selected', {
            method: 'PUT',
            body: JSON.stringify({ slug }),
          });
          toast(`Active project set: ${slug}`, 'success');
          // Auto-collapse drawer when project is set active
          const drawer = $('projectsDrawer');
          if (drawer) drawer.classList.add('hidden');
          await loadProjects();
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

  return {
    loadProjects,
    loadTree,
    loadFileContent,
  };
}
