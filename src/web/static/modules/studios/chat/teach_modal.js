/**
 * Chat Studio: Teach Agent modal [CARD-352, REQ-SKIL-011, CARD-472]
 * Opens the Teach modal, distills a skill runbook, and sends needs-tool proposals to the Developer.
 */

import { $, safeCreateIcons } from '../../dom.js';
import { renderSkillProposalCard } from './render.js';
import { readableError } from '../../utils/formatters.js';
import { TOOLS_AUTHORING_TALK_URL, authoringErrorMessage, interpretAuthoringTalk } from '../tools_studio_authoring.js';

function readEscalation(card) {
  try {
    return JSON.parse((card && card.getAttribute('data-factory-escalation')) || '{}') || {};
  } catch {
    return {};
  }
}

/** Draft for the Developer chat, built from the proposal card [CARD-472 REQ-472-007]. */
export function buildDeveloperToolDraft(esc = {}, agentId = '') {
  const objectives = (Array.isArray(esc.starter_objectives) ? esc.starter_objectives : [])
    .map((o) => String(o || '').trim()).filter(Boolean);
  const lines = [String(esc.seed_intent || '').trim()].filter(Boolean);
  if (objectives.length) lines.push(`Objectives:\n${objectives.map((o) => `- ${o}`).join('\n')}`);
  if (agentId) lines.push(`Requested from a Teach proposal for ${agentId}.`);
  return { intent: 'create', tool_name: String(esc.suggested_tool_name || '').trim(), behavior: lines.join('\n\n') };
}

export function setupTeachAgentModal(state, elements = {}, {
  showToastFn, callbacks = {}, messagesContainer, fetchFn = null, openDeveloperSessionFn = null,
} = {}) {
  const getEl = (key) => elements[key] || $(key);
  const teachAgentModal = getEl('teachAgentModal');
  const teachAgentTargetAgentBadge = getEl('teachAgentTargetAgentBadge');
  const teachAgentGuidanceInput = getEl('teachAgentGuidanceInput');
  const submitTeachAgentBtn = getEl('submitTeachAgentBtn');
  const cancelTeachAgentBtn = getEl('cancelTeachAgentBtn');
  const closeTeachAgentModalBtn = getEl('closeTeachAgentModalBtn');

  const showToast = showToastFn || (() => {});
  const doFetch = (...args) => (fetchFn || globalThis.fetch)(...args);
  let activeTeachMessageId = null;
  let activeTeachTargetAgentId = null;

  const NO_REPLY = 'Send a message first, then teach from the reply.'; // CARD-500 REQ-500-004

  function openTeachAgentModal(opts = {}) {
    if (!opts.messageId) {
      showToast(NO_REPLY, 'warning');
      return;
    }
    activeTeachMessageId = opts.messageId;
    activeTeachTargetAgentId = opts.targetAgentId || state.selectedAgentId || 'autoreiv';
    if (teachAgentTargetAgentBadge) teachAgentTargetAgentBadge.textContent = activeTeachTargetAgentId;
    if (teachAgentGuidanceInput) teachAgentGuidanceInput.value = opts.guidance || '';
    if (teachAgentModal) {
      teachAgentModal.classList.remove('hidden');
      teachAgentModal.classList.add('flex');
    }
    safeCreateIcons();
  }

  function closeTeachAgentModal() {
    activeTeachMessageId = null;
    activeTeachTargetAgentId = null;
    if (teachAgentGuidanceInput) teachAgentGuidanceInput.value = '';
    if (teachAgentModal) {
      teachAgentModal.classList.add('hidden');
      teachAgentModal.classList.remove('flex');
    }
  }

  if (cancelTeachAgentBtn) cancelTeachAgentBtn.addEventListener('click', closeTeachAgentModal);
  if (closeTeachAgentModalBtn) closeTeachAgentModalBtn.addEventListener('click', closeTeachAgentModal);

  if (submitTeachAgentBtn) {
    submitTeachAgentBtn.addEventListener('click', async () => {
      const targetAgent = activeTeachTargetAgentId || state.selectedAgentId || 'autoreiv';
      const guidance = teachAgentGuidanceInput ? teachAgentGuidanceInput.value.trim() : '';
      const messageId = activeTeachMessageId;
      if (!messageId) {
        showToast(NO_REPLY, 'warning');
        return;
      }
      submitTeachAgentBtn.disabled = true;
      submitTeachAgentBtn.textContent = 'Distilling...';
      try {
        const res = await doFetch('/api/skills/distill', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          // CARD-500 REQ-500-001: the exact fields the server reads (D1, D2)
          body: JSON.stringify({ session_id: state.activeSessionId, message_id: messageId, guidance }),
        });
        if (!res.ok) throw new Error(readableError(await res.json().catch(() => ({})), res.status));
        const proposal = await res.json();
        closeTeachAgentModal();
        renderSkillProposalCard(proposal, {
          container: messagesContainer,
          activeAgentId: targetAgent,
          sessionId: state.activeSessionId,
          showToastFn: showToast,
          callbacks,
        });
      } catch (err) {
        showToast(`Distillation failed: ${err.message}`, 'error');
      } finally {
        submitTeachAgentBtn.disabled = false;
        submitTeachAgentBtn.textContent = 'Distill Skill Runbook';
      }
    });
  }

  // Needs-tool proposal: open a Developer chat with the proposal attached; Tools Studio if that fails.
  async function askDeveloperToBuildTool(card) {
    const esc = readEscalation(card);
    const agent = esc.target_agent_id || card.getAttribute('data-target-agent-id') || state.selectedAgentId || 'autoreiv';
    const draft = buildDeveloperToolDraft(esc, agent);
    try {
      const res = await doFetch(TOOLS_AUTHORING_TALK_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intent: 'create', draft }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(authoringErrorMessage(data, res.status));
      const plan = interpretAuthoringTalk(data, draft);
      if (typeof openDeveloperSessionFn !== 'function') throw new Error('Developer chat is unavailable here.');
      await openDeveloperSessionFn(plan.sessionId, plan.prompt);
    } catch (err) {
      showToast(`Could not open a Developer chat: ${err.message || err}. Opening Tools Studio.`, 'error');
      if (typeof callbacks.openToolsStudio === 'function') callbacks.openToolsStudio(agent);
    }
  }

  if (messagesContainer && !messagesContainer.dataset.teachEscalateBound) {
    messagesContainer.dataset.teachEscalateBound = '1';
    messagesContainer.addEventListener('click', (ev) => {
      const btn = ev.target && typeof ev.target.closest === 'function' ? ev.target.closest('.btn-escalate-factory') : null;
      const card = btn ? btn.closest('.skill-proposal-card') : null;
      if (!card || btn.disabled) return;
      btn.disabled = true;
      askDeveloperToBuildTool(card).finally(() => { btn.disabled = false; });
    });
  }

  return { openTeachAgentModal, closeTeachAgentModal };
}
