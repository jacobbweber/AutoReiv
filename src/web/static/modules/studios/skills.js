/**
 * Skills Studio - list and edit user SKILL.md packs [REQ-DATA-012 - REQ-DATA-014].
 * Sibling of Agent Studio. Disk under $DATA_DIR/skills is the source of truth.
 */

import { $, safeCreateIcons } from '../dom.js';
import { fetchJSON } from '../services/api.js';
import { escapeHtml } from '../utils/formatters.js';

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
  const drawerBtn = $('skillsMobileDrawerBtn');
  const drawerPane = $('skillsDrawerPane');
  const drawerClose = $('skillsDrawerCloseBtn');
  const drawerBackdrop = $('skillsDrawerBackdrop');

  let activePackId = '';
  let packs = [];

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

  function renderPackList() {
    if (!packList) return;
    if (!packs.length) {
      packList.innerHTML =
        '<p class="text-xs text-slate-500 italic p-3">No user packs yet. Create a slug under the data dir skills tree.</p>';
      return;
    }
    packList.innerHTML = '';
    packs.forEach((pack) => {
      const btn = document.createElement('button');
      const selected = pack.id === activePackId;
      btn.type = 'button';
      btn.dataset.packId = pack.id;
      btn.className =
        'w-full text-left px-3 py-2 rounded-lg border transition ' +
        (selected
          ? 'border-brand-500 bg-brand-950/40'
          : 'border-slate-800 bg-slate-900/40 hover:border-slate-600');
      btn.innerHTML = `
        <p class="text-sm font-semibold text-white truncate">${escapeHtml(pack.name)}</p>
        <p class="text-[11px] text-slate-500 truncate">${escapeHtml(pack.description)}</p>`;
      packList.appendChild(btn);
    });
  }

  function renderTools(tools) {
    if (!toolsList) return;
    const list = tools || [];
    if (!list.length) {
      toolsList.innerHTML =
        '<p class="text-xs text-slate-500 italic">None — playbook only.</p>';
      return;
    }
    toolsList.innerHTML = list
      .map((tool) => {
        const desc = tool.description ? ` — ${escapeHtml(tool.description)}` : '';
        return `<li class="text-xs text-slate-200 font-mono"><span class="text-brand-300">${escapeHtml(tool.name)}</span>${desc}</li>`;
      })
      .join('');
  }

  function applyPack(data) {
    const manifest = data.manifest || {};
    activePackId = manifest.id || activePackId;
    if (nameInput) nameInput.value = manifest.name || data.name || '';
    if (descInput) descInput.value = manifest.description || data.description || '';
    if (bodyInput) bodyInput.value = data.instructions || '';
    if (activeTitle) activeTitle.textContent = manifest.name || activePackId || 'Select a pack';
    if (activePath) activePath.textContent = manifest.path || '';
    renderTools(data.tools || []);
    renderPackList();
    safeCreateIcons();
  }

  function clearEditor() {
    activePackId = '';
    if (nameInput) nameInput.value = '';
    if (descInput) descInput.value = '';
    if (bodyInput) bodyInput.value = '';
    if (activeTitle) activeTitle.textContent = 'Select a pack';
    if (activePath) activePath.textContent = '';
    renderTools([]);
    renderPackList();
  }

  async function loadSkills() {
    try {
      const data = await fetchJSON('/api/skills/user-packs');
      packs = data.packs || [];
      renderPackList();
      if (activePackId) {
        const still = packs.find((p) => p.id === activePackId);
        if (still) {
          await openPack(activePackId);
        } else {
          clearEditor();
        }
      }
    } catch (err) {
      toast(String(err.message || err), 'error');
    }
  }

  async function openPack(packId) {
    try {
      const data = await fetchJSON(`/api/skills/user-packs/${encodeURIComponent(packId)}`);
      applyPack(data);
      if (window.innerWidth < 768) closeDrawer();
    } catch (err) {
      toast(String(err.message || err), 'error');
    }
  }

  if (packList) {
    packList.addEventListener('click', (event) => {
      const btn = event.target.closest('button[data-pack-id]');
      if (!btn) return;
      openPack(btn.dataset.packId);
    });
  }

  if (saveBtn) {
    saveBtn.addEventListener('click', async () => {
      if (!activePackId) {
        toast('Select or create a pack first', 'error');
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
        const listed = await fetchJSON('/api/skills/user-packs');
        packs = listed.packs || [];
        applyPack(data);
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
        const listed = await fetchJSON('/api/skills/user-packs');
        packs = listed.packs || [];
        applyPack(data);
      } catch (err) {
        toast(String(err.message || err), 'error');
      }
    });
  }

  return { loadSkills };
}