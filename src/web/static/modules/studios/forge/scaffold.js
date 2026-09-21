/**
 * Agent Studio: Quick Scaffold & Candidate Queue Submodule [CARD-197, CARD-218, CARD-251, CARD-304, CARD-398]
 * Manages quick agent pack presets, scaffold modal, self-scaffold candidate queue,
 * approval actions, and same-job origin resumption.
 */

import { $ } from '../../dom.js';
import { escapeHtml } from '../../utils/formatters.js';
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
    `Never search the filesystem or use shell commands to hunt for Wiki vault files. Always use canonical wiki_* tools (list_wiki_templates, wiki_note_read, wiki_note_search, wiki_note_create).`,
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

export async function resumeOriginAfterForgeApprove(data, callbacks = {}) {
  const jobId = data && data.job_id ? String(data.job_id) : '';
  const sessionId = data && data.session_id ? String(data.session_id) : '';
  if (!jobId) return;
  try {
    const chat = typeof callbacks.getChatCtrl === 'function' ? callbacks.getChatCtrl() : null;
    if (chat && sessionId && typeof chat.selectSession === 'function') {
      await chat.selectSession(sessionId);
    }
    if (chat && typeof chat.resumeParkedJob === 'function') {
      await chat.resumeParkedJob();
    }
    if (typeof callbacks.switchTab === 'function') {
      callbacks.switchTab('chat');
    }
    const obs = typeof callbacks.getObsCtrl === 'function' ? callbacks.getObsCtrl() : null;
    const input = $('standingJourneyJobIdInput');
    if (input) input.value = jobId;
    if (obs && typeof obs.loadStandingJourney === 'function') {
      await obs.loadStandingJourney();
    }
  } catch (err) {
    console.warn('CARD-251 origin resume after Forge Approve soft-fail:', err);
  }
}

export async function loadForgeScaffoldQueue() {
  const statusEl = $('forgeScaffoldStatus');
  const body = $('forgeScaffoldQueueBody');
  if (!body) return;
  if (statusEl) statusEl.textContent = 'Loading candidates...';
  try {
    const res = await fetch('/api/capabilities/scaffold/candidates?limit=50');
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to load candidates');
    const rows = data.candidates || [];
    if (!rows.length) {
      body.innerHTML = '<tr><td colspan="5" class="p-2 text-slate-500">No candidates in queue.</td></tr>';
    } else {
      body.innerHTML = rows.map((r) => {
        const id = escapeHtml(r.id || '');
        const name = escapeHtml(r.name || r.pack_id || '');
        const phase = escapeHtml(r.phase || '');
        const trust = escapeHtml(r.trust_tier || '');
        const sand = r.sandboxed ? 'yes' : 'no';
        return `<tr data-scaffold-id="${id}">
          <td class="p-2">${name}</td>
          <td class="p-2 font-mono">${phase}</td>
          <td class="p-2">${trust}</td>
          <td class="p-2">${sand}</td>
          <td class="p-2 space-x-1">
            <button type="button" data-scaffold-action="sandbox" data-id="${id}" class="px-1.5 py-0.5 rounded bg-amber-800/60 hover:bg-amber-700 text-[10px] text-amber-100 border border-amber-700/50">Sandbox</button>
            <button type="button" data-scaffold-action="version" data-id="${id}" class="px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] text-slate-200 border border-slate-700">Version</button>
            <button type="button" data-scaffold-action="approve" data-id="${id}" class="px-1.5 py-0.5 rounded bg-emerald-800/60 hover:bg-emerald-700 text-[10px] text-emerald-100 border border-emerald-700/50">Approve</button>
            <button type="button" data-scaffold-action="rollback" data-id="${id}" class="px-1.5 py-0.5 rounded bg-slate-800 hover:bg-rose-950/50 text-[10px] text-slate-300 border border-slate-700">Rollback</button>
          </td>
        </tr>`;
      }).join('');
    }
    if (statusEl) statusEl.textContent = `Queue: ${rows.length} candidate(s). forge_queue=${!!data.forge_queue}`;
  } catch (err) {
    if (statusEl) statusEl.textContent = `Error: ${err.message || err}`;
    body.innerHTML = `<tr><td colspan="5" class="p-2 text-rose-400">${escapeHtml(String(err.message || err))}</td></tr>`;
  }
}

