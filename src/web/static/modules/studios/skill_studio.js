/**
 * Skill Studio — skill lifecycle and tool scoping [CARD-418].
 * Pick/create, metadata, SKILL.md and the tool catalog. Save writes the skill store and
 * SQLite bindings (CARD-411). The Factory is retired (ADR-0060, CARD-496); the save, skills and
 * capabilities routes are /api/skill_studio/* and /api/tools_studio/capabilities (CARD-497).
 * Element ids keep their factory* prefix (ADR-0060 D5).
 */

import { $, escapeHtml, safeCreateIcons } from '../dom.js';
import { showToast } from '../ui/toast.js';
import { toSnakeCase } from '../utils/slug.js';
import { createSkillWorkshop, skillDeleteRequest } from './skill_studio/workshop_meta.js';
import { createSkillScopeUI } from './skill_studio/skill_scope.js';

export const SKILL_STUDIO_TAB = 'skill-studio';
export const SKILL_STUDIO_LABEL = 'Skill Studio';

const COMMON_STOP_WORDS = new Set([
  'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'as',
  'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', 'could',
  'did', 'do', 'does', 'doing', 'down', 'during', 'each', 'few', 'for', 'from', 'further', 'had',
  'has', 'have', 'having', 'he', 'her', 'here', 'hers', 'herself', 'him', 'himself', 'his', 'how',
  'i', 'if', 'in', 'into', 'is', 'it', 'its', 'itself', 'just', 'me', 'more', 'most', 'my', 'myself',
  'no', 'nor', 'not', 'now', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'our', 'ours',
  'ourselves', 'out', 'over', 'own', 'same', 'she', 'should', 'so', 'some', 'such', 'than', 'that',
  'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there', 'these', 'they', 'this', 'those',
  'through', 'to', 'too', 'under', 'until', 'up', 'very', 'was', 'we', 'were', 'what', 'when', 'where',
  'which', 'while', 'who', 'whom', 'why', 'with', 'would', 'you', 'your', 'yours', 'yourself',
]);

/**
 * Agent Studio / dock handoff into Skill Studio.
 * @param {{ agentId?: string|null, skillId?: string|null }} [link]
 */
export function planSkillStudioDeepLink({ agentId = null, skillId = null } = {}) {
  const skill = String(skillId || '').trim();
  const agent = String(agentId || '').trim();
  return {
    tab: SKILL_STUDIO_TAB,
    label: SKILL_STUDIO_LABEL,
    agentId: agent || null,
    skillId: skill || null,
    writeSurface: SKILL_STUDIO_TAB,
  };
}

