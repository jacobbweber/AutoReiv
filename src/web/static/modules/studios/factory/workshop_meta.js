/**
 * Factory workshop structured frontmatter controls [CARD-411].
 * Tool picker state is the single lever for requires_tools.
 */

import { applyWorkshopMetadata } from '../../utils/skill_frontmatter.js';

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
      const resp = await fetch(`/api/agent_training_factory/skills/${encodeURIComponent(skillId)}${query ? `?${query}` : ''}`);
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) throw new Error(data.detail || `HTTP ${resp.status}`);
      setIdentityLocked(true);
      if (factorySkillNameInput) factorySkillNameInput.value = data.name || skillId;
      if (factorySkillIdInput) factorySkillIdInput.value = data.skill_id || skillId;
      if (factorySkillTriggerInput) {
        const description = String(data.description || '').slice(0, 60);
        factorySkillTriggerInput.value = description;
        if (factorySkillTriggerCharCount) factorySkillTriggerCharCount.textContent = `${description.length}/60`;
      }
      if (factorySkillTierSelect) factorySkillTierSelect.value = data.tier || 'pack';
      const safety = data.safety || {};
      if (factorySkillSafetyReadOnly) factorySkillSafetyReadOnly.checked = Boolean(safety.read_only);
      if (factorySkillSafetyHitl) factorySkillSafetyHitl.checked = Boolean(safety.requires_hitl);
      if (factorySkillSafetyUntrusted) factorySkillSafetyUntrusted.checked = Boolean(safety.untrusted_input_allowed);
      setSelectedTools(new Set(Array.isArray(data.requires_tools) ? data.requires_tools : []));
      if (factorySkillMarkdownEditor) factorySkillMarkdownEditor.value = data.markdown_content || '';
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
