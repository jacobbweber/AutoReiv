/**
 * Wiki Studio: Chat Message Export Submodule [REQ-FE-001, CARD-399]
 * Handles exporting chat message turns directly to Wiki Inbox notes.
 */

import { $ } from '../../dom.js';
import { showToast } from '../../ui/toast.js';

/**
 * Exports a chat message turn to a new note in the Wiki Inbox.
 * @param {object} state - Application state with selectedAgentId and activeSessionId.
 * @param {string} content - Markdown content of the message turn.
 */
export async function exportMessageToWiki(state = {}, content = '') {
  const activeAgentTitle = $('activeAgentTitle');
  const agentName = activeAgentTitle ? activeAgentTitle.textContent : 'Agent';
  const title = `${agentName} Note - ${new Date().toISOString().split('T')[0]}`;
  try {
    const res = await fetch('/api/export/wiki', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title,
        content,
        agent_id: state.selectedAgentId || 'assistant',
        session_id: state.activeSessionId,
        category: 'inbox',
        tags: ['single_note', state.selectedAgentId || 'assistant'],
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    showToast(`Saved note to Wiki Inbox at '${data.filename || title}'!`, 'success');
  } catch (err) {
    console.error('[AutoReiv UI] Failed to export message to wiki:', err);
    showToast('Failed to save note to Wiki', 'error');
  }
}
