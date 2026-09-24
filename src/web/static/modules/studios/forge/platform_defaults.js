/**
 * Agent Studio: Platform defaults section [CARD-450].
 * Badge for skipped or partial platform updates, one Reset to platform defaults button,
 * and the per-agent backups list with Restore. Consumes the existing pack APIs only.
 */

import { $, safeCreateIcons } from '../../dom.js';
import { escapeHtml } from '../../utils/formatters.js';
import { showToast } from '../../ui/toast.js';
import { closeModal, openModal, setupModal } from '../../ui/modal.js';

const FIELD_WORDS = {
  system_prompt: 'system prompt',
  allowed_skill: 'skill list',
  pack_tool_names: 'tool list',
  allowed_tool_names: 'tool list',
  max_turns: 'max turns',
  model: 'model',
};

const BADGE_STATUSES = new Set(['skipped_user_modified', 'promoted_partial']);

/** Replaced on reset: mirrors promote_one_platform_pack force-reset path. */
export const RESET_REPLACED = [
  'System prompt (instructions)',
  'Skill files that ship with this agent (retired platform skills are removed)',
  'Which skills are on (skills you turned off come back on)',
  'Platform tool list',
];

/** Kept on reset: max turns/model are preserved; promotion never touches the rest. */
export const RESET_KEPT = [
  'Max turns',
  'Model',
  'Provider, API settings, and context window',
  'Name, description, tone, memory, storage, and Show in Chat',
  'Credentials and MCP servers',
  'Skill folders you created yourself',
];

export function humanizePackField(field) {
  const key = String(field || '').trim();
  return FIELD_WORDS[key] || key.replace(/_/g, ' ');
}

function joinWords(words) {
  const unique = [...new Set(words.filter(Boolean))];
  if (unique.length <= 1) return unique[0] || '';
  return `${unique.slice(0, -1).join(', ')} and ${unique[unique.length - 1]}`;
}

export function platformSyncEntryFor(report, agentId) {
  if (!report || !Array.isArray(report.results) || !agentId) return null;
  return report.results.find((r) => r && r.pack_id === agentId) || null;
}

/**
 * Badge for the agent's last sync outcome, or null when it is up to date [REQ-450-007].
 * @returns {{text: string, hint: string} | null}
 */
export function platformUpdateBadge(entry) {
  if (!entry || !BADGE_STATUSES.has(entry.status)) return null;
  const hint = 'Use Reset to platform defaults to take the platform version. A backup is saved first.';
  if (entry.status === 'promoted_partial') {
    const kept = joinWords((entry.skipped_fields || []).map(humanizePackField));
    const text = kept
      ? `Platform update partly applied. Kept your edited ${kept}.`
      : 'Platform update partly applied. Some of your edits were kept.';
    return { text, hint };
  }
  const reason = String(entry.reason || '');
  const text = reason.startsWith('cutover')
    ? "Platform update skipped because this agent's instructions, skills, or tools were customized."
    : 'Platform update skipped because the system prompt was edited.';
  return { text, hint };
}

export function formatBackupTime(iso) {
  const raw = String(iso || '');
  const d = raw ? new Date(raw) : null;
  if (!d || Number.isNaN(d.getTime())) return { label: 'Unknown time', iso: raw };
  const label = d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
  return { label, iso: raw };
}

export function backupReasonLabel(reason) {
  switch (String(reason || '')) {
    case 'reset_to_platform_defaults':
    case 'accept_platform_seed':
      return 'Before reset to platform defaults';
    case 'force_reset_keep_customizations_off':
      return 'Before automatic reset (keep customizations was off)';
    default:
      return 'Saved snapshot';
  }
}

export function renderResetDialogMarkup(agentName) {
  const li = (items) => items.map((i) => `<li>${escapeHtml(i)}</li>`).join('');
  return `
    <p>Reset <strong>${escapeHtml(agentName || 'this agent')}</strong> to the version that ships with AutoReiv?</p>
    <p class="text-emerald-300">A backup of the current version is saved first. You can restore it from Backups.</p>
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <div class="rounded-xl border border-amber-500/30 bg-amber-950/20 p-3">
        <h4 class="font-semibold text-amber-200 mb-1">Replaced</h4>
        <ul class="list-disc pl-4 space-y-0.5">${li(RESET_REPLACED)}</ul>
      </div>
      <div class="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-3">
        <h4 class="font-semibold text-emerald-200 mb-1">Kept</h4>
        <ul class="list-disc pl-4 space-y-0.5">${li(RESET_KEPT)}</ul>
      </div>
    </div>`;
}

