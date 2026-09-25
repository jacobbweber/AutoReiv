/**
 * Chat Studio: Agent Training Handshake Modal Controller [CARD-165, CARD-186, CARD-397]
 * Manages modal inputs, objective derivation, training job submission, and live lab links.
 */

import { $, $query, safeCreateIcons } from '../../dom.js';
import { escapeHtml } from '../../utils/formatters.js';
import { buildTrainAgentPayload, submitTrainAgentJob } from './training.js';

export function closeTrainModal({
  trainAgentHandshakeModal,
  trainAgentTargetSelect,
  trainAgentToggle,
  trainAgentBadge,
  state,
} = {}) {
  if (trainAgentHandshakeModal) {
    trainAgentHandshakeModal.classList.add('hidden');
    delete trainAgentHandshakeModal.dataset.agentId;
  }
  if (trainAgentTargetSelect && state?.agents && state.agents.length > 0) {
    trainAgentTargetSelect.value = state.selectedAgentId || state.agents[0].id;
  }
  const targetLoc = $('trainTargetLocation');
  if (targetLoc) targetLoc.value = '';
  const intentInput = $('trainSeedIntentInput');
  if (intentInput) intentInput.value = '';
  const seedObj = $('trainSeedObjectives');
  if (seedObj) seedObj.value = '';
  const nameInput = $('trainAgentNameInput');
  if (nameInput) nameInput.value = '';
  const deliverableSelect = $('trainDeliverableType');
  if (deliverableSelect) deliverableSelect.value = 'auto';
  const constraintsInput = $('trainConstraintsInput');
  if (constraintsInput) constraintsInput.value = '';
  const prereqsInput = $('trainPrerequisitesInput');
  if (prereqsInput) prereqsInput.value = '';
  const refDocsInput = $('trainReferenceDocsInput');
  if (refDocsInput) refDocsInput.value = '';
  const advContent = $('trainAdvancedReqsContent');
  if (advContent) advContent.classList.add('hidden');
  const chevron = $('trainAdvancedChevron');
  if (chevron) chevron.classList.remove('rotate-180');
  if (trainAgentToggle) trainAgentToggle.checked = false;
  if (trainAgentBadge) trainAgentBadge.classList.add('hidden');
}

