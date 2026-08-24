/**
 * Shared Application State Store [REQ-FE-001]
 */

export const state = {
  activeTab: 'chat',
  agents: [],
  selectedAgentId: 'general-assistant',
  sessions: [],
  activeSessionId: null,
  messages: [],
  isStreaming: false,
  verifyEnabled: false,
  goalEnabled: false,
  currentVault: null,
  activeDoc: null,
};
