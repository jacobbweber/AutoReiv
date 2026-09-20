/**
 * Capabilities & Scaffolding Workshop Studio Controller [CARD-386]
 *
 * Replaces the legacy 8-phase synthetic tool factory with a 3-column workbench:
 * Column 1: Agent Brief (New or Existing)
 * Column 2: Skills & Runbook (Matt Pocock SKILL.md with Auto-Pin)
 * Column 3: Capabilities & Grounding (Live MCP tool inspector & source context)
 */

import { $, escapeHtml, safeCreateIcons } from '../dom.js';
import { showToast } from '../ui/toast.js';

// ==================== Scaffolder Helpers & Gap Bindings ====================
export function populateFactoryAgentOptions(selectEl, agents = [], selectedAgentId = '') {
  if (!selectEl) return;
  selectEl.innerHTML = '';

  const createOpt = (val, text) => {
    if (typeof document !== 'undefined' && document.createElement) {
      const opt = document.createElement('option');
      opt.value = val;
      opt.textContent = text;
      return opt;
    }
    return { value: val, textContent: text };
  };

  const defaultOpt = createOpt('', 'All Agents (Platform View)');
  selectEl.appendChild(defaultOpt);

  (agents || []).forEach((ag) => {
    if (ag.id === 'agent_builder' || ag.id === 'agent-builder') return;
    const opt = createOpt(ag.id, `${ag.name || ag.id} (${ag.id})`);
    selectEl.appendChild(opt);
  });

  if (selectedAgentId) {
    selectEl.value = selectedAgentId;
  }
}

export function applyBacklogGapToIntake(gap = {}) {
  if (!gap) return null;
  const seedIntent = gap.missing_capability || gap.identified_capability || gap.description || gap.intent || gap.name || '';
  const objectives = gap.objectives || (gap.suggested_steps ? gap.suggested_steps : (seedIntent ? [seedIntent] : []));
  return {
    targetAgentId: gap.agent_id || gap.target_agent_id || '',
    seedIntent,
    objectives,
    deliverableType: gap.suggested_deliverable || gap.deliverable_type || 'tool',
    referenceDocs: gap.user_intent || '',
    capabilityGapId: gap.id || null,
  };
}

export function buildForgeInitialPrompt(agentId = '') {
  if (agentId) {
    return `Let's design a new capability for agent ${agentId}. What tools or skills do we need?`;
  }
  return `Let's design a new capability. What agent, tools, or skills should we build?`;
}

export const LEGACY_GAP_TRIGGER_CLASS = 'btn-train-gap';
export const LEGACY_GAP_PAYLOAD_FIELD = 'identified_capability';

export function toSnakeCase(text) {
  return (text || '')
    .toString()
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
}

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

