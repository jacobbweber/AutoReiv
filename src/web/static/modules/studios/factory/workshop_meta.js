/**
 * Factory workshop structured frontmatter controls [CARD-411].
 * Tool picker state is the single lever for requires_tools.
 */

import { applyWorkshopMetadata } from '../../utils/skill_frontmatter.js';

/**
 * Map a workshop GET payload onto Skill Studio fields [CARD-418 / CARD-411].
 * A catalog-resolvable skill has no "not found" detail.
 * @param {object} data
 * @param {string} skillId
 */
export function applyLoadedSkillView(data = {}, skillId = '') {
  const payload = data && typeof data === 'object' ? data : {};
  const detail = typeof payload.detail === 'string' ? payload.detail : '';
  const description = String(payload.description || '').slice(0, 60);
  const requiresTools = Array.isArray(payload.requires_tools)
    ? payload.requires_tools.map((item) => String(item || '').trim()).filter(Boolean)
    : [];
  return {
    ok: !detail,
    notFound: /not found/i.test(detail),
    detail,
    name: String(payload.name || skillId || ''),
    skillId: String(payload.skill_id || skillId || ''),
    description,
    tier: String(payload.tier || 'pack'),
    safety: {
      read_only: Boolean(payload.safety && payload.safety.read_only),
      requires_hitl: Boolean(payload.safety && payload.safety.requires_hitl),
      untrusted_input_allowed: Boolean(payload.safety && payload.safety.untrusted_input_allowed),
    },
    requiresTools,
    markdown: String(payload.markdown_content || ''),
  };
}

export function createSkillWorkshop({
  showToast,
  getCapabilities,
  getSelectedTools,
  setSelectedTools,
  setIdentityLocked,
  renderCapabilities,
  updateSelectedToolBadge,
  elements,
}) {
  function els() {
    return elements();
  }

  function catalogIds() {
    const ids = [];
    (getCapabilities() || []).forEach((ns) => {
      (ns.tools || []).forEach((tool) => {
        if (tool && tool.name) ids.push(tool.name);
      });
    });
    getSelectedTools().forEach((name) => ids.push(name));
    return ids;
  }

  function readSafety() {
    const {
      factorySkillSafetyReadOnly,
      factorySkillSafetyHitl,
      factorySkillSafetyUntrusted,
    } = els();
    return {
      read_only: Boolean(factorySkillSafetyReadOnly && factorySkillSafetyReadOnly.checked),
      requires_hitl: Boolean(factorySkillSafetyHitl && factorySkillSafetyHitl.checked),
      untrusted_input_allowed: Boolean(factorySkillSafetyUntrusted && factorySkillSafetyUntrusted.checked),
    };
  }

  function workshopFields() {
    const { factorySkillNameInput, factorySkillTriggerInput, factorySkillTierSelect } = els();
    return {
      name: (factorySkillNameInput && factorySkillNameInput.value.trim()) || '',
      description: (factorySkillTriggerInput && factorySkillTriggerInput.value.trim()) || '',
      tier: (factorySkillTierSelect && factorySkillTierSelect.value) || 'pack',
      safety: readSafety(),
      requires_tools: Array.from(getSelectedTools()),
    };
  }

  function renderRequiredToolChips() {
    const { factoryRequiredToolsChips, factoryToolSearchInput } = els();
    if (!factoryRequiredToolsChips) return;
    const ids = Array.from(getSelectedTools());
    if (!ids.length) {
      factoryRequiredToolsChips.innerHTML = '<span class="text-[11px] text-slate-500 italic">No required tools selected.</span>';
      return;
    }
    factoryRequiredToolsChips.innerHTML = '';
    ids.forEach((toolId) => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-mono bg-[#13161f] border border-white/[0.08] text-purple-200';
      chip.dataset.toolId = toolId;
      chip.textContent = `${toolId} ×`;
      chip.addEventListener('click', () => {
        const next = getSelectedTools();
        next.delete(toolId);
        setSelectedTools(next);
        const filter = (factoryToolSearchInput && factoryToolSearchInput.value) || '';
        renderCapabilities(filter);
        syncFrontmatter();
      });
      factoryRequiredToolsChips.appendChild(chip);
    });
  }

  function syncFrontmatter() {
    renderRequiredToolChips();
    updateSelectedToolBadge();
    const { factorySkillMarkdownEditor } = els();
    if (!factorySkillMarkdownEditor) return;
    const fields = workshopFields();
    const current = factorySkillMarkdownEditor.value || '';
    if (!current.trim() && !fields.name && !fields.description && fields.requires_tools.length === 0) return;
    const applied = applyWorkshopMetadata(current, fields, catalogIds());
    factorySkillMarkdownEditor.value = applied.markdown;
  }

  async function loadExistingSkill(skillId, agentId) {
    if (!skillId) return;
    const params = new URLSearchParams();
    if (agentId) params.set('agent_id', agentId);
    const query = params.toString();
    const {
      factorySkillNameInput,
      factorySkillIdInput,
      factorySkillTriggerInput,
      factorySkillTriggerCharCount,
      factorySkillTierSelect,
      factorySkillSafetyReadOnly,
      factorySkillSafetyHitl,
      factorySkillSafetyUntrusted,
      factorySkillMarkdownEditor,
      factoryToolSearchInput,
    } = els();
    try {
      const encoded = String(skillId).split('/').map((part) => encodeURIComponent(part)).join('/');
      const resp = await fetch(`/api/agent_training_factory/skills/${encoded}${query ? `?${query}` : ''}`);
      const data = await resp.json().catch(() => ({}));
      const view = applyLoadedSkillView(data, skillId);
      if (!resp.ok || view.notFound) throw new Error(view.detail || data.detail || `HTTP ${resp.status}`);
      setIdentityLocked(true);
      if (factorySkillNameInput) factorySkillNameInput.value = view.name;
      if (factorySkillIdInput) factorySkillIdInput.value = view.skillId;
      if (factorySkillTriggerInput) {
        factorySkillTriggerInput.value = view.description;
        if (factorySkillTriggerCharCount) factorySkillTriggerCharCount.textContent = `${view.description.length}/60`;
      }
      if (factorySkillTierSelect) factorySkillTierSelect.value = view.tier;
      if (factorySkillSafetyReadOnly) factorySkillSafetyReadOnly.checked = view.safety.read_only;
      if (factorySkillSafetyHitl) factorySkillSafetyHitl.checked = view.safety.requires_hitl;
      if (factorySkillSafetyUntrusted) factorySkillSafetyUntrusted.checked = view.safety.untrusted_input_allowed;
      setSelectedTools(new Set(view.requiresTools));
      if (factorySkillMarkdownEditor) factorySkillMarkdownEditor.value = view.markdown;
      renderCapabilities((factoryToolSearchInput && factoryToolSearchInput.value) || '');
      syncFrontmatter();
      showToast(`Opened ${skillId} in the workshop`, 'success');
    } catch (err) {
      showToast(`Could not open skill: ${err.message || err}`, 'error');
    }
  }

  return {
    workshopFields,
    renderRequiredToolChips,
    syncFrontmatter,
    loadExistingSkill,
  };
}
