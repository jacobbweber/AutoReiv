/**
 * Projects Studio — list, create, select, delete [REQ-SDLC-050..052].
 * Separate from Wiki.
 */

import { $ } from '../dom.js';
import { fetchJSON } from '../services/api.js';

export function initProjectsStudio(state, callbacks = {}) {
  const toast = callbacks.showToast || (() => {});

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
    } catch (err) {
      toast(String(err.message || err), 'error');
    }
  }

  function rPlaceholder() {
    return 'D:\\Projects\\Active';
  }

  function renderList(data) {
    const list = $('projectsList');
    const meta = $('projectsMeta');
    if (meta) {
      meta.textContent = data.projects_root
        ? `Root: ${data.projects_root}`
        : 'Set projects_root to list folders.';
    }
    if (!list) return;
    const selectedPath = (data.selected && data.selected.path) || '';
    const projects = data.projects || [];
    if (!projects.length) {
      list.innerHTML =
        '<p class="text-xs text-slate-500 italic p-3">No projects yet. Create a folder slug under the root.</p>';
      return;
    }
    list.innerHTML = '';
    projects.forEach((p) => {
      const row = document.createElement('div');
      const isSel = selectedPath && p.path === selectedPath;
      row.className =
        'flex items-center justify-between gap-2 px-3 py-2 rounded-lg border ' +
        (isSel ? 'border-brand-500 bg-brand-950/40' : 'border-slate-800 bg-slate-900/40');
      row.innerHTML = `
        <div class="min-w-0">
          <p class="text-sm font-semibold text-white truncate">${escapeHtml(p.name)}</p>
          <p class="text-[11px] text-slate-500 truncate">${escapeHtml(p.path)}</p>
        </div>
        <div class="flex items-center gap-1 flex-shrink-0">
          <button data-act="open" data-slug="${escapeHtml(p.slug)}" class="px-2 py-1 text-[11px] rounded-md bg-brand-600 text-white">Open</button>
          <button data-act="delete" data-slug="${escapeHtml(p.slug)}" class="px-2 py-1 text-[11px] rounded-md bg-rose-900/60 text-rose-200">Delete</button>
        </div>`;
      list.appendChild(row);
    });
  }

  function escapeHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

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
        toast(`Created ${slug}`, 'success');
        await loadProjects();
      } catch (err) {
        toast(String(err.message || err), 'error');
      }
    });
  }

  const list = $('projectsList');
  if (list) {
    list.addEventListener('click', async (event) => {
      const btn = event.target.closest('button[data-act]');
      if (!btn) return;
      const slug = btn.dataset.slug;
      const act = btn.dataset.act;
      try {
        if (act === 'open') {
          await fetchJSON('/api/projects/selected', {
            method: 'PUT',
            body: JSON.stringify({ slug }),
          });
          toast(`Opened ${slug}`, 'success');
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

  return { loadProjects };
}
