/**
 * Tools Studio intent form helpers [CARD-422].
 * Talk opens a developer chat. Submit runs a developer turn.
 * A queued or empty mediation result is not success.
 */

import { readableError } from '../utils/formatters.js';

export const DEVELOPER_AGENT_ID = 'developer';
export const TOOLS_AUTHORING_JOBS_URL = '/api/tools_studio/authoring/jobs';
export const TOOLS_AUTHORING_TALK_URL = '/api/tools_studio/authoring/talk';
export const PACKET_SCHEMA = 'tools_studio_authoring_packet';

const INTENTS = new Set(['create', 'modify', 'delete']);
const PACKAGING = new Set(['', 'native', 'mcp']);
const CODE_KEYS = ['code', 'implementation', 'source_code', 'script'];

/** Same readable sentence as Teach/Adopt; one helper for string, object and 422-list details [CARD-500]. */
export function authoringErrorMessage(data, status) {
  return readableError(data, status);
}

export function normalizeToolIntentDraft(raw = {}) {
  const source = raw && typeof raw === 'object' ? raw : {};
  for (let i = 0; i < CODE_KEYS.length; i += 1) {
    if (String(source[CODE_KEYS[i]] || '').trim()) {
      throw new Error('Tools Studio does not accept tool implementation code. Describe what the tool should do.');
    }
  }
  const intent = String(source.intent || 'create').trim().toLowerCase();
  const packaging = String(source.packaging_preference || '').trim().toLowerCase();
  return {
    intent: INTENTS.has(intent) ? intent : 'create',
    tool_name: String(source.tool_name || '').trim(),
    behavior: String(source.behavior || '').trim(),
    language_hint: String(source.language_hint || '').trim(),
    runtime_hint: String(source.runtime_hint || '').trim(),
    path_context: String(source.path_context || '').trim(),
    packaging_preference: PACKAGING.has(packaging) ? packaging : '',
  };
}

export function intentValidationError(draft) {
  const clean = normalizeToolIntentDraft(draft);
  if ((clean.intent === 'modify' || clean.intent === 'delete') && !clean.tool_name) {
    return 'Name the tool to modify or delete.';
  }
  if ((clean.intent === 'create' || clean.intent === 'modify') && !clean.behavior) {
    return 'Describe what the tool should do.';
  }
  return '';
}

export function interpretAuthoringTalk(data, draft = {}) {
  if (!data || data.opened_job || data.job_id) {
    throw new Error('Talk must open a developer chat without starting a job.');
  }
  const sessionId = String(data.session_id || '').trim();
  if (!sessionId) throw new Error('Developer chat session was empty.');
  if (data.agent_id && data.agent_id !== DEVELOPER_AGENT_ID) {
    throw new Error('Talk must open the developer agent.');
  }
  const prompt = String(data.prompt || '');
  if (!prompt.trim()) throw new Error('Developer chat is missing the tool intent.');
  const behavior = String((draft && draft.behavior) || '').trim();
  const toolName = String((draft && draft.tool_name) || '').trim();
  if (behavior && !prompt.includes(behavior)) {
    throw new Error('Developer chat is missing the tool intent.');
  }
  if (toolName && !prompt.includes(toolName)) {
    throw new Error('Developer chat is missing the tool name.');
  }
  return {
    sessionId,
    agentId: DEVELOPER_AGENT_ID,
    prompt,
    openedJob: false,
    jobId: null,
  };
}

export function interpretAuthoringSubmit(data) {
  const status = String((data && data.status) || '').trim().toLowerCase();
  const jobId = String((data && data.job_id) || '').trim();
  const sessionId = String((data && data.session_id) || '').trim();
  const ran = Boolean(data && data.ran === true && data.queued_only !== true && data.mediation === 'developer_turn');
  if (!jobId || !sessionId || !ran || !status || status === 'queued' || status === 'failed' || status === 'cancelled') {
    throw new Error('Developer mediation did not run.');
  }
  if (data.persisted_tool || data.packaging_applied) {
    throw new Error('Tools Studio must not apply tool packaging from this form.');
  }
  const reply = String(data.reply || '').trim();
  if (!reply) throw new Error('Developer mediation returned an empty reply.');
  return {
    jobId,
    sessionId,
    agentId: data.agent_id || DEVELOPER_AGENT_ID,
    status,
    reply,
    prompt: String(data.prompt || ''),
    packet: data.packet || null,
    ran: true,
    queuedOnly: false,
    persistedTool: false,
    packagingApplied: false,
  };
}
