/**
 * Chat Studio: Ask Developer real send [CARD-497 REQ-497-016]
 * Gap Ask Developer, Tools Studio Talk and Teach "Ask Developer to build this tool" open a new Developer
 * session (POST /api/tools_studio/authoring/talk). The intent is sent here as a real turn, as if the
 * operator typed it and pressed Enter: once, never while the chat is busy, never again on reopen.
 */

const inFlight = new Set();
const NEEDLE_LEN = 80;

function alreadyInHistory(messages, text) {
  const needle = text.slice(0, NEEDLE_LEN);
  return (messages || []).some((msg) => String((msg && msg.content) || '').includes(needle));
}

/**
 * @returns {{status: 'none'|'already-sent'|'busy'|'sent', done: Promise<void>}}
 */
export function sendDeveloperIntent({ sessionId, prompt, state, send, fillComposer = null, toast = null } = {}) {
  const id = String(sessionId || '').trim();
  const text = String(prompt || '').trim();
  const idle = Promise.resolve();
  if (!id || !text || typeof send !== 'function') return { status: 'none', done: idle };
  const st = state || {};
  // Reopened session, another device, or a legacy session whose intent was pre-saved: it was already sent.
  if (inFlight.has(id) || alreadyInHistory(st.messages, text)) return { status: 'already-sent', done: idle };
  if (st.isStreaming || st.sessionBusy) {
    if (typeof fillComposer === 'function') fillComposer(text);
    if (typeof toast === 'function') toast('Developer is busy. The request is in the message box; press Send when the reply finishes.', 'warning');
    return { status: 'busy', done: idle };
  }
  inFlight.add(id);
  let done;
  try {
    done = Promise.resolve(send(text));
  } catch (err) {
    done = Promise.reject(err);
  }
  done = done.catch(() => {}).finally(() => inFlight.delete(id));
  return { status: 'sent', done };
}