export function renderBackupsListMarkup(backups) {
  if (!Array.isArray(backups) || backups.length === 0) {
    return '<p class="text-[11px] text-slate-500">No backups yet.</p>';
  }
  return backups
    .map((b) => {
      const t = formatBackupTime(b.backed_up_at);
      return `
      <div class="flex items-center justify-between gap-2 py-1.5 border-b border-white/[0.04] last:border-b-0">
        <div class="min-w-0">
          <span class="text-[11px] text-slate-200 block" title="${escapeHtml(t.iso)}">${escapeHtml(t.label)}</span>
          <span class="text-[10px] text-slate-500 block">${escapeHtml(backupReasonLabel(b.reason))}</span>
        </div>
        <button type="button" class="forge-pack-backup-restore px-2.5 py-1 rounded-lg bg-[#141721] hover:bg-slate-800 border border-white/[0.08] text-[11px] font-semibold text-slate-200" data-backup-id="${escapeHtml(b.id)}">Restore</button>
      </div>`;
    })
    .join('');
}

export function restoreDialogMessage(backup) {
  const t = formatBackupTime(backup && backup.backed_up_at);
  return (
    `Restore the instructions, skill list, tool list, max turns, and model saved on ${t.label}? ` +
    'Skill files on disk are not changed. The agent will count as customized, so platform updates will skip it ' +
    'until you reset it again.'
  );
}

