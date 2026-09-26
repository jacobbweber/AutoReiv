/**
 * Agent Studio: Quick Scaffold Submodule [CARD-197, CARD-218, CARD-398, CARD-496]
 * Manages quick agent pack presets and the scaffold modal. The self-scaffold candidate queue
 * ("Agent Training Optimization") was removed in CARD-496 (ADR-0060); its backend retires in CARD-512.
 */

import { $ } from '../../dom.js';
import { showToast } from '../../ui/toast.js';

export function startNewAgentPackFromStudio(callbacks = {}) {
  if (typeof callbacks.onStartNewAgentPack === 'function') {
    callbacks.onStartNewAgentPack();
    return true;
  }
  return false;
}

export const FORGE_QUICK_PRESETS = {
  'wiki-librarian': {
    id: 'wiki-librarian',
    name: 'Wiki Librarian',
    role: 'Knowledge Curator & Research Librarian',
    description: 'Specialist agent for wiki vault curation, structured note synthesis, taxonomy management, and template-guided knowledge capture.',
    avatar: 'book-open',
    tone: 'balanced',
    purpose: 'reasoning',
  },
  'sre-ops': {
    id: 'sre-ops',
    name: 'SRE Specialist',
    role: 'Kubernetes cluster administrator and pod diagnostician',
    description: 'Specialist agent for incident triage, telemetry inspection, and resilient operations.',
    avatar: 'terminal',
    tone: 'analytical',
    purpose: 'execution',
  },
};

/**
 * Construct a structured agent pack specification with gold-standard sections [CARD-197, REQ-FACT-047, CARD-269].
 */
export function buildQuickScaffoldPayload({
  id = '',
  name = '',
  description = '',
  role = '',
  avatar = 'bot',
  tone = 'balanced',
  purpose = 'general',
} = {}) {
  const cleanId = String(id || '').trim().toLowerCase().replace(/[^a-z0-9_-]/g, '-');
  const cleanName = String(name || '').trim() || cleanId;
  const cleanRole = String(role || '').trim() || cleanName;
  const cleanDesc = String(description || '').trim() || `Specialist agent for ${cleanRole}.`;

  const systemPrompt = [
    `[IDENTITY & ROLE]`,
    `You are ${cleanName}, a specialized AI agent focused on: ${cleanRole}.`,
    ``,
    `[DOMAIN BOUNDARIES & REFUSALS]`,
    `Focus strictly on ${cleanRole}. Refuse requests outside your authorized domain or refer them to other specialists.`,
    ``,
    `[EXECUTION PROTOCOL]`,
    `1. Inspect and read the current environment or state before making changes.`,
    `2. Formulate an explicit plan before executing commands or actions.`,
    `3. Validate all inputs and parameters defensively.`,
    `4. Verify completion and report clear outcomes with evidence.`,
    ``,
    `[SAFETY & APPROVALS]`,
    `Always require confirmation before executing destructive, mutating, or production operations. Use dry-runs where available.`,
    `HITL gates (REQUIRE_CONFIRM / Approve / Reject) are authoritative — never treat a toast or UI hint as approval.`,
    ``,
    `[TOOL USAGE RULES]`,
    `Invoke tools atomically and check return status codes. Handle failures gracefully with actionable diagnostic messages.`,
    `Only claim tool results you actually received this turn. Listed tools are capabilities, not proof of execution.`,
    `Never search the filesystem or use shell commands to hunt for Wiki vault files. Always use canonical wiki_* tools (wiki_template_list, wiki_note_read, wiki_note_search, wiki_note_create).`,
    ``,
    `[PROVENANCE & HONESTY]`,
    `Separate operator-visible facts (tool returns, job_id, wiki/repo reads) from inference.`,
    `When citing wiki or checkout files, name the source path or note id; do not invent contents.`,
    `On kill/resume and handoffs, keep the same job_id and report continuity honestly.`,
    ``,
    `[OUTPUT FORMAT]`,
    `Provide concise, structured markdown with clear checklists, diagnostic tables, or code snippets.`,
  ].join('\n');

  const primarySkillId = `${cleanId}-core`;

  return {
    id: cleanId,
    name: cleanName,
    description: cleanDesc,
    system_prompt: systemPrompt,
    tone: tone,
    purpose: purpose,
    avatar_icon: avatar,
    model: 'default',
    show_in_chat: true,
    skills: [
      {
        id: primarySkillId,
        name: `${cleanName} Core`,
        description: `Core operational capabilities and runbook for ${cleanName}.`,
        tools: [],
      },
    ],
  };
}

export function openQuickScaffoldModal() {
  const modal = $('forgeNewAgentModal');
  const presetSelect = $('forgeNewAgentPresetSelect');
  const idInput = $('forgeNewAgentIdInput');
  const nameInput = $('forgeNewAgentNameInput');
  const roleInput = $('forgeNewAgentRoleInput');
  const descInput = $('forgeNewAgentDescInput');
  if (!modal) return;
  if (presetSelect) presetSelect.value = '';
  if (idInput) idInput.value = '';
  if (nameInput) nameInput.value = '';
  if (roleInput) roleInput.value = '';
  if (descInput) descInput.value = '';
  modal.classList.remove('hidden');
  if (idInput) idInput.focus();
}