export function setupTrainModal(elements, {
  state,
  promptInput = null,
  messagesContainer = null,
  showToastFn = null,
  maybeAutoscrollMessagesFn = null,
} = {}) {
  const {
    trainAgentHandshakeModal,
    trainAgentTargetSelect,
    trainAgentToggle,
    trainAgentBadge,
    closeTrainAgentModalBtn,
    cancelTrainAgentBtn,
    startTrainAgentBtn,
    trainTargetLocation,
    trainSeedObjectives,
    trainRequireApproval,
  } = elements;

  const toggleTrainAdvancedReqsBtn = $('toggleTrainAdvancedReqsBtn');
  if (toggleTrainAdvancedReqsBtn) {
    toggleTrainAdvancedReqsBtn.addEventListener('click', () => {
      const content = $('trainAdvancedReqsContent');
      const advChevron = $('trainAdvancedChevron');
      if (content) {
        const isHidden = content.classList.contains('hidden');
        content.classList.toggle('hidden', !isHidden);
        if (advChevron) {
          advChevron.classList.toggle('rotate-180', isHidden);
        }
      }
    });
  }

  const closeFn = () => closeTrainModal({
    trainAgentHandshakeModal,
    trainAgentTargetSelect,
    trainAgentToggle,
    trainAgentBadge,
    state,
  });

  if (closeTrainAgentModalBtn) {
    closeTrainAgentModalBtn.addEventListener('click', closeFn);
  }
  if (cancelTrainAgentBtn) {
    cancelTrainAgentBtn.addEventListener('click', closeFn);
  }

  if (startTrainAgentBtn) {
    startTrainAgentBtn.addEventListener('click', async () => {
      const selectedTargetValue = trainAgentTargetSelect ? trainAgentTargetSelect.value : null;
      const isNew = selectedTargetValue === '__new__';
      const explicitAgentId = (!isNew && selectedTargetValue)
        ? selectedTargetValue
        : (trainAgentHandshakeModal?.dataset?.agentId || null);
      const trainAgentNameInput = $('trainAgentNameInput');
      const customAgentName = trainAgentNameInput ? trainAgentNameInput.value.trim() : '';

      let targetAgentId = isNew ? null : explicitAgentId;
      const trainSeedIntentInput = $('trainSeedIntentInput');
      const explicitIntent = trainSeedIntentInput ? trainSeedIntentInput.value.trim() : '';
      let seedIntent = explicitIntent || (promptInput ? promptInput.value.trim() : '');

      const rawObjectives = trainSeedObjectives ? trainSeedObjectives.value.trim() : '';
      const objectives = rawObjectives
        ? rawObjectives.split('\n').map((s) => s.trim().replace(/^-\s*/, '')).filter(Boolean)
        : [];

      if (!targetAgentId && !customAgentName) {
        if (typeof showToastFn === 'function') {
          showToastFn('Please select a target agent to train.', 'warning');
        }
        return;
      }

      if (!targetAgentId && customAgentName) {
        targetAgentId = customAgentName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
        if (!seedIntent && objectives.length > 0) {
          seedIntent = objectives[0].length > 120 ? objectives[0].slice(0, 117) + '...' : objectives[0];
        } else if (!seedIntent) {
          seedIntent = `Train capabilities for ${customAgentName}`;
        }
      } else if (!seedIntent && objectives.length > 0) {
        seedIntent = objectives[0].length > 120 ? objectives[0].slice(0, 117) + '...' : objectives[0];
      } else if (!seedIntent && explicitAgentId) {
        const agentObj = (state?.agents || []).find((a) => a.id === explicitAgentId);
        seedIntent = (agentObj && agentObj.description) ? agentObj.description : `Train capabilities for ${explicitAgentId}`;
      } else if (!seedIntent) {
        seedIntent = 'Custom Specialist Agent';
      }

      const targetTypeInput = $query('input[name="trainTargetType"]');
      const targetType = targetTypeInput ? targetTypeInput.value : 'local';
      const targetLocation = trainTargetLocation ? trainTargetLocation.value.trim() : '';
      const requireApproval = trainRequireApproval ? trainRequireApproval.checked : true;

      const deliverableSelect = $('trainDeliverableType');
      const deliverableType = deliverableSelect ? deliverableSelect.value : 'auto';

      const constraintsInput = $('trainConstraintsInput');
      const constraints = constraintsInput ? constraintsInput.value.trim() : '';

      const prereqsInput = $('trainPrerequisitesInput');
      const prerequisites = prereqsInput ? prereqsInput.value.trim() : '';

      const refDocsInput = $('trainReferenceDocsInput');
      const referenceDocs = refDocsInput ? refDocsInput.value.trim() : '';

      const payload = buildTrainAgentPayload({
        seedIntent,
        targetType,
        targetLocation,
        objectives,
        requireApproval,
        sessionId: (state?.selectedAgentId === 'autoreiv' || !state?.selectedAgentId) ? state?.activeSessionId : null,
        targetAgentId,
        deliverableType,
        constraints,
        prerequisites,
        referenceDocs,
      });

      if (trainAgentHandshakeModal) {
        trainAgentHandshakeModal.classList.add('hidden');
        delete trainAgentHandshakeModal.dataset.agentId;
      }
      if (trainTargetLocation) trainTargetLocation.value = '';
      if (trainAgentNameInput) trainAgentNameInput.value = '';
      if (trainSeedObjectives) trainSeedObjectives.value = '';
      if (deliverableSelect) deliverableSelect.value = 'auto';
      if (constraintsInput) constraintsInput.value = '';
      if (prereqsInput) prereqsInput.value = '';
      if (refDocsInput) refDocsInput.value = '';
      startTrainAgentBtn.disabled = true;

      try {
        const result = await submitTrainAgentJob(payload);
        if (typeof showToastFn === 'function') {
          showToastFn(`Training Job ${result.job_id} initiated!`, 'success');
        }

        if (typeof window.openLabMonitorDrawer === 'function') {
          window.openLabMonitorDrawer(result.job_id);
        }

        if (messagesContainer) {
          const infoBubble = document.createElement('div');
          infoBubble.className = 'flex justify-start w-full';
          infoBubble.innerHTML = `
            <div class="max-w-4xl w-full rounded-2xl p-4 shadow-md bg-slate-900/90 border border-emerald-500/40 text-slate-100 rounded-bl-sm space-y-2">
              <div class="flex items-center justify-between">
                <div class="flex items-center space-x-2 text-emerald-400 font-semibold text-xs">
                  <i data-lucide="cpu" class="w-4 h-4"></i>
                  <span>Autonomous Factory Loop Started</span>
                </div>
                <button type="button" class="open-lab-drawer-btn text-xs text-emerald-400 hover:text-emerald-300 underline font-medium" data-job-id="${escapeHtml(result.job_id)}">
                  View in Lab Monitor &rarr;
                </button>
              </div>
              <p class="text-xs text-slate-300">Job <strong class="font-mono text-emerald-300">${escapeHtml(result.job_id)}</strong> queued for <strong class="font-mono">${escapeHtml(payload.target_agent_id || 'specialist')}</strong>.</p>
            </div>
          `;
          messagesContainer.appendChild(infoBubble);
          if (typeof maybeAutoscrollMessagesFn === 'function') {
            maybeAutoscrollMessagesFn();
          }
          safeCreateIcons();
        }
      } catch (err) {
        if (typeof showToastFn === 'function') {
          showToastFn(`Failed to start training loop: ${err.message}`, 'error');
        }
      } finally {
        startTrainAgentBtn.disabled = false;
      }
    });
  }

  return {
    closeTrainModal: closeFn,
  };
}
