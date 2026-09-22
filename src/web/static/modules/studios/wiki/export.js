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

/**
 * Exports the full chat thread to a Wiki Inbox note [CARD-415].
 * @param {object} state - Application state with messages, selectedAgentId, activeSessionId.
 * @param {string|null} sessionId - Optional session id override.
 */
export async function exportSessionToWiki(state = {}, sessionId = null) {
  const messages = Array.isArray(state.messages) ? state.messages : [];
  const exportable = messages.filter((m) => m && String(m.content || '').trim());
  if (!exportable.length) {
    showToast('No messages to export', 'warning');
    return;
  }
  const activeAgentTitle = $('activeAgentTitle');
  const agentName = activeAgentTitle ? activeAgentTitle.textContent : 'Agent';
  const agentId = state.selectedAgentId || 'assistant';
  const sid = sessionId || state.activeSessionId || null;
  const title = `${agentName} Chat - ${new Date().toISOString().split('T')[0]}`;
  try {
    const res = await fetch('/api/export/wiki', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title,
        messages: exportable.map((m) => ({
          role: m.role || 'user',
          content: m.content || '',
          name: m.name || undefined,
        })),
        agent_id: agentId,
        session_id: sid,
        category: 'inbox',
        tags: ['chat_thread', agentId],
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    showToast(`Saved conversation to Wiki Inbox at '${data.filename || title}'!`, 'success');
  } catch (err) {
    console.error('[AutoReiv UI] Failed to export session to wiki:', err);
    showToast('Failed to save conversation to Wiki', 'error');
  }
}
