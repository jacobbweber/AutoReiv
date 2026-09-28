/**
 * Chat Studio: card tool rows [CARD-563, CARD-564].
 * hand_off_card outcomes and review_card / finish_review results are read from git and the card by the tools;
 * they are shown as cards (the review packet collapsed, since it holds the diff).
 */

import { escapeHtml } from '../../utils/formatters.js';

function handOffRow(msg) {
  const refused = msg.content.startsWith('=== Hand-off refused');
  const el = document.createElement('div');
  el.className = 'flex justify-start w-full my-1.5';
  el.setAttribute('data-hand-off-outcome', refused ? 'refused' : 'outcome');
  el.innerHTML = `
    <div class="max-w-2xl w-full rounded-xl bg-indigo-950/40 border ${refused ? 'border-rose-500/40' : 'border-indigo-500/30'} p-3 text-xs text-indigo-100 shadow-sm">
      <div class="font-semibold mb-1 ${refused ? 'text-rose-300' : 'text-indigo-300'}">${refused ? 'Hand-off to Developer refused' : 'Hand-off to Developer'}</div>
      <pre class="whitespace-pre-wrap font-mono text-[11px] text-slate-200">${escapeHtml(msg.content)}</pre>
    </div>
  `;
  return el;
}

const REVIEW_LOOK = {
  refused: ['Review refused', 'border-rose-500/40', 'text-rose-300'],
  packet: ['Review packet (diff, commits, checks)', 'border-indigo-500/30', 'text-indigo-300'],
  done: ['Review: Done', 'border-emerald-500/40', 'text-emerald-300'],
  returned: ['Review: Returned to Developer', 'border-amber-500/40', 'text-amber-300'],
  other: ['Review', 'border-indigo-500/30', 'text-indigo-300'],
};

export function reviewKind(text) {
  if (/^=== (Review|Verdict) refused/.test(text)) return 'refused';
  if (text.startsWith('=== Review packet')) return 'packet';
  if (text.startsWith('=== Review Done')) return 'done';
  if (text.startsWith('=== Review Returned')) return 'returned';
  return 'other';
}

function reviewRow(msg) {
  const text = msg.content;
  const kind = reviewKind(text);
  const [title, border, color] = REVIEW_LOOK[kind];
  const body = `<pre class="whitespace-pre-wrap font-mono text-[11px] text-slate-200">${escapeHtml(text)}</pre>`;
  const inner = kind === 'packet'
    ? `<details><summary class="cursor-pointer text-slate-300">${escapeHtml(text.split('\n')[0])}</summary>${body}</details>`
    : body;
  const el = document.createElement('div');
  el.className = 'flex justify-start w-full my-1.5';
  el.setAttribute('data-card-review', kind);
  el.innerHTML = `
    <div class="max-w-2xl w-full rounded-xl bg-indigo-950/40 border ${border} p-3 text-xs text-indigo-100 shadow-sm">
      <div class="font-semibold mb-1 ${color}">${title}</div>
      ${inner}
    </div>
  `;
  return el;
}

/** Append the card row for a hand-off or review tool message; returns true when it handled the message. */
export function renderCardToolRow(msg, container) {
  if (!msg || typeof msg.content !== 'string' || !container) return false;
  let el = null;
  if (msg.name === 'hand_off_card' && msg.content.startsWith('=== Hand-off')) el = handOffRow(msg);
  else if ((msg.name === 'review_card' || msg.name === 'finish_review') && msg.content.startsWith('=== ')) el = reviewRow(msg);
  if (!el) return false;
  container.appendChild(el);
  return true;
}