async function readJson(res) {
  let body = null;
  try {
    body = await res.json();
  } catch (err) {
    console.warn('[AutoReiv UI] Platform defaults: response was not JSON', err);
  }
  if (!res.ok) {
    const detail = body && body.detail ? body.detail : `HTTP ${res.status}`;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return body || {};
}

/** Fresh agent + sync entry + backups for one agent [REQ-450-003]. */
export async function loadPlatformDefaultsData(agentId, fetchImpl = fetch) {
  const id = encodeURIComponent(agentId);
  const agent = await readJson(await fetchImpl(`/api/agents/${id}`));
  const report = await readJson(await fetchImpl('/api/platform-packs/sync-status'));
  const backupsBody = await readJson(await fetchImpl(`/api/agents/${id}/pack-content-backups`));
  return {
    agent,
    entry: platformSyncEntryFor(report, agentId),
    backups: Array.isArray(backupsBody.backups) ? backupsBody.backups : [],
  };
}

export async function performPlatformReset(agentId, fetchImpl = fetch) {
  await readJson(
    await fetchImpl(`/api/agents/${encodeURIComponent(agentId)}/accept-platform-seed`, { method: 'POST' }),
  );
  return loadPlatformDefaultsData(agentId, fetchImpl);
}

export async function performBackupRestore(agentId, backupId, fetchImpl = fetch) {
  const url = `/api/agents/${encodeURIComponent(agentId)}/pack-content-backups/${encodeURIComponent(backupId)}/restore`;
  await readJson(await fetchImpl(url, { method: 'POST' }));
  return loadPlatformDefaultsData(agentId, fetchImpl);
}

/**
 * Wire the Platform defaults section. Returns { render(agent) } for the coordinator.
 * @param {{ onAgentRefreshed?: (agent: object) => Promise<void>|void }} options
 */
export function setupPlatformDefaults(options = {}) {
  const section = $('forgePlatformDefaultsSection');
  const badge = $('forgePlatformUpdateBadge');
  const badgeText = $('forgePlatformUpdateText');
  const badgeHint = $('forgePlatformUpdateHint');
  const upToDate = $('forgePlatformUpToDate');
  const resetBtn = $('forgeResetPlatformDefaultsBtn');
  const backupsList = $('forgePackBackupsList');
  const resetModal = $('resetPlatformDefaultsModal');
  const resetBody = $('resetPlatformDefaultsBody');
  const confirmReset = $('confirmResetPlatformDefaultsBtn');
  const cancelReset = $('cancelResetPlatformDefaultsBtn');
  const restoreModal = $('restorePackBackupModal');
  const restoreMessage = $('restorePackBackupMessage');
  const confirmRestore = $('confirmRestorePackBackupBtn');
  const cancelRestore = $('cancelRestorePackBackupBtn');

  let currentAgent = null;
  let backups = [];
  let pendingBackupId = null;
  let busy = false;

  if (resetModal) setupModal(resetModal);
  if (restoreModal) setupModal(restoreModal);

  function paint(entry) {
    const info = platformUpdateBadge(entry);
    if (badge) badge.classList.toggle('hidden', !info);
    if (badgeText) badgeText.textContent = info ? info.text : '';
    if (badgeHint) badgeHint.textContent = info ? info.hint : '';
    if (upToDate) upToDate.classList.toggle('hidden', Boolean(info));
    if (backupsList) {
      backupsList.innerHTML = renderBackupsListMarkup(backups);
    }
  }

  async function refreshFrom(result) {
    backups = result.backups;
    paint(result.entry);
    if (typeof options.onAgentRefreshed === 'function') {
      await options.onAgentRefreshed(result.agent);
    }
  }

  async function render(agent) {
    currentAgent = agent || null;
    const isPlatform = Boolean(agent && agent.is_platform_pack);
    if (section) section.classList.toggle('hidden', !isPlatform);
    if (!isPlatform) return;
    try {
      const data = await loadPlatformDefaultsData(agent.id);
      if (!currentAgent || currentAgent.id !== agent.id) return;
      backups = data.backups;
      paint(data.entry);
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load platform defaults status:', err);
      showToast(`Could not load platform update status: ${err.message}`, 'error');
    }
  }

  function openReset() {
    if (!currentAgent || !resetModal) return;
    if (resetBody) resetBody.innerHTML = renderResetDialogMarkup(currentAgent.name || currentAgent.id);
    openModal(resetModal);
    if (cancelReset) cancelReset.focus();
    safeCreateIcons();
  }

  async function runReset() {
    if (!currentAgent || busy) return;
    busy = true;
    const agent = currentAgent;
    if (confirmReset) confirmReset.disabled = true;
    try {
      const result = await performPlatformReset(agent.id);
      closeModal(resetModal);
      await refreshFrom(result);
      showToast(`${agent.name || agent.id} was reset to platform defaults. A backup was saved.`, 'success');
    } catch (err) {
      console.error('[AutoReiv UI] Reset to platform defaults failed:', err);
      showToast(`Reset failed: ${err.message}`, 'error');
    } finally {
      busy = false;
      if (confirmReset) confirmReset.disabled = false;
    }
  }

  function openRestore(backupId) {
    const backup = backups.find((b) => String(b.id) === String(backupId));
    if (!backup || !restoreModal) return;
    pendingBackupId = backup.id;
    if (restoreMessage) restoreMessage.textContent = restoreDialogMessage(backup);
    openModal(restoreModal);
    if (cancelRestore) cancelRestore.focus();
    safeCreateIcons();
  }

  async function runRestore() {
    if (!currentAgent || !pendingBackupId || busy) return;
    busy = true;
    const agent = currentAgent;
    if (confirmRestore) confirmRestore.disabled = true;
    try {
      const result = await performBackupRestore(agent.id, pendingBackupId);
      closeModal(restoreModal);
      pendingBackupId = null;
      await refreshFrom(result);
      showToast(`Backup restored for ${agent.name || agent.id}.`, 'success');
    } catch (err) {
      console.error('[AutoReiv UI] Restore backup failed:', err);
      showToast(`Restore failed: ${err.message}`, 'error');
    } finally {
      busy = false;
      if (confirmRestore) confirmRestore.disabled = false;
    }
  }

  if (resetBtn) resetBtn.addEventListener('click', openReset);
  if (confirmReset) confirmReset.addEventListener('click', runReset);
  if (confirmRestore) confirmRestore.addEventListener('click', runRestore);
  if (backupsList) {
    backupsList.addEventListener('click', (event) => {
      const btn = event.target && event.target.closest ? event.target.closest('.forge-pack-backup-restore') : null;
      if (btn) openRestore(btn.getAttribute('data-backup-id'));
    });
  }

  return { render };
}
