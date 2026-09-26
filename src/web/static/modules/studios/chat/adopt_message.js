/**
 * Teach > Adopt result text [CARD-502 REQ-502-004..006].
 * The message is built from the server answer, never assumed.
 */
import { readableError } from '../../utils/formatters.js';

/** Returns { text, type } for the toast and card; throws when the agent did not pick the skill up. */
export function adoptResultMessage(data, status, skillName, agent) {
  if (status < 200 || status >= 300) throw new Error(readableError(data, status));
  if (!data || !data.active) throw new Error(`${agent} did not pick up ${skillName}. Open Agent Studio, tick it, and save.`);
  const text = data.already_adopted
    ? `Updated ${skillName} for ${agent}. It is used from your next message.`
    : `${skillName} is on for ${agent} from your next message.`;
  if (!data.resets_on_restart) return { text, type: 'success' };
  return { text: `${text} Keep my agent customizations is off, so it will be removed on the next restart.`, type: 'warning' };
}

/** Green banner that replaces the Adopt buttons; innerHtml must already be escaped. */
export function adoptedBannerHtml(innerHtml) {
  return `<div class="p-2.5 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-xs text-emerald-300 font-medium w-full">${innerHtml}</div>`;
}