export function initSkillStudio(_state, callbacks = {}) {
  const factoryExistingSkillSelect = $('factoryExistingSkillSelect');
  const factoryExistingSkillFilter = $('factoryExistingSkillFilter');
  const factoryNewSkillFormBtn = $('factoryNewSkillFormBtn');
  const factoryWorkshopSkillBadge = $('factoryWorkshopSkillBadge');
  const factorySkillNameInput = $('factorySkillNameInput');
  const factorySkillIdInput = $('factorySkillIdInput');
  if (factorySkillIdInput) factorySkillIdInput.readOnly = true;
  const factorySkillTriggerInput = $('factorySkillTriggerInput');
  const factorySkillTriggerCharCount = $('factorySkillTriggerCharCount');
  const factorySkillIntentInput = $('factorySkillIntentInput');
  const factoryGenerateRunbookBtn = $('factoryGenerateRunbookBtn');
  const factoryGenerateStatusText = $('factoryGenerateStatusText');
  const factorySkillMarkdownEditor = $('factorySkillMarkdownEditor');
  const factorySaveSkillBtn = $('factorySaveSkillBtn');
  const skillStudioDeleteBtn = $('skillStudioDeleteBtn');
  const factorySaveFeedbackMsg = $('factorySaveFeedbackMsg');
  const factorySkillSafetyReadOnly = $('factorySkillSafetyReadOnly');
  const factorySkillSafetyHitl = $('factorySkillSafetyHitl');
  const factorySkillSafetyUntrusted = $('factorySkillSafetyUntrusted');
  const factoryRequiredToolsChips = $('factoryRequiredToolsChips');
  const factoryToolSearchInput = $('factoryToolSearchInput');
  const factorySelectAllToolsBtn = $('factorySelectAllToolsBtn');
  const factoryClearAllToolsBtn = $('factoryClearAllToolsBtn');
  const factoryAutoSuggestToolsBtn = $('factoryAutoSuggestToolsBtn');
  const factoryCapabilitiesContainer = $('factoryCapabilitiesContainer');
  const factorySelectedToolCountBadge = $('factorySelectedToolCountBadge');
  const factorySourceContextInput = $('factorySourceContextInput');
  const factoryRefreshBtn = $('factoryRefreshBtn');
  const factoryCurrentSkillsList = $('factoryCurrentSkillsList');
  const factoryAssignedSkillsCount = $('factoryAssignedSkillsCount');

  let currentCapabilities = [];
  let selectedTools = new Set();
  let assignedSkills = [];
  let skillIdentityLocked = false;
  let pinAgentId = '';
  let pinAgentName = '';
  let pinRolePersona = '';
  let queuedLink = null;
  let pendingSkillId = '';
  let loadGen = 0;
  let skillDeletable = false;

  const workshop = createSkillWorkshop({
    showToast,
    getCapabilities: () => currentCapabilities,
    getSelectedTools: () => selectedTools,
    setSelectedTools: (next) => { selectedTools = next; },
    setIdentityLocked: (value) => { skillIdentityLocked = value; },
    renderCapabilities: (filter) => renderCapabilities(filter),
    updateSelectedToolBadge: () => updateSelectedToolBadge(),
    elements: () => ({
      factorySkillNameInput,
      factorySkillIdInput,
      factorySkillTriggerInput,
      factorySkillTriggerCharCount,
      factorySkillSafetyReadOnly,
      factorySkillSafetyHitl,
      factorySkillSafetyUntrusted,
      factorySkillMarkdownEditor,
      factoryRequiredToolsChips,
      factoryToolSearchInput,
    }),
  });
  const { workshopFields, syncFrontmatter, loadExistingSkill: loadWorkshopSkill } = workshop;

  const skillScope = createSkillScopeUI({
    getAssignedSkills: () => assignedSkills,
    getAgentId: () => pinAgentId,
    onLoadSkill: (skillId, agentId) => { loadExistingSkill(skillId, agentId); },
    onNewSkill: () => resetNewSkillForm({ clearPicker: false }),
    onOpenInSkillStudio: (skillId) => {
      if (typeof callbacks.openSkillStudio === 'function') {
        callbacks.openSkillStudio(pinAgentId || null, skillId || null);
        return;
      }
      loadExistingSkill(skillId, pinAgentId);
    },
    elements: () => ({
      factoryCurrentSkillsList,
      factoryAssignedSkillsCount,
      factoryExistingSkillSelect,
      factoryExistingSkillFilter,
      factoryNewSkillFormBtn,
      factoryWorkshopSkillBadge,
    }),
  });
  skillScope.bindEvents();

  function queueDeepLink(agentId, skillId) {
    queuedLink = planSkillStudioDeepLink({ agentId, skillId });
    if (queuedLink.skillId) pendingSkillId = queuedLink.skillId;
  }

  function syncAgentScope(snapshot = {}, { refreshPicker = true } = {}) {
    pinAgentId = String(snapshot.agentId || '').trim();
    pinAgentName = String(snapshot.agentName || '').trim();
    pinRolePersona = String(snapshot.rolePersona || '').trim();
    if (Array.isArray(snapshot.skills)) assignedSkills = snapshot.skills.slice();
    skillScope.renderAssignedSkills();
    if (refreshPicker) {
      const selected = factoryExistingSkillSelect ? factoryExistingSkillSelect.value : '';
      skillScope.refreshEditableSkillOptions(selected);
    }
  }

  function resetNewSkillForm({ clearPicker = true } = {}) {
    if (factorySkillNameInput) factorySkillNameInput.value = '';
    if (factorySkillIdInput) {
      factorySkillIdInput.value = '';
      factorySkillIdInput.readOnly = true;
    }
    if (factorySkillTriggerInput) {
      factorySkillTriggerInput.value = '';
      if (factorySkillTriggerCharCount) factorySkillTriggerCharCount.textContent = '0/60';
    }
    if (factorySkillIntentInput) factorySkillIntentInput.value = '';
    if (factorySkillMarkdownEditor) factorySkillMarkdownEditor.value = '';
    if (factorySkillSafetyReadOnly) factorySkillSafetyReadOnly.checked = false;
    if (factorySkillSafetyHitl) factorySkillSafetyHitl.checked = false;
    if (factorySkillSafetyUntrusted) factorySkillSafetyUntrusted.checked = false;
    skillIdentityLocked = false;
    selectedTools = new Set();
    workshop.renderRequiredToolChips();
    if (factorySaveFeedbackMsg) factorySaveFeedbackMsg.classList.add('hidden');
    if (clearPicker) skillScope.clearPickerSelection();
    else skillScope.setWorkshopBadge('New skill');
    syncDeleteButton(false);
  }

  function syncDeleteButton(deletable) {
    skillDeletable = deletable === true;
    if (!skillStudioDeleteBtn) return;
    skillStudioDeleteBtn.classList.toggle('hidden', !skillDeletable);
    skillStudioDeleteBtn.disabled = !skillDeletable;
  }

  async function loadExistingSkill(skillId, agentId) {
    const view = await loadWorkshopSkill(skillId, agentId || pinAgentId);
    if (view && view.ok) {
      skillScope.selectSkillInPicker(skillId);
      syncDeleteButton(view.deletable);
      return view;
    }
    syncDeleteButton(false);
    return null;
  }

  async function handleDeleteSkill() {
    const skillId = (factorySkillIdInput && factorySkillIdInput.value.trim()) || '';
    if (!skillDeletable) {
      showToast('This skill cannot be deleted from Skill Studio.', 'warning');
      return;
    }
    const confirmed = typeof window !== 'undefined' && typeof window.confirm === 'function'
      ? window.confirm(`Delete skill ${skillId}? This removes it from the skill store.`)
      : false;
    const request = skillDeleteRequest(skillId, { confirmed, deletable: skillDeletable });
    if (!request.allowed || !request.url) return;
    if (skillStudioDeleteBtn) skillStudioDeleteBtn.disabled = true;
    try {
      const resp = await fetch(request.url, { method: request.method });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        const detail = data && (data.detail || data.message);
        throw new Error(detail || `Server returned ${resp.status}`);
      }
      showToast(`Deleted ${skillId}.`, 'success');
      resetNewSkillForm({ clearPicker: true });
      await skillScope.refreshEditableSkillOptions('');
    } catch (err) {
      console.error('[SkillStudio] Delete failed:', err);
      showToast(`Delete failed: ${err.message}`, 'error');
      syncDeleteButton(skillDeletable);
    }
  }

  async function handleGenerateRunbook() {
    const skillName = (factorySkillNameInput && factorySkillNameInput.value.trim()) || '';
    const skillId = (factorySkillIdInput && factorySkillIdInput.value.trim()) || toSnakeCase(skillName);
    const trigger = (factorySkillTriggerInput && factorySkillTriggerInput.value.trim()) || '';
    const intent = (factorySkillIntentInput && factorySkillIntentInput.value.trim()) || '';
    const sourceContext = (factorySourceContextInput && factorySourceContextInput.value.trim()) || '';
    const agentId = pinAgentId || 'general';

    if (!skillName) {
      showToast('Please enter a Skill Name first.', 'warning');
      if (factorySkillNameInput) factorySkillNameInput.focus();
      return;
    }
    if (!trigger) {
      showToast('Please specify a Trigger Condition (<= 60 chars).', 'warning');
      if (factorySkillTriggerInput) factorySkillTriggerInput.focus();
      return;
    }

    if (factoryGenerateRunbookBtn) {
      factoryGenerateRunbookBtn.disabled = true;
      factoryGenerateRunbookBtn.classList.add('opacity-50', 'cursor-not-allowed');
    }
    if (factoryGenerateStatusText) {
      factoryGenerateStatusText.textContent = 'Generating standard runbook...';
      factoryGenerateStatusText.classList.remove('hidden');
    }

    try {
      const resp = await fetch('/api/skill_studio/runbook', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: agentId,
          skill_id: skillId,
          skill_name: skillName,
          trigger_description: trigger,
          intent_notes: intent,
          selected_tools: Array.from(selectedTools),
          source_context: sourceContext,
        }),
      });

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned ${resp.status}`);
      }

      const data = await resp.json();
      if (factorySkillMarkdownEditor) {
        factorySkillMarkdownEditor.value = data.markdown_content || '';
      }
      syncFrontmatter();
      showToast(`✨ Generated runbook for ${skillName}!`, 'success');
    } catch (err) {
      console.error('[SkillStudio] Failed to generate runbook:', err);
      showToast(`Runbook generation failed: ${err.message}`, 'error');
    } finally {
      if (factoryGenerateRunbookBtn) {
        factoryGenerateRunbookBtn.disabled = false;
        factoryGenerateRunbookBtn.classList.remove('opacity-50', 'cursor-not-allowed');
      }
      if (factoryGenerateStatusText) {
        factoryGenerateStatusText.classList.add('hidden');
      }
    }
  }

  async function handleSaveSkill() {
    const skillName = (factorySkillNameInput && factorySkillNameInput.value.trim()) || '';
    const skillId = (factorySkillIdInput && factorySkillIdInput.value.trim()) || toSnakeCase(skillName);
    const fields = workshopFields();
    syncFrontmatter();
    const content = (factorySkillMarkdownEditor && factorySkillMarkdownEditor.value.trim()) || '';

    if (!skillId) {
      showToast('Skill ID is required.', 'warning');
      if (factorySkillIdInput) factorySkillIdInput.focus();
      return;
    }
    if (!content) {
      showToast('Skill markdown content is empty. Generate or write a runbook first.', 'warning');
      if (factorySkillMarkdownEditor) factorySkillMarkdownEditor.focus();
      return;
    }

    if (factorySaveSkillBtn) {
      factorySaveSkillBtn.disabled = true;
      factorySaveSkillBtn.classList.add('opacity-50', 'cursor-not-allowed');
    }

    const payload = {
      skill_id: skillId,
      skill_content: content,
      auto_pin: Boolean(pinAgentId),
      name: fields.name || skillName,
      description: fields.description,
      tier: fields.tier,
      safety: fields.safety,
      requires_tools: fields.requires_tools,
    };
    if (pinAgentId) {
      payload.agent_id = pinAgentId;
      if (pinAgentName) payload.agent_name = pinAgentName;
      if (pinRolePersona) payload.role_persona = pinRolePersona;
    }

    try {
      const resp = await fetch('/api/skill_studio/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned ${resp.status}`);
      }

      const saved = await resp.json();
      if (factorySkillMarkdownEditor && saved.markdown_content) {
        factorySkillMarkdownEditor.value = saved.markdown_content;
      }
      if (pinAgentId && !assignedSkills.includes(skillId)) {
        assignedSkills.push(skillId);
      }
      skillScope.renderAssignedSkills();
      await skillScope.refreshEditableSkillOptions(skillId);
      skillScope.selectSkillInPicker(skillId);

      const pinnedNote = pinAgentId ? ` and pinned to ${pinAgentId}` : '';
      if (factorySaveFeedbackMsg) {
        factorySaveFeedbackMsg.textContent = `✓ Saved ${skillId}${pinnedNote}`;
        factorySaveFeedbackMsg.classList.remove('hidden');
        setTimeout(() => {
          if (factorySaveFeedbackMsg) factorySaveFeedbackMsg.classList.add('hidden');
        }, 4000);
      }
      showToast(`💾 Skill ${skillId} saved${pinnedNote}.`, 'success');
    } catch (err) {
      console.error('[SkillStudio] Failed to save skill:', err);
      showToast(`Save failed: ${err.message}`, 'error');
    } finally {
      if (factorySaveSkillBtn) {
        factorySaveSkillBtn.disabled = false;
        factorySaveSkillBtn.classList.remove('opacity-50', 'cursor-not-allowed');
      }
    }
  }

  async function loadCapabilities() {
    try {
      const resp = await fetch('/api/tools_studio/capabilities');
      if (resp.ok) {
        const data = await resp.json();
        currentCapabilities = data.namespaces || [];
        renderCapabilities((factoryToolSearchInput && factoryToolSearchInput.value) || '');
      }
    } catch (err) {
      console.error('[SkillStudio] Failed to load capabilities:', err);
    }
  }

  function renderCapabilities(filterText = '') {
    if (!factoryCapabilitiesContainer) return;
    const q = (filterText || '').toLowerCase().trim();

    if (!currentCapabilities || currentCapabilities.length === 0) {
      factoryCapabilitiesContainer.innerHTML = '<div class="text-[11px] text-slate-500 italic p-2">No capabilities registered.</div>';
      return;
    }

    factoryCapabilitiesContainer.innerHTML = '';
    let totalRendered = 0;

    currentCapabilities.forEach((ns) => {
      const matchingTools = (ns.tools || []).filter((t) => {
        if (!q) return true;
        return (t.name || '').toLowerCase().includes(q) || (t.description || '').toLowerCase().includes(q);
      });

      if (matchingTools.length === 0) return;
      totalRendered += matchingTools.length;

      const groupCard = document.createElement('div');
      groupCard.className = 'bg-[#13161f]/80 border border-white/[0.06] rounded-xl overflow-hidden mb-2';

      const groupHeader = document.createElement('div');
      groupHeader.className = 'px-3 py-2 bg-white/[0.02] border-b border-white/[0.04] flex items-center justify-between cursor-pointer select-none';
      groupHeader.innerHTML = `
        <div class="flex items-center space-x-2">
          <i data-lucide="package" class="w-3.5 h-3.5 text-purple-400"></i>
          <span class="text-xs font-semibold text-white">${escapeHtml(ns.name)}</span>
        </div>
        <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-950/60 text-purple-300 border border-purple-500/20">${matchingTools.length} tools</span>
      `;

      const toolsList = document.createElement('div');
      toolsList.className = 'p-2 space-y-1.5';

      matchingTools.forEach((tool) => {
        const isChecked = selectedTools.has(tool.name);
        const item = document.createElement('label');
        item.className = 'flex items-start space-x-2 p-1.5 rounded-lg hover:bg-white/[0.04] cursor-pointer transition';
        item.innerHTML = `
          <input type="checkbox" class="mt-0.5 rounded border-white/[0.2] bg-[#08090c] text-purple-600 focus:ring-purple-500 focus:ring-offset-0" data-tool-name="${escapeHtml(tool.name)}" ${isChecked ? 'checked' : ''}>
          <div class="min-w-0 flex-1 text-[11px]">
            <div class="font-mono text-slate-200 font-medium truncate">${escapeHtml(tool.name)}</div>
            <div class="text-slate-400 text-[10px] line-clamp-1">${escapeHtml(tool.description || 'No description')}</div>
          </div>
        `;

        const chk = item.querySelector('input[type="checkbox"]');
        chk.addEventListener('change', (e) => {
          if (e.target.checked) {
            selectedTools.add(tool.name);
          } else {
            selectedTools.delete(tool.name);
          }
          syncFrontmatter();
        });

        toolsList.appendChild(item);
      });

      groupCard.appendChild(groupHeader);
      groupCard.appendChild(toolsList);
      factoryCapabilitiesContainer.appendChild(groupCard);
    });

    if (totalRendered === 0) {
      factoryCapabilitiesContainer.innerHTML = `<div class="text-[11px] text-slate-500 italic p-2">No capabilities match "${escapeHtml(q)}".</div>`;
    }

    safeCreateIcons({ root: factoryCapabilitiesContainer });
  }

  function handleSelectAllVisibleTools() {
    if (!factoryCapabilitiesContainer) return;
    const checkboxes = factoryCapabilitiesContainer.querySelectorAll('input[type="checkbox"][data-tool-name]');
    let count = 0;
    checkboxes.forEach((cb) => {
      const toolName = cb.dataset.toolName;
      if (toolName && !cb.checked) {
        cb.checked = true;
        selectedTools.add(toolName);
        count++;
      }
    });
    syncFrontmatter();
    showToast(count > 0 ? `Selected ${count} matching tool(s)` : 'All matching tools are already selected', 'info');
  }

  function handleClearAllVisibleTools() {
    if (!factoryCapabilitiesContainer) return;
    const checkboxes = factoryCapabilitiesContainer.querySelectorAll('input[type="checkbox"][data-tool-name]');
    let count = 0;
    checkboxes.forEach((cb) => {
      const toolName = cb.dataset.toolName;
      if (toolName && cb.checked) {
        cb.checked = false;
        selectedTools.delete(toolName);
        count++;
      }
    });
    syncFrontmatter();
    showToast(count > 0 ? `Cleared ${count} tool(s)` : 'No tools were selected in current view', 'info');
  }

  function handleAutoSuggestTools() {
    const textSources = [
      (factorySkillNameInput && factorySkillNameInput.value) || '',
      (factorySkillTriggerInput && factorySkillTriggerInput.value) || '',
      (factorySkillIntentInput && factorySkillIntentInput.value) || '',
    ].join(' ').toLowerCase();

    const tokens = textSources
      .replace(/[^a-z0-9]+/g, ' ')
      .split(/\s+/)
      .filter((w) => w.length >= 3 && !COMMON_STOP_WORDS.has(w));

    if (tokens.length === 0) {
      showToast('Enter a skill name, trigger, or intent notes first to suggest tools', 'warning');
      return;
    }

    let addedCount = 0;
    (currentCapabilities || []).forEach((ns) => {
      (ns.tools || []).forEach((t) => {
        const toolText = `${t.name} ${t.description || ''} ${ns.name || ''}`.toLowerCase();
        const matches = tokens.some((tok) => toolText.includes(tok));
        if (matches && !selectedTools.has(t.name)) {
          selectedTools.add(t.name);
          addedCount++;
        }
      });
    });

    renderCapabilities((factoryToolSearchInput && factoryToolSearchInput.value) || '');
    syncFrontmatter();
    if (addedCount > 0) {
      showToast(`Auto-suggested and selected ${addedCount} tool(s)`, 'success');
    } else {
      showToast('No matching tools found in catalog for current intent keywords', 'info');
    }
  }

  function updateSelectedToolBadge() {
    if (factorySelectedToolCountBadge) {
      factorySelectedToolCountBadge.textContent = `${selectedTools.size} Selected`;
    }
  }

  if (factorySkillNameInput) {
    factorySkillNameInput.addEventListener('input', () => {
      if (!skillIdentityLocked && factorySkillIdInput) {
        factorySkillIdInput.value = toSnakeCase(factorySkillNameInput.value);
      }
      syncFrontmatter();
    });
  }

  if (factorySkillTriggerInput) {
    factorySkillTriggerInput.addEventListener('input', () => {
      const len = factorySkillTriggerInput.value.length;
      if (factorySkillTriggerCharCount) {
        factorySkillTriggerCharCount.textContent = `${len}/60`;
        if (len > 55) {
          factorySkillTriggerCharCount.className = 'text-[10px] font-mono text-amber-400';
        } else {
          factorySkillTriggerCharCount.className = 'text-[10px] font-mono text-slate-500';
        }
      }
      syncFrontmatter();
    });
  }

  [factorySkillSafetyReadOnly, factorySkillSafetyHitl, factorySkillSafetyUntrusted].forEach((el) => {
    if (!el) return;
    el.addEventListener('change', () => syncFrontmatter());
  });

  if (factoryGenerateRunbookBtn) {
    factoryGenerateRunbookBtn.addEventListener('click', handleGenerateRunbook);
  }

  if (factorySaveSkillBtn) {
    factorySaveSkillBtn.addEventListener('click', handleSaveSkill);
  }

  if (skillStudioDeleteBtn) {
    skillStudioDeleteBtn.addEventListener('click', handleDeleteSkill);
  }

  if (factoryToolSearchInput) {
    factoryToolSearchInput.addEventListener('input', () => {
      renderCapabilities(factoryToolSearchInput.value);
    });
  }

  if (factorySelectAllToolsBtn) {
    factorySelectAllToolsBtn.addEventListener('click', handleSelectAllVisibleTools);
  }

  if (factoryClearAllToolsBtn) {
    factoryClearAllToolsBtn.addEventListener('click', handleClearAllVisibleTools);
  }

  if (factoryAutoSuggestToolsBtn) {
    factoryAutoSuggestToolsBtn.addEventListener('click', handleAutoSuggestTools);
  }

  if (factoryRefreshBtn) {
    factoryRefreshBtn.addEventListener('click', async () => {
      showToast('Refreshing Skill Studio...', 'info');
      await Promise.all([
        loadCapabilities(),
        skillScope.refreshEditableSkillOptions(factoryExistingSkillSelect ? factoryExistingSkillSelect.value : ''),
      ]);
      showToast('Skill Studio refreshed.', 'success');
    });
  }

  if (typeof window !== 'undefined') {
    window.openSkillStudioForSkill = ({ agentId = null, skillId = null } = {}) => {
      if (typeof callbacks.openSkillStudio === 'function') {
        callbacks.openSkillStudio(agentId, skillId);
        return;
      }
      queueDeepLink(agentId, skillId);
      loadSkillStudio(agentId, skillId);
    };
  }

  async function loadSkillStudio(agentId = null, skillId = null) {
    const gen = ++loadGen;
    const queued = queuedLink;
    queuedLink = null;
    const plan = planSkillStudioDeepLink({
      agentId: agentId || (queued && queued.agentId) || pinAgentId,
      skillId: skillId || (queued && queued.skillId) || pendingSkillId || '',
    });
    if (plan.agentId) pinAgentId = plan.agentId;
    await Promise.all([
      loadCapabilities(),
      skillScope.refreshEditableSkillOptions(plan.skillId || (factoryExistingSkillSelect ? factoryExistingSkillSelect.value : '')),
    ]);
    if (gen !== loadGen) return;
    if (plan.skillId) {
      await loadExistingSkill(plan.skillId, plan.agentId);
      if (gen === loadGen) pendingSkillId = '';
    }
  }

  const controller = {
    loadSkillStudio,
    queueDeepLink,
    syncAgentScope,
    stopPolling: () => {},
  };
  return controller;
}
