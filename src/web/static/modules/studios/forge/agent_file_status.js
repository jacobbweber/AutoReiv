/**
 * Agent Studio: agent file status [CARD-570].
 * Agents are files: a shipped agent you edit gets a user copy that wins. This shows "Edited",
 * the "shipped version changed" note, and Use shipped version (deletes the copy; model settings stay).
 */

import { $ } from '../../dom.js';
import { showToast } from '../../ui/toast.js';

export function agentFileStatusText(status) {
  if (!status || !status.shipped) return '';
  if (!status.edited) return 'Shipped agent. Saving here keeps your own copy of it.';
  return 'Edited: you are using your own copy of this shipped agent.';
}

export function setupAgentFileStatus({ onAgentRefreshed = null, fetchImpl = null } = {}) {
  const doFetch = fetchImpl || ((...args) => fetch(...args));
  let current = null;

  function render(agent) {
    current = agent || null;
    const box = $('forgeAgentFileStatus');
    if (!box) return;
    const status = (agent && agent.file_status) || null;
    const text = agentFileStatusText(status);
    box.classList.toggle('hidden', !text);
    const textEl = $('forgeAgentFileText');
    if (textEl) textEl.textContent = text;
    const changed = $('forgeAgentFileChanged');
    if (changed) changed.classList.toggle('hidden', !(status && status.shipped_changed));
    const btn = $('forgeUseShippedBtn');
    if (btn) btn.classList.toggle('hidden', !(status && status.edited));
  }

  async function useShipped() {
    if (!current || !current.id) return;
    if (typeof window !== 'undefined' && window.confirm
      && !window.confirm('Use the shipped version of this agent? Your copy is deleted. Model and provider settings stay.')) {
      return;
    }
    const res = await doFetch(`/api/agents/${encodeURIComponent(current.id)}/use-shipped`, { method: 'POST' });
    if (!res.ok) {
      showToast('Could not switch to the shipped version.', 'error');
      return;
    }
    const body = await res.json();
    showToast('Using the shipped version.', 'success');
    if (body.agent && typeof onAgentRefreshed === 'function') onAgentRefreshed(body.agent);
  }

  const btn = $('forgeUseShippedBtn');
  if (btn) btn.addEventListener('click', () => { useShipped(); });

  return { render, useShipped };
}
