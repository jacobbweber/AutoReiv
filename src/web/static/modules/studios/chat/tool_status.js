/**
 * Chat Studio: what a tool row says happened [CARD-477].
 * A tool row used to print a green "Complete" for every tool message, even an approval park or an error.
 * Pure: reads the saved tool message (and, for a park, whether a later row for the same call holds the decision).
 */

const PARK_PREFIX = /^\s*Tool Error:\s*approval_required:/i;
const ERROR_PREFIX = /^\s*Tool Error:/i;
const NOT_RUN_PREFIX = /^\s*Not run:/i;
const REJECTED = /^\s*Rejected\b/i;

export const TOOL_ROW_STATUS = {
  waiting: { key: 'waiting', label: '\u23F3 Waiting for approval', cls: 'text-amber-400' },
  asked: { key: 'asked', label: 'Asked for approval', cls: 'text-slate-400' },
  rejected: { key: 'rejected', label: '\u2715 Rejected', cls: 'text-rose-400' },
  failed: { key: 'failed', label: '\u2715 Failed', cls: 'text-rose-400' },
  notRun: { key: 'notRun', label: 'Not run', cls: 'text-slate-400' },
  complete: { key: 'complete', label: '\u2713 Complete', cls: 'text-emerald-400' },
};

function parseJson(text) {
  const t = String(text || '').trim();
  if (!t.startsWith('{')) return null;
  try {
    const v = JSON.parse(t);
    return v && typeof v === 'object' && !Array.isArray(v) ? v : null;
  } catch {
    return null;
  }
}

/** The status key for one tool message's content. */
export function toolContentStatus(content) {
  const text = String(content ?? '');
  if (PARK_PREFIX.test(text)) return 'waiting';
  if (/^\s*(Tool Error:\s*)?tool_policy_blocked/i.test(text) || ERROR_PREFIX.test(text)) return 'failed';
  if (NOT_RUN_PREFIX.test(text)) return 'notRun';
  if (REJECTED.test(text)) return 'rejected';
  const data = parseJson(text);
  if (data) {
    const status = String(data.status || '').toLowerCase();
    if (status === 'parked' || status === 'approval_required' || status === 'pending_approval') return 'waiting';
    if (status === 'rejected') return 'rejected';
    if (data.success === false || status === 'error' || status === 'failed') return 'failed';
  }
  return 'complete';
}

/** True when a later tool row answers the same call (the approval was decided). */
function laterRowForCall(msg, idx, allMessages) {
  const callId = msg && msg.tool_call_id;
  if (!callId || !Array.isArray(allMessages)) return false;
  for (let i = (Number(idx) || 0) + 1; i < allMessages.length; i += 1) {
    const m = allMessages[i];
    if (m && String(m.role || '').toLowerCase() === 'tool' && m.tool_call_id === callId) return true;
  }
  return false;
}

/** { key, label, cls } for the row of tool message `msg` at `idx` in `allMessages`. */
export function toolRowStatus(msg, idx = 0, allMessages = null) {
  let key = toolContentStatus(msg && msg.content);
  if (key === 'waiting' && laterRowForCall(msg, idx, allMessages)) key = 'asked';
  return TOOL_ROW_STATUS[key];
}
