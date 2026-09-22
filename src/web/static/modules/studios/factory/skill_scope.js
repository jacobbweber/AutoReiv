/**
 * Factory column-1 assigned skills + column-2 existing-skill picker [CARD-411 UX].
 * Assigned list is agent↔skill scoping only — not a write path into the runbook form.
 */

import { escapeHtml, safeCreateIcons } from '../../dom.js';

export function indexListedSkills(listed = [], assignedIds = []) {
  const assigned = new Set((assignedIds || []).map((id) => String(id || '').trim()).filter(Boolean));
  return (listed || [])
    .filter((row) => row && String(row.id || '').trim())
    .map((row) => {
      const id = String(row.id).trim();
      return {
        id,
        name: String(row.name || id).trim() || id,
        source: assigned.has(id) ? 'assigned' : (row.source || 'workshop'),
      };
    })
    .sort((a, b) => {
      if (a.source === 'assigned' && b.source !== 'assigned') return -1;
      if (b.source === 'assigned' && a.source !== 'assigned') return 1;
      return a.id.localeCompare(b.id);
    });
}
export function mergeEditableSkillOptions({
  assignedIds = [],
  platformSkills = [],
  packOwnedIds = [],
  userPacks = [],
} = {}) {
  const byId = new Map();

  const upsert = (id, name, source) => {
    const sid = String(id || '').trim();
    if (!sid) return;
    const label = String(name || sid).trim() || sid;
    const prev = byId.get(sid);
    if (!prev) {
      byId.set(sid, { id: sid, name: label, source });
      return;
    }
    if (label !== sid && prev.name === prev.id) prev.name = label;
    if (source === 'assigned') prev.source = 'assigned';
  };

  (assignedIds || []).forEach((id) => upsert(id, id, 'assigned'));
  (platformSkills || []).forEach((skill) => {
    if (!skill) return;
    upsert(skill.id || skill.skill_id, skill.name, 'platform');
  });
  (packOwnedIds || []).forEach((id) => upsert(id, id, 'pack'));
  (userPacks || []).forEach((pack) => {
    if (!pack) return;
    upsert(pack.id, pack.name, 'user');
  });

  return Array.from(byId.values()).sort((a, b) => {
    if (a.source === 'assigned' && b.source !== 'assigned') return -1;
    if (b.source === 'assigned' && a.source !== 'assigned') return 1;
    return a.id.localeCompare(b.id);
  });
}