export async function runForgeScaffoldAction(action, id, callbacks = {}) {
  const statusEl = $('forgeScaffoldStatus');
  const paths = {
    sandbox: `/api/capabilities/scaffold/${encodeURIComponent(id)}/sandbox`,
    version: `/api/capabilities/scaffold/${encodeURIComponent(id)}/version`,
    approve: `/api/capabilities/scaffold/${encodeURIComponent(id)}/approve`,
    rollback: `/api/capabilities/scaffold/${encodeURIComponent(id)}/rollback`,
  };
  const url = paths[action];
  if (!url) return;
  try {
    if (statusEl) statusEl.textContent = `${action}...`;
    const opts = { method: 'POST', headers: { 'Content-Type': 'application/json' } };
    if (action === 'sandbox') opts.body = JSON.stringify({ evidence: 'forge-ui-sandbox' });
    const res = await fetch(url, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `${action} failed`);
    // CARD-251: Forge Approve resumes same job_id / origin session (no orphan).
    if (action === 'approve' && data && data.resumed && data.job_id) {
      showToast(`Approved — resumed same job ${data.job_id}`, 'success');
      if (statusEl) {
        statusEl.textContent = `Approved. Resumed same job_id=${data.job_id} (origin session; no orphan).`;
      }
      await resumeOriginAfterForgeApprove(data, callbacks);
    } else {
      showToast(`Scaffold ${action} ok`, 'success');
    }
    await loadForgeScaffoldQueue();
  } catch (err) {
    showToast(String(err.message || err), 'error');
    if (statusEl) statusEl.textContent = `Error: ${err.message || err}`;
  }
}

/**
 * Wires Quick Scaffold Modal and Candidate Queue listeners.
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
        if (typeof onLoadAgent === 'function') {
          await onLoadAgent(id);
        }
        if (typeof callbacks.openFactoryStudio === 'function') {
          callbacks.openFactoryStudio(id);
        } else if (typeof window !== 'undefined' && typeof window.openFactoryStudioForAgent === 'function') {
          window.openFactoryStudioForAgent(id);
        }
      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        forgeNewAgentSubmitBtn.disabled = false;
      }
    });
  }

  const forgeScaffoldRefreshBtn = $('forgeScaffoldRefreshBtn');
  if (forgeScaffoldRefreshBtn) {
    forgeScaffoldRefreshBtn.addEventListener('click', () => {
      loadForgeScaffoldQueue();
    });
  }

  const forgeScaffoldQueueBody = $('forgeScaffoldQueueBody');
  if (forgeScaffoldQueueBody) {
    forgeScaffoldQueueBody.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-scaffold-action]');
      if (!btn) return;
      const action = btn.getAttribute('data-scaffold-action');
      const id = btn.getAttribute('data-id');
      if (action && id) runForgeScaffoldAction(action, id, callbacks);
    });
  }

  const forgeScaffoldOpenFactoryBtn = $('forgeScaffoldOpenFactoryBtn');
  const forgeIdInput = $('forgeIdInput');
  const forgeTrainAgentBtn = $('forgeTrainAgentBtn');
  if (forgeScaffoldOpenFactoryBtn && !forgeScaffoldOpenFactoryBtn.dataset.card304Bound) {
    forgeScaffoldOpenFactoryBtn.dataset.card304Bound = '1';
    forgeScaffoldOpenFactoryBtn.addEventListener('click', () => {
      const currentAgentId = forgeIdInput ? forgeIdInput.value.trim() : '';
      if (typeof callbacks.openFactoryStudio === 'function') {
        callbacks.openFactoryStudio(currentAgentId);
      } else if (typeof window !== 'undefined' && typeof window.openFactoryStudioForAgent === 'function') {
        window.openFactoryStudioForAgent(currentAgentId);
      } else if (forgeTrainAgentBtn) {
        forgeTrainAgentBtn.click();
      }
    });
  }

  return {
    openQuickScaffoldModal,
    closeQuickScaffoldModal,
    loadForgeScaffoldQueue,
    runForgeScaffoldAction,
  };
}
