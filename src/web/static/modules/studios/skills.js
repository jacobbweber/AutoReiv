/**
 * Skills Studio - list and edit user SKILL.md packs [REQ-DATA-012 - REQ-DATA-018].
 * Sibling of Agent Studio. Disk under $DATA_DIR/skills is the source of truth.
 * Lists USER packs only. Python builtin tools stay out of this catalog.
 */

import { $, safeCreateIcons } from '../dom.js';
import { fetchJSON } from '../services/api.js';
import { escapeHtml } from '../utils/formatters.js';

const BUNDLED_SEED_ID = 'okta-admin';

export function initSkillsStudio(state, callbacks = {}) {
  const toast = callbacks.showToast || (() => {});

  const packList = $('skillsPackList');
  const nameInput = $('skillsNameInput');
  const descInput = $('skillsDescInput');
  const bodyInput = $('skillsBodyTextarea');
  const toolsList = $('skillsToolsList');
  const activeTitle = $('skillsActiveTitle');
  const activePath = $('skillsActivePath');
  const saveBtn = $('skillsSavePackBtn');
  const newBtn = $('skillsNewPackBtn');
  const slugInput = $('skillsNewPackSlug');
  const archiveBtn = $('skillsArchiveBtn');
  const unarchiveBtn = $('skillsUnarchiveBtn');
  const deleteBtn = $('skillsDeleteBtn');
  const drawerBtn = $('skillsMobileDrawerBtn');
  const drawerPane = $('skillsDrawerPane');
  const drawerClose = $('skillsDrawerCloseBtn');
  const drawerBackdrop = $('skillsDrawerBackdrop');

  let activePackId = '';
  let activeArchived = false;
  let packs = [];
  let archivedPacks = [];

  function openDrawer() {
    if (drawerPane) drawerPane.classList.remove('-translate-x-full');
    if (drawerBackdrop) drawerBackdrop.classList.remove('hidden');
  }

  function closeDrawer() {
    if (drawerPane) drawerPane.classList.add('-translate-x-full');
    if (drawerBackdrop) drawerBackdrop.classList.add('hidden');
  }

  if (drawerBtn) drawerBtn.addEventListener('click', openDrawer);
  if (drawerClose) drawerClose.addEventListener('click', closeDrawer);
  if (drawerBackdrop) drawerBackdrop.addEventListener('click', closeDrawer);

  function setActionVisibility() {
    const has = Boolean(activePackId);
    if (archiveBtn) archiveBtn.classList.toggle('hidden', !has || activeArchived);
    if (unarchiveBtn) unarchiveBtn.classList.toggle('hidden', !has || !activeArchived);
    if (deleteBtn) deleteBtn.classList.toggle('hidden', !has);
  }

  function renderSection(title, items, archived) {
    const wrap = document.createElement('div');
    wrap.className = 'space-y-2';
    const heading = document.createElement('p');
    heading.className = 'text-[10px] font-semibold uppercase tracking-wider text-slate-500 px-1';
    heading.textContent = title;
    wrap.appendChild(heading);
    if (!items.length) {
      const empty = document.createElement('p');
      empty.className = 'text-xs text-slate-500 italic px-1';
      empty.textContent = archived ? 'No archived packs.' : 'No live user packs.';
      wrap.appendChild(empty);
      return wrap;
    }
    items.forEach((pack) => {
      const btn = document.createElement('button');
      const selected = pack.id === activePackId && Boolean(archived) === activeArchived;
      btn.type = 'button';
      btn.dataset.packId = pack.id;
      btn.dataset.archived = archived ? '1' : '0';
      btn.className =
        'w-full text-left px-3 py-2 rounded-lg border transition ' +
        (selected
          ? 'border-brand-500 bg-brand-950/40'
          : 'border-slate-800 bg-slate-900/40 hover:border-slate-600');
      const badge = archived
        ? '<span class="text-[10px] uppercase tracking-wider text-amber-400">Archived</span>'
        : '';
      btn.innerHTML = `
        <div class="flex items-center justify-between gap-2">
          <p class="text-sm font-semibold text-white truncate">${escapeHtml(pack.name)}</p>
          ${badge}
        </div>
        <p class="text-[11px] text-slate-500 truncate">${escapeHtml(pack.description)}</p>`;
      wrap.appendChild(btn);
    });
    return wrap;
  }

  function renderPackList() {
    if (!packList) return;
    if (!packs.length && !archivedPacks.length) {
      packList.innerHTML =
        '<p class="text-xs text-slate-500 italic p-3">No user packs yet. Create a slug under the data dir skills tree.</p>';
      return;
    }
    packList.innerHTML = '';
    packList.appendChild(renderSection('Live', packs, false));
    packList.appendChild(renderSection('Archived', archivedPacks, true));
  }

  function renderTools(tools) {
    if (!toolsList) return;
    const list = tools || [];
    if (!list.length) {
      toolsList.innerHTML =
        '<p class="text-xs text-slate-500 italic">None - playbook only.</p>';
      return;
    }
    toolsList.innerHTML = list
      .map((tool) => {
        const desc = tool.description ? ` - ${escapeHtml(tool.description)}` : '';
        return `<li class="text-xs text-slate-200 font-mono"><span class="text-brand-300">${escapeHtml(tool.name)}</span>${desc}</li>`;
      })
      .join('');
  }

  function applyPack(data, archivedHint) {
    const manifest = data.manifest || {};
    activePackId = manifest.id || activePackId;
    activeArchived = Boolean(
      archivedHint || data.archived || manifest.origin === 'archived',
    );
    if (nameInput) nameInput.value = manifest.name || data.name || '';
    if (descInput) descInput.value = manifest.description || data.description || '';
    if (bodyInput) bodyInput.value = data.instructions || '';
    if (activeTitle) activeTitle.textContent = manifest.name || activePackId || 'Select a pack';
    if (activePath) activePath.textContent = manifest.path || '';
    renderTools(data.tools || []);
    renderPackList();
    setActionVisibility();
    safeCreateIcons();
  }

  function clearEditor() {
    activePackId = '';
    activeArchived = false;
    if (nameInput) nameInput.value = '';
    if (descInput) descInput.value = '';
    if (bodyInput) bodyInput.value = '';
    if (activeTitle) activeTitle.textContent = 'Select a pack';
    if (activePath) activePath.textContent = '';
    renderTools([]);
    renderPackList();
    setActionVisibility();
  }

  async function loadSkills() {
    try {
      const data = await fetchJSON('/api/skills/user-packs');
      const archived = await fetchJSON('/api/skills/archived-packs');
      packs = data.packs || [];
      archivedPacks = archived.packs || [];
      renderPackList();
      if (activePackId) {
        const stillLive = packs.find((p) => p.id === activePackId);
        const stillArch = archivedPacks.find((p) => p.id === activePackId);
        if (stillLive || stillArch) {
          await openPack(activePackId, Boolean(stillArch) && !stillLive);
        } else {
          clearEditor();
        }
      } else {
        setActionVisibility();
      }
    } catch (err) {
      toast(String(err.message || err), 'error');
    }
  }

  async function openPack(packId, archived) {
    try {
      const data = await fetchJSON(`/api/skills/user-packs/${encodeURIComponent(packId)}`);
      applyPack(data, archived);
      if (window.innerWidth < 768) closeDrawer();
    } catch (err) {
      toast(String(err.message || err), 'error');
    }
  }

  if (packList) {
    packList.addEventListener('click', (event) => {
      const btn = event.target.closest('button[data-pack-id]');
      if (!btn) return;
      openPack(btn.dataset.packId, btn.dataset.archived === '1');
    });
  }

  if (saveBtn) {
    saveBtn.addEventListener('click', async () => {
      if (!activePackId) {
        toast('Select or create a pack first', 'error');
        return;
      }
      if (activeArchived) {
        toast('Unarchive this pack before saving', 'error');
        return;
      }
      try {
        saveBtn.disabled = true;
        const data = await fetchJSON(`/api/skills/user-packs/${encodeURIComponent(activePackId)}`, {
          method: 'PUT',
          body: JSON.stringify({
            name: nameInput ? nameInput.value : '',
            description: descInput ? descInput.value : '',
            instructions: bodyInput ? bodyInput.value : '',
          }),
        });
        toast('Pack saved', 'success');
        await loadSkills();
        applyPack(data, false);
      } catch (err) {
        toast(String(err.message || err), 'error');
      } finally {
        saveBtn.disabled = false;
      }
    });
  }

  if (newBtn) {
    newBtn.addEventListener('click', async () => {
      const slug = ((slugInput && slugInput.value) || '').trim();
      if (!slug) {
        toast('Pack slug is required', 'error');
        return;
      }
      try {
        const data = await fetchJSON('/api/skills/user-packs', {
          method: 'POST',
          body: JSON.stringify({ id: slug, name: slug, description: 'User skill pack.' }),
        });
        if (slugInput) slugInput.value = '';
        toast(`Created ${slug}`, 'success');
        await loadSkills();
        applyPack(data, false);
      } catch (err) {
        toast(String(err.message || err), 'error');
      }
    });
  }

  if (archiveBtn) {
    archiveBtn.addEventListener('click', async () => {
      if (!activePackId) {
        toast('Select a pack first', 'error');
        return;
      }
      const ok = window.confirm(
        `Archive pack "${activePackId}"? It leaves the live list and can be unarchived later.`,
      );
      if (!ok) return;
      try {
        archiveBtn.disabled = true;
        await fetchJSON(`/api/skills/user-packs/${encodeURIComponent(activePackId)}/archive`, {
          method: 'POST',
          body: JSON.stringify({ confirm: true }),
        });
        toast(`Archived ${activePackId}`, 'success');
        await loadSkills();
      } catch (err) {
        toast(String(err.message || err), 'error');
      } finally {
        archiveBtn.disabled = false;
      }
    });
  }

  if (unarchiveBtn) {
    unarchiveBtn.addEventListener('click', async () => {
      if (!activePackId) {
        toast('Select an archived pack first', 'error');
        return;
      }
      const ok = window.confirm(`Unarchive pack "${activePackId}" and restore it to the live list?`);
      if (!ok) return;
      try {
        unarchiveBtn.disabled = true;
        await fetchJSON(`/api/skills/user-packs/${encodeURIComponent(activePackId)}/unarchive`, {
          method: 'POST',
        });
        toast(`Unarchived ${activePackId}`, 'success');
        await loadSkills();
      } catch (err) {
        toast(String(err.message || err), 'error');
      } finally {
        unarchiveBtn.disabled = false;
      }
    });
  }

  if (deleteBtn) {
    deleteBtn.addEventListener('click', async () => {
      if (!activePackId) {
        toast('Select a pack first', 'error');
        return;
      }
      const ok = window.confirm(
        `Permanently delete pack "${activePackId}"? This removes the directory under skills/ and cannot be undone.`,
      );
      if (!ok) return;
      let confirmSeed = false;
      if (activePackId === BUNDLED_SEED_ID) {
        const seedOk = window.confirm(
          'okta-admin is a bundled seed. Archive instead, or confirm hard-delete of the data-dir copy only. Repo seeds are never deleted. Continue?',
        );
        if (!seedOk) return;
        confirmSeed = true;
      }
      try {
        deleteBtn.disabled = true;
        const params = new URLSearchParams({ confirm: 'true' });
        if (confirmSeed) params.set('confirm_seed', 'true');
        await fetchJSON(
          `/api/skills/user-packs/${encodeURIComponent(activePackId)}?${params.toString()}`,
          { method: 'DELETE', body: JSON.stringify({ confirm: true, confirm_seed: confirmSeed }) },
        );
        toast(`Deleted ${activePackId}`, 'success');
        activePackId = '';
        activeArchived = false;
        await loadSkills();
        clearEditor();
      } catch (err) {
        const message = String(err.message || err);
        if (message.toLowerCase().includes('confirm_seed') || message.toLowerCase().includes('bundled seed')) {
          const seedOk = window.confirm(
            `${message}\n\nHard-delete the data-dir copy of this bundled seed? Repo seeds stay.`,
          );
          if (seedOk) {
            try {
              const params = new URLSearchParams({ confirm: 'true', confirm_seed: 'true' });
              await fetchJSON(
                `/api/skills/user-packs/${encodeURIComponent(activePackId)}?${params.toString()}`,
                { method: 'DELETE', body: JSON.stringify({ confirm: true, confirm_seed: true }) },
              );
              toast(`Deleted ${activePackId}`, 'success');
              activePackId = '';
              activeArchived = false;
              await loadSkills();
              clearEditor();
              return;
            } catch (retryErr) {
              toast(String(retryErr.message || retryErr), 'error');
              return;
            }
          }
        }
        toast(message, 'error');
      } finally {
        deleteBtn.disabled = false;
      }
    });
  }

  setActionVisibility();
  return { loadSkills };
}