export function createSkillScopeUI({
  getAssignedSkills,
  getAgentId,
  onLoadSkill,
  onNewSkill,
  elements,
}) {
  let editableOptions = [];
  let filterText = '';

  function els() {
    return elements();
  }

  function setWorkshopBadge(label) {
    const { factoryWorkshopSkillBadge } = els();
    if (!factoryWorkshopSkillBadge) return;
    factoryWorkshopSkillBadge.textContent = label || 'New skill';
  }

  function renderAssignedSkills() {
    const { factoryCurrentSkillsList, factoryAssignedSkillsCount } = els();
    const assignedSkills = getAssignedSkills() || [];
    if (factoryAssignedSkillsCount) {
      factoryAssignedSkillsCount.textContent = `${assignedSkills.length} Assigned`;
    }
    if (!factoryCurrentSkillsList) return;

    if (!assignedSkills.length) {
      factoryCurrentSkillsList.innerHTML = '<span class="text-[11px] text-slate-500 italic">No skills assigned yet.</span>';
      return;
    }

    factoryCurrentSkillsList.innerHTML = '';
    assignedSkills.forEach((sid) => {
      const pill = document.createElement('span');
      pill.className = 'inline-flex items-center space-x-1.5 px-2 py-1 rounded-lg text-xs font-mono bg-[#13161f] border border-white/[0.08] text-emerald-300';
      pill.dataset.skillId = sid;
      pill.title = 'Pinned to this agent. Edit in Skill Studio.';
      pill.innerHTML = `
        <i data-lucide="check" class="w-3 h-3 text-emerald-400"></i>
        <span>${escapeHtml(sid)}</span>
      `;
      factoryCurrentSkillsList.appendChild(pill);
    });
    safeCreateIcons({ root: factoryCurrentSkillsList });
  }

  function renderExistingSkillPicker(selectedId = null) {
    const { factoryExistingSkillSelect } = els();
    if (!factoryExistingSkillSelect) return;
    const keep = selectedId != null
      ? selectedId
      : (factoryExistingSkillSelect.value || '');
    const q = (filterText || '').toLowerCase().trim();
    let visible = editableOptions.filter((opt) => {
      if (!q) return true;
      return opt.id.toLowerCase().includes(q) || opt.name.toLowerCase().includes(q);
    });
    if (keep && !visible.some((opt) => opt.id === keep)) {
      const kept = editableOptions.find((opt) => opt.id === keep);
      if (kept) visible = [kept, ...visible];
    }

    factoryExistingSkillSelect.innerHTML = '';
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = '— Select a skill to edit —';
    factoryExistingSkillSelect.appendChild(placeholder);

    visible.forEach((opt) => {
      const el = document.createElement('option');
      el.value = opt.id;
      const suffix = opt.source === 'assigned' ? ' (assigned)' : '';
      el.textContent = opt.name === opt.id ? `${opt.id}${suffix}` : `${opt.name} (${opt.id})${suffix}`;
      factoryExistingSkillSelect.appendChild(el);
    });

    if (keep && visible.some((opt) => opt.id === keep)) {
      factoryExistingSkillSelect.value = keep;
    } else {
      factoryExistingSkillSelect.value = '';
    }
  }

  function setEditableOptions(options, selectedId = null) {
    editableOptions = Array.isArray(options) ? options : [];
    renderExistingSkillPicker(selectedId);
  }

  async function refreshEditableSkillOptions(selectedId = null) {
    const assignedIds = getAssignedSkills() || [];
    let listed = [];
    try {
      const res = await fetch('/api/agent_training_factory/skills');
      if (res.ok) {
        const data = await res.json();
        listed = data.skills || [];
      }
    } catch {
      listed = [];
    }
    setEditableOptions(indexListedSkills(listed, assignedIds), selectedId);
  }

  function selectSkillInPicker(skillId) {
    const { factoryExistingSkillSelect } = els();
    if (factoryExistingSkillSelect && skillId) {
      if (![...factoryExistingSkillSelect.options].some((o) => o.value === skillId)) {
        const opt = document.createElement('option');
        opt.value = skillId;
        opt.textContent = skillId;
        factoryExistingSkillSelect.appendChild(opt);
      }
      factoryExistingSkillSelect.value = skillId;
    }
    setWorkshopBadge(skillId ? `Editing: ${skillId}` : 'New skill');
  }

  function clearPickerSelection() {
    const { factoryExistingSkillSelect, factoryExistingSkillFilter } = els();
    if (factoryExistingSkillFilter) factoryExistingSkillFilter.value = '';
    filterText = '';
    renderExistingSkillPicker('');
    if (factoryExistingSkillSelect) factoryExistingSkillSelect.value = '';
    setWorkshopBadge('New skill');
  }

  function bindEvents() {
    const {
      factoryExistingSkillSelect,
      factoryExistingSkillFilter,
      factoryNewSkillFormBtn,
    } = els();

    if (factoryExistingSkillFilter) {
      factoryExistingSkillFilter.addEventListener('input', () => {
        filterText = factoryExistingSkillFilter.value || '';
        renderExistingSkillPicker(factoryExistingSkillSelect ? factoryExistingSkillSelect.value : '');
      });
    }

    if (factoryExistingSkillSelect) {
      factoryExistingSkillSelect.addEventListener('change', () => {
        const skillId = factoryExistingSkillSelect.value || '';
        if (!skillId) {
          setWorkshopBadge('New skill');
          return;
        }
        setWorkshopBadge(`Editing: ${skillId}`);
        if (typeof onLoadSkill === 'function') {
          onLoadSkill(skillId, getAgentId());
        }
      });
    }

    if (factoryNewSkillFormBtn) {
      factoryNewSkillFormBtn.addEventListener('click', () => {
        clearPickerSelection();
        if (typeof onNewSkill === 'function') onNewSkill();
      });
    }
  }

  return {
    bindEvents,
    renderAssignedSkills,
    refreshEditableSkillOptions,
    selectSkillInPicker,
    clearPickerSelection,
    setWorkshopBadge,
    setEditableOptions,
    mergeEditableSkillOptions,
  };
}