export function closeQuickScaffoldModal() {
  const modal = $('forgeNewAgentModal');
  if (modal) {
    modal.classList.add('hidden');
  }
}

/**
 * Wires Quick Scaffold Modal listeners.
 */
export function setupScaffold({
  callbacks = {},
  onLoadAgent = null,
} = {}) {
  const forgeNewAgentPresetSelect = $('forgeNewAgentPresetSelect');
  const forgeNewAgentIdInput = $('forgeNewAgentIdInput');
  const forgeNewAgentNameInput = $('forgeNewAgentNameInput');
  const forgeNewAgentRoleInput = $('forgeNewAgentRoleInput');
  const forgeNewAgentDescInput = $('forgeNewAgentDescInput');
  const forgeNewAgentAvatarSelect = $('forgeNewAgentAvatarSelect');
  const forgeNewAgentToneSelect = $('forgeNewAgentToneSelect');
  const forgeNewAgentPurposeSelect = $('forgeNewAgentPurposeSelect');
  const forgeQuickScaffoldBtn = $('forgeQuickScaffoldBtn');
  const forgeNewAgentCloseBtn = $('forgeNewAgentCloseBtn');
  const forgeNewAgentCancelBtn = $('forgeNewAgentCancelBtn');
  const forgeNewAgentChatInsteadBtn = $('forgeNewAgentChatInsteadBtn');
  const forgeNewAgentSubmitBtn = $('forgeNewAgentSubmitBtn');

  if (forgeNewAgentPresetSelect) {
    forgeNewAgentPresetSelect.addEventListener('change', () => {
      const presetKey = forgeNewAgentPresetSelect.value;
      const preset = FORGE_QUICK_PRESETS[presetKey];
      if (preset) {
        if (forgeNewAgentIdInput) forgeNewAgentIdInput.value = preset.id;
        if (forgeNewAgentNameInput) forgeNewAgentNameInput.value = preset.name;
        if (forgeNewAgentRoleInput) forgeNewAgentRoleInput.value = preset.role;
        if (forgeNewAgentDescInput) forgeNewAgentDescInput.value = preset.description;
        if (forgeNewAgentAvatarSelect) forgeNewAgentAvatarSelect.value = preset.avatar;
        if (forgeNewAgentToneSelect) forgeNewAgentToneSelect.value = preset.tone;
        if (forgeNewAgentPurposeSelect) forgeNewAgentPurposeSelect.value = preset.purpose;
      }
    });
  }

  if (forgeQuickScaffoldBtn) {
    forgeQuickScaffoldBtn.addEventListener('click', () => {
      openQuickScaffoldModal();
    });
  }

  if (forgeNewAgentCloseBtn) {
    forgeNewAgentCloseBtn.addEventListener('click', () => {
      closeQuickScaffoldModal();
    });
  }

  if (forgeNewAgentCancelBtn) {
    forgeNewAgentCancelBtn.addEventListener('click', () => {
      closeQuickScaffoldModal();
    });
  }

  if (forgeNewAgentChatInsteadBtn) {
    forgeNewAgentChatInsteadBtn.addEventListener('click', () => {
      closeQuickScaffoldModal();
      startNewAgentPackFromStudio(callbacks);
    });
  }

  if (forgeNewAgentSubmitBtn) {
    forgeNewAgentSubmitBtn.addEventListener('click', async () => {
      const id = forgeNewAgentIdInput ? forgeNewAgentIdInput.value.trim() : '';
      const name = forgeNewAgentNameInput ? forgeNewAgentNameInput.value.trim() : '';
      if (!id || !name) {
        showToast('Please provide both an Agent ID and Display Name.', 'warning');
        return;
      }
      const role = forgeNewAgentRoleInput ? forgeNewAgentRoleInput.value.trim() : '';
      const desc = forgeNewAgentDescInput ? forgeNewAgentDescInput.value.trim() : '';
      const avatar = forgeNewAgentAvatarSelect ? forgeNewAgentAvatarSelect.value : 'bot';
      const tone = forgeNewAgentToneSelect ? forgeNewAgentToneSelect.value : 'balanced';
      const purpose = forgeNewAgentPurposeSelect ? forgeNewAgentPurposeSelect.value : 'general';

      const payload = buildQuickScaffoldPayload({
        id,
        name,
        description: desc,
        role,
        avatar,
        tone,
        purpose,
      });

      try {
        forgeNewAgentSubmitBtn.disabled = true;
        const res = await fetch('/api/agents', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || 'Failed to scaffold agent pack');
        }
        closeQuickScaffoldModal();
        showToast(`Agent "${name}" pack created successfully!`, 'success');
        // CARD-496 D6: stay in Agent Studio with the new agent loaded (no Factory jump).
        if (typeof onLoadAgent === 'function') {
          await onLoadAgent(id);
        }
      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        forgeNewAgentSubmitBtn.disabled = false;
      }
    });
  }

  return {
    openQuickScaffoldModal,
    closeQuickScaffoldModal,
  };
}