// ==================== Studio Lifecycle Manager ====================
export function initFactoryStudio(state, callbacks = {}) {
  // DOM Elements - Column 1: Agent Brief
  const factoryAgentSelect = $('factoryAgentSelect');
  const factoryAgentModeBadge = $('factoryAgentModeBadge');
  const factoryAgentIdInput = $('factoryAgentIdInput');
  const factoryAgentNameInput = $('factoryAgentNameInput');
  const factoryAgentPromptInput = $('factoryAgentPromptInput');

  // DOM Elements - Column 2: Skills & Runbook
  const factoryCurrentSkillsList = $('factoryCurrentSkillsList');
  const factoryAssignedSkillsCount = $('factoryAssignedSkillsCount');
  const factoryNewSkillFormBtn = $('factoryNewSkillFormBtn');
  const factorySkillNameInput = $('factorySkillNameInput');
  const factorySkillIdInput = $('factorySkillIdInput');
  if (factorySkillIdInput) {
    factorySkillIdInput.readOnly = true;
  }
  const factorySkillTriggerInput = $('factorySkillTriggerInput');
  const factorySkillTriggerCharCount = $('factorySkillTriggerCharCount');
  const factorySkillIntentInput = $('factorySkillIntentInput');
  const factoryGenerateRunbookBtn = $('factoryGenerateRunbookBtn');
  const factoryGenerateStatusText = $('factoryGenerateStatusText');
  const factorySkillMarkdownEditor = $('factorySkillMarkdownEditor');
  const factorySaveSkillBtn = $('factorySaveSkillBtn');
  const factorySaveFeedbackMsg = $('factorySaveFeedbackMsg');

  // DOM Elements - Column 3: Capabilities & Grounding
  const factoryToolSearchInput = $('factoryToolSearchInput');
  const factorySelectAllToolsBtn = $('factorySelectAllToolsBtn');
  const factoryClearAllToolsBtn = $('factoryClearAllToolsBtn');
  const factoryAutoSuggestToolsBtn = $('factoryAutoSuggestToolsBtn');
  const factoryCapabilitiesContainer = $('factoryCapabilitiesContainer');
  const factorySelectedToolCountBadge = $('factorySelectedToolCountBadge');
  const factorySourceContextInput = $('factorySourceContextInput');
  const factoryRefreshBtn = $('factoryRefreshBtn');

  // Internal State
  let loadedAgents = [];
  let currentCapabilities = [];
  let selectedTools = new Set();
  let assignedSkills = [];

  // Deep-link helper for CARD-314
  if (typeof window !== 'undefined') {
    window.openFactoryStudioForAgent = (agentId) => {
      if (typeof callbacks.openFactoryStudio === 'function') {
        callbacks.openFactoryStudio(agentId);
      }
      setAgentScope(agentId);
    };
  }

  // ----------------------------------------------------
  // Column 1: Agent Management
  // ----------------------------------------------------
  async function loadAgents(preferredAgentId = null) {
    try {
      const resp = await fetch('/api/agents');
      if (resp.ok) {
        const data = await resp.json();
        loadedAgents = Array.isArray(data) ? data : (data.agents || []);
        if (factoryAgentSelect) {
          factoryAgentSelect.innerHTML = '';
          const newOpt = document.createElement('option');
          newOpt.value = '__new__';
          newOpt.textContent = '+ Create New Agent';
          factoryAgentSelect.appendChild(newOpt);

          loadedAgents.forEach((ag) => {
            if (ag.id === 'agent_builder' || ag.id === 'agent-builder') return;
            const opt = document.createElement('option');
            opt.value = ag.id;
            opt.textContent = `${ag.name || ag.id} (${ag.id})`;
            if (ag.id === preferredAgentId) opt.selected = true;
            factoryAgentSelect.appendChild(opt);
          });
        }
        onAgentSelectChanged();
      }
    } catch (err) {
      console.error('[FactoryStudio] Failed to load agents:', err);
    }
  }

  function setAgentScope(agentId) {
    if (factoryAgentSelect) {
      factoryAgentSelect.value = agentId || '__new__';
      onAgentSelectChanged();
    }
  }

  function onAgentSelectChanged() {
    if (!factoryAgentSelect) return;
    const val = factoryAgentSelect.value;
    const factoryIntakeAgentIdBadge = $('factoryIntakeAgentIdBadge');
    const factoryIntakeLivePackPath = $('factoryIntakeLivePackPath');
    const factoryIntakeLiveCounts = $('factoryIntakeLiveCounts');

    if (val === '__new__') {
      if (factoryAgentModeBadge) {
        factoryAgentModeBadge.textContent = 'New';
        factoryAgentModeBadge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-brand-950/60 border border-brand-500/30 text-brand-400';
      }
      if (factoryIntakeAgentIdBadge) {
        factoryIntakeAgentIdBadge.textContent = 'New Agent';
        factoryIntakeAgentIdBadge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-brand-950/80 text-brand-300 border border-brand-500/30';
      }
      if (factoryIntakeLivePackPath) {
        factoryIntakeLivePackPath.textContent = 'packs/<agent_id>';
      }
      if (factoryIntakeLiveCounts) {
        factoryIntakeLiveCounts.textContent = 'Skills: 0 | Tools: 0';
      }
      if (factoryAgentIdInput) {
        factoryAgentIdInput.value = toSnakeCase(factoryAgentNameInput ? factoryAgentNameInput.value : '');
        factoryAgentIdInput.readOnly = true;
      }
      if (factoryAgentNameInput) {
        factoryAgentNameInput.value = '';
        factoryAgentNameInput.focus();
      }
      if (factoryAgentPromptInput) factoryAgentPromptInput.value = '';
      assignedSkills = [];
    } else {
      const agent = loadedAgents.find((a) => a.id === val);
      if (factoryAgentModeBadge) {
        factoryAgentModeBadge.textContent = 'Existing';
        factoryAgentModeBadge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-500/30 text-emerald-400';
      }
      const agentId = agent ? agent.id : val;
      if (factoryIntakeAgentIdBadge) {
        factoryIntakeAgentIdBadge.textContent = agent ? (agent.name || agent.id) : (val || 'AutoReiv');
        factoryIntakeAgentIdBadge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-950/80 border border-indigo-500/30 text-indigo-300';
      }
      if (factoryIntakeLivePackPath) {
        factoryIntakeLivePackPath.textContent = `packs/${agentId || 'AutoReiv'}`;
      }
      const sCount = agent && agent.allowed_skill ? agent.allowed_skill.length : (agent && agent.skills ? agent.skills.length : 0);
      const tCount = agent && agent.tools ? agent.tools.length : 0;
      if (factoryIntakeLiveCounts) {
        factoryIntakeLiveCounts.textContent = `Skills: ${sCount} | Tools: ${tCount}`;
      }
      if (agent) {
        if (factoryAgentIdInput) {
          factoryAgentIdInput.value = agent.id || '';
          factoryAgentIdInput.readOnly = true;
        }
        if (factoryAgentNameInput) factoryAgentNameInput.value = agent.name || '';
        if (factoryAgentPromptInput) factoryAgentPromptInput.value = agent.system_prompt || agent.description || '';
        assignedSkills = agent.allowed_skill ? [...agent.allowed_skill] : (agent.skills ? [...agent.skills] : []);
      }
    }
    renderAssignedSkills();
  }

  // ----------------------------------------------------
  // Column 2: Skills & Runbook
  // ----------------------------------------------------
  function renderAssignedSkills() {
    if (!factoryCurrentSkillsList) return;
    if (factoryAssignedSkillsCount) {
      factoryAssignedSkillsCount.textContent = `${assignedSkills.length} Assigned`;
    }

    if (!assignedSkills || assignedSkills.length === 0) {
      factoryCurrentSkillsList.innerHTML = '<span class="text-[11px] text-slate-500 italic">No skills assigned yet.</span>';
      return;
    }

    factoryCurrentSkillsList.innerHTML = '';
    assignedSkills.forEach((sid) => {
      const pill = document.createElement('span');
      pill.className = 'inline-flex items-center space-x-1.5 px-2 py-1 rounded-lg text-xs font-mono bg-[#13161f] border border-white/[0.08] text-emerald-300';
      pill.innerHTML = `
        <i data-lucide="check" class="w-3 h-3 text-emerald-400"></i>
        <span>${escapeHtml(sid)}</span>
      `;
      factoryCurrentSkillsList.appendChild(pill);
    });
    safeCreateIcons({ root: factoryCurrentSkillsList });
  }

  function resetNewSkillForm() {
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
    if (factorySaveFeedbackMsg) factorySaveFeedbackMsg.classList.add('hidden');
  }

  async function handleGenerateRunbook() {
    const skillName = (factorySkillNameInput && factorySkillNameInput.value.trim()) || '';
    const skillId = (factorySkillIdInput && factorySkillIdInput.value.trim()) || toSnakeCase(skillName);
    const trigger = (factorySkillTriggerInput && factorySkillTriggerInput.value.trim()) || '';
    const intent = (factorySkillIntentInput && factorySkillIntentInput.value.trim()) || '';
    const sourceContext = (factorySourceContextInput && factorySourceContextInput.value.trim()) || '';
    const agentId = (factoryAgentIdInput && factoryAgentIdInput.value.trim()) || 'general';

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
      const resp = await fetch('/api/agent_training_factory/scaffold/runbook', {
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
      showToast(`✨ Generated runbook for ${skillName}!`, 'success');
    } catch (err) {
      console.error('[FactoryStudio] Failed to generate runbook:', err);
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
    const agentId = (factoryAgentIdInput && factoryAgentIdInput.value.trim()) || '';
    const agentName = (factoryAgentNameInput && factoryAgentNameInput.value.trim()) || '';
    const rolePersona = (factoryAgentPromptInput && factoryAgentPromptInput.value.trim()) || '';
    const skillName = (factorySkillNameInput && factorySkillNameInput.value.trim()) || '';
    const skillId = (factorySkillIdInput && factorySkillIdInput.value.trim()) || toSnakeCase(skillName);
    const content = (factorySkillMarkdownEditor && factorySkillMarkdownEditor.value.trim()) || '';

    if (!agentId) {
      showToast('Agent ID is required.', 'warning');
      if (factoryAgentIdInput) factoryAgentIdInput.focus();
      return;
    }
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

    try {
      const resp = await fetch('/api/agent_training_factory/scaffold/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: agentId,
          agent_name: agentName,
          role_persona: rolePersona,
          skill_id: skillId,
          skill_content: content,
          auto_pin: true,
        }),
      });

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned ${resp.status}`);
      }

      await resp.json();
      if (!assignedSkills.includes(skillId)) {
        assignedSkills.push(skillId);
      }
      renderAssignedSkills();

      if (factorySaveFeedbackMsg) {
        factorySaveFeedbackMsg.textContent = `✓ Saved & Pinned ${skillId} to ${agentId}!`;
        factorySaveFeedbackMsg.classList.remove('hidden');
        setTimeout(() => {
          if (factorySaveFeedbackMsg) factorySaveFeedbackMsg.classList.add('hidden');
        }, 4000);
      }
      showToast(`💾 Skill ${skillId} saved and pinned to ${agentId}!`, 'success');

      await loadAgents(agentId);
    } catch (err) {
      console.error('[FactoryStudio] Failed to save skill:', err);
      showToast(`Save failed: ${err.message}`, 'error');
    } finally {
      if (factorySaveSkillBtn) {
        factorySaveSkillBtn.disabled = false;
        factorySaveSkillBtn.classList.remove('opacity-50', 'cursor-not-allowed');
      }
    }
  }

  // ----------------------------------------------------
  // Column 3: Capabilities & Grounding
  // ----------------------------------------------------
  async function loadCapabilities() {
    try {
      const resp = await fetch('/api/agent_training_factory/capabilities');
      if (resp.ok) {
        const data = await resp.json();
        currentCapabilities = data.namespaces || [];
        renderCapabilities((factoryToolSearchInput && factoryToolSearchInput.value) || '');
      }
    } catch (err) {
      console.error('[FactoryStudio] Failed to load capabilities:', err);
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
          updateSelectedToolBadge();
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
    updateSelectedToolBadge();
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
    updateSelectedToolBadge();
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
    updateSelectedToolBadge();
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

  // ----------------------------------------------------
  // Event Listeners Binding
  // ----------------------------------------------------
  if (factoryAgentSelect) {
    factoryAgentSelect.addEventListener('change', onAgentSelectChanged);
  }

  if (factoryAgentNameInput) {
    factoryAgentNameInput.addEventListener('input', () => {
      if (factoryAgentSelect && factoryAgentSelect.value === '__new__') {
        const slug = toSnakeCase(factoryAgentNameInput.value);
        if (factoryAgentIdInput) factoryAgentIdInput.value = slug;
        const badge = $('factoryIntakeAgentIdBadge');
        const packPath = $('factoryIntakeLivePackPath');
        if (badge) badge.textContent = slug || 'New Agent';
        if (packPath) packPath.textContent = slug ? `packs/${slug}` : 'packs/<agent_id>';
      }
    });
  }

  if (factorySkillNameInput) {
    factorySkillNameInput.addEventListener('input', () => {
      if (factorySkillIdInput) {
        factorySkillIdInput.value = toSnakeCase(factorySkillNameInput.value);
      }
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
    });
  }

  if (factoryGenerateRunbookBtn) {
    factoryGenerateRunbookBtn.addEventListener('click', handleGenerateRunbook);
  }

  if (factorySaveSkillBtn) {
    factorySaveSkillBtn.addEventListener('click', handleSaveSkill);
  }

  if (factoryNewSkillFormBtn) {
    factoryNewSkillFormBtn.addEventListener('click', resetNewSkillForm);
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


  const factoryIntakeTalkToForgeBtn = $('factoryIntakeTalkToForgeBtn');
  if (factoryIntakeTalkToForgeBtn) {
    factoryIntakeTalkToForgeBtn.addEventListener('click', () => {
      const agentId = (factoryAgentSelect && factoryAgentSelect.value !== '__new__') ? factoryAgentSelect.value : '';
      const prompt = buildForgeInitialPrompt(agentId);
      if (typeof callbacks.switchTab === 'function') {
        callbacks.switchTab('chat');
      }
      const chatInput = $('chatInput');
      if (chatInput) {
        chatInput.value = prompt;
        chatInput.focus();
      }
    });
  }

  if (factoryRefreshBtn) {
    factoryRefreshBtn.addEventListener('click', async () => {
      showToast('Refreshing workshop capabilities...', 'info');
      await Promise.all([loadAgents(factoryAgentSelect ? factoryAgentSelect.value : null), loadCapabilities()]);
      showToast('Workshop refreshed!', 'success');
    });
  }

  // ----------------------------------------------------
  // Public Controller API
  // ----------------------------------------------------
  return {
    loadFactoryStudio: async (preferredAgentId = null) => {
      await Promise.all([loadAgents(preferredAgentId), loadCapabilities()]);
    },
    setAgentScope,
    stopPolling: () => {},
  };
}
