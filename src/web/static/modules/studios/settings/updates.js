/**
 * Settings Studio — System & Software Updates handlers.
 * Extracted from settings.js for CARD-716 modularization.
 */

import { $, safeCreateIcons } from '../../dom.js';

export function initSettingsUpdates() {
  // --- System & Software Updates [CARD-196 / CARD-451] ---
  const systemVersionPill = $('systemVersionPill');
  const systemDeploymentBadge = $('systemDeploymentBadge');
  const systemCommitSha = $('systemCommitSha');
  const systemCommitSubject = $('systemCommitSubject');
  const systemBranchName = $('systemBranchName');
  const systemAheadBehind = $('systemAheadBehind');
  const systemTreeStatus = $('systemTreeStatus');
  const systemLastFetch = $('systemLastFetch');
  const updateRemoteUrl = $('updateRemoteUrl');
  const checkForUpdatesBtn = $('checkForUpdatesBtn');
  const applyUpdateBtn = $('applyUpdateBtn');
  const updateStatusBanner = $('updateStatusBanner');
  const updateStatusDot = $('updateStatusDot');
  const updateStatusMessage = $('updateStatusMessage');
  const updateNotesContainer = $('updateNotesContainer');
  const updateReleaseNotesText = $('updateReleaseNotesText');
  const updateManualDockerHelper = $('updateManualDockerHelper');
  const updateBranchSelect = $('updateBranchSelect');
  const switchBranchBtn = $('switchBranchBtn');
  const switchBranchStatus = $('switchBranchStatus');
  const autoUpdateEnabled = $('autoUpdateEnabled');
  const autoUpdateTime = $('autoUpdateTime');
  const saveAutoUpdateBtn = $('saveAutoUpdateBtn');
  const saveAutoUpdateStatus = $('saveAutoUpdateStatus');
  const autoUpdateLastResult = $('autoUpdateLastResult');
  const updateHistoryList = $('updateHistoryList');
  const applyUpdateDisabledReason = $('applyUpdateDisabledReason');
  const updateBranchListHint = $('updateBranchListHint');

  function formatLocalTimestamp(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return String(iso);
    try {
      return d.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      });
    } catch {
      return d.toString();
    }
  }

  function setTimestampEl(el, iso) {
    if (!el) return;
    if (!iso) {
      el.textContent = 'never';
      el.removeAttribute('title');
      return;
    }
    el.textContent = formatLocalTimestamp(iso);
    el.setAttribute('title', iso);
  }

  function showUpdateBanner(kind, message, notes) {
    if (!updateStatusBanner) return;
    updateStatusBanner.classList.remove('hidden');
    const colors = {
      ok: 'w-2 h-2 rounded-full bg-emerald-400',
      warn: 'w-2 h-2 rounded-full bg-amber-400',
      err: 'w-2 h-2 rounded-full bg-rose-500',
    };
    if (updateStatusDot) updateStatusDot.className = colors[kind] || colors.ok;
    if (updateStatusMessage) updateStatusMessage.textContent = message || '';
    if (notes && updateNotesContainer && updateReleaseNotesText) {
      updateReleaseNotesText.textContent = notes;
      updateNotesContainer.classList.remove('hidden');
    } else if (updateNotesContainer) {
      updateNotesContainer.classList.add('hidden');
    }
  }

  function renderVersion(data) {
    if (systemVersionPill) {
      systemVersionPill.textContent = data.current_version ? `v${data.current_version}` : '-';
    }
    if (systemDeploymentBadge) {
      const modeLabels = {
        git: 'Git Clone',
        docker: 'Docker Container',
        systemd: 'Systemd Service',
        windows_service: 'Windows Service',
        standalone: 'Standalone',
      };
      systemDeploymentBadge.textContent = modeLabels[data.deployment_mode] || data.deployment_mode || '-';
    }
    if (systemCommitSha) systemCommitSha.textContent = data.commit || 'unknown';
    if (systemCommitSubject) systemCommitSubject.textContent = data.subject || '';
    if (systemBranchName) systemBranchName.textContent = data.branch || (data.detached_head ? '(detached)' : '-');
    if (systemAheadBehind) {
      if (!data.upstream) {
        systemAheadBehind.textContent = 'No upstream';
        systemAheadBehind.className = 'text-amber-400';
        systemAheadBehind.title = 'This branch has no upstream tracking ref to compare against.';
      } else {
        const up = ` vs ${data.upstream}`;
        const ahead = data.ahead == null ? '?' : data.ahead;
        const behind = data.behind == null ? '?' : data.behind;
        systemAheadBehind.textContent = `+${ahead} / -${behind}${up}`;
        systemAheadBehind.className = 'text-slate-200';
        systemAheadBehind.title = '';
      }
    }
    if (systemTreeStatus) {
      if (data.is_dirty) {
        systemTreeStatus.textContent = 'Dirty (Uncommitted)';
        systemTreeStatus.className = 'text-amber-400 font-semibold';
      } else {
        systemTreeStatus.textContent = 'Clean';
        systemTreeStatus.className = 'text-emerald-400';
      }
    }
    if (systemLastFetch) {
      setTimestampEl(systemLastFetch, data.last_fetch_at);
    }
    if (updateRemoteUrl) {
      updateRemoteUrl.value = data.remote_url || '';
    }
    if (updateManualDockerHelper) {
      updateManualDockerHelper.classList.toggle('hidden', data.deployment_mode !== 'docker');
    }
    const gitOk = data.is_git && data.deployment_mode === 'git';
    if (applyUpdateBtn) {
      applyUpdateBtn.classList.toggle('hidden', !gitOk);
      const noUpstream = gitOk && !data.upstream;
      applyUpdateBtn.disabled = !!noUpstream;
      if (applyUpdateDisabledReason) {
        if (noUpstream) {
          applyUpdateDisabledReason.textContent = 'Update now disabled: no upstream on this branch.';
          applyUpdateDisabledReason.classList.remove('hidden');
        } else {
          applyUpdateDisabledReason.textContent = '';
          applyUpdateDisabledReason.classList.add('hidden');
        }
      }
    }
    if (switchBranchBtn) switchBranchBtn.disabled = !gitOk;
    if (updateBranchSelect) updateBranchSelect.disabled = !gitOk;
  }

  async function loadSystemVersionInfo() {
    try {
      const res = await fetch('/api/system/version');
      if (!res.ok) return;
      renderVersion(await res.json());
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load system version info:', err);
    }
  }

  async function loadUpdateConfig() {
    try {
      const res = await fetch('/api/system/updates/config');
      if (!res.ok) return;
      const data = await res.json();
      if (autoUpdateEnabled) autoUpdateEnabled.checked = !!data.auto_update_enabled;
      if (autoUpdateTime && data.auto_update_time) autoUpdateTime.value = data.auto_update_time;
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load update config:', err);
    }
  }

  async function loadAutoUpdateStatus() {
    try {
      const res = await fetch('/api/system/updates/auto-status');
      if (!res.ok || !autoUpdateLastResult) return;
      const data = await res.json();
      if (!data.last_run_at) {
        autoUpdateLastResult.textContent = 'Last auto-update: never';
        autoUpdateLastResult.removeAttribute('title');
      } else {
        const when = formatLocalTimestamp(data.last_run_at);
        autoUpdateLastResult.textContent = `Last auto-update: ${data.last_result || '?'} at ${when}${data.last_message ? ' — ' + data.last_message : ''}`;
        autoUpdateLastResult.setAttribute('title', data.last_run_at);
      }
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load auto-update status:', err);
    }
  }

  async function loadUpdateHistory() {
    try {
      const res = await fetch('/api/system/updates/history?limit=15');
      if (!res.ok || !updateHistoryList) return;
      const data = await res.json();
      const entries = data.entries || [];
      if (!entries.length) {
        updateHistoryList.innerHTML = '<li class="text-slate-500">No updates yet.</li>';
        return;
      }
      updateHistoryList.innerHTML = entries
        .map((e) => {
          const sha = e.from_sha && e.to_sha ? `${e.from_sha} → ${e.to_sha}` : '';
          const tsLabel = e.timestamp ? formatLocalTimestamp(e.timestamp) : '';
          const tsTitle = e.timestamp ? ` title="${String(e.timestamp).replace(/"/g, '&quot;')}"` : '';
          return `<li><span class="text-slate-500"${tsTitle}>${tsLabel}</span> · <span class="text-slate-200">${e.trigger}</span> · <span class="${e.result === 'success' ? 'text-emerald-400' : e.result === 'refused' || e.result === 'deferred' ? 'text-amber-400' : 'text-rose-400'}">${e.result}</span> · ${e.branch || ''} ${sha}<div class="text-slate-500 truncate">${e.message || ''}</div></li>`;
        })
        .join('');
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load update history:', err);
    }
  }

  async function loadBranchList() {
    if (!updateBranchSelect) return;
    try {
      const res = await fetch('/api/system/updates/branches');
      if (!res.ok) {
        if (updateBranchListHint) updateBranchListHint.textContent = 'Could not load branches.';
        return;
      }
      const data = await res.json();
      const branches = data.branches || [];
      updateBranchSelect.innerHTML = '';
      branches.forEach((b) => {
        const opt = document.createElement('option');
        opt.value = b.name;
        const tags = [];
        if (b.is_current) tags.push('current');
        if (b.is_local) tags.push('local');
        if (b.is_remote) tags.push('remote');
        opt.textContent = tags.length ? `${b.name} (${tags.join(', ')})` : b.name;
        if (b.is_current) opt.selected = true;
        updateBranchSelect.appendChild(opt);
      });
      if (updateBranchListHint) {
        const names = branches.map((b) => b.name);
        updateBranchListHint.textContent = branches.length
          ? `${branches.length} branches (includes ${['qa', 'main'].filter((n) => names.includes(n)).join(', ') || 'local/remote refs'})`
          : 'No branches found.';
      }
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load branches:', err);
      if (updateBranchListHint) updateBranchListHint.textContent = 'Could not load branches.';
    }
  }

  if (saveAutoUpdateBtn) {
    saveAutoUpdateBtn.addEventListener('click', async () => {
      try {
        saveAutoUpdateBtn.disabled = true;
        const res = await fetch('/api/system/updates/config', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            auto_update_enabled: !!(autoUpdateEnabled && autoUpdateEnabled.checked),
            auto_update_time: (autoUpdateTime && autoUpdateTime.value) || '03:00',
          }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        if (saveAutoUpdateStatus) {
          saveAutoUpdateStatus.textContent = 'Preferences saved.';
          saveAutoUpdateStatus.classList.remove('hidden', 'text-rose-400');
          saveAutoUpdateStatus.classList.add('text-emerald-400');
          setTimeout(() => saveAutoUpdateStatus.classList.add('hidden'), 3000);
        }
        await loadAutoUpdateStatus();
      } catch (err) {
        console.error('[AutoReiv UI] Failed to save auto-update config:', err);
        if (saveAutoUpdateStatus) {
          saveAutoUpdateStatus.textContent = 'Failed to save preferences.';
          saveAutoUpdateStatus.classList.remove('hidden', 'text-emerald-400');
          saveAutoUpdateStatus.classList.add('text-rose-400');
        }
      } finally {
        saveAutoUpdateBtn.disabled = false;
      }
    });
  }

  if (checkForUpdatesBtn) {
    checkForUpdatesBtn.addEventListener('click', async () => {
      try {
        checkForUpdatesBtn.disabled = true;
        const origHtml = checkForUpdatesBtn.innerHTML;
        checkForUpdatesBtn.innerHTML = '<span>Checking...</span>';
        const res = await fetch('/api/system/updates/check');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        await loadSystemVersionInfo();
        await loadBranchList();
        if (data.error) {
          showUpdateBanner('err', `Check failed: ${data.error}`);
        } else if (data.no_upstream) {
          showUpdateBanner(
            'warn',
            data.message ||
              `Branch '${data.channel || 'current'}' has no upstream to compare against.`,
          );
        } else if (data.update_available) {
          const behindTxt = data.commits_behind ? ` (${data.commits_behind} behind)` : '';
          showUpdateBanner('warn', `Update available: ${data.remote_commit || 'newer'}${behindTxt}`, data.release_notes || null);
        } else {
          showUpdateBanner('ok', `Up to date (${data.current_commit || 'HEAD'}).`);
        }
        checkForUpdatesBtn.innerHTML = origHtml;
        checkForUpdatesBtn.disabled = false;
        safeCreateIcons();
      } catch (err) {
        console.error('[AutoReiv UI] Update check error:', err);
        showUpdateBanner('err', 'Fetch failed or remote unreachable.');
        checkForUpdatesBtn.disabled = false;
        checkForUpdatesBtn.innerHTML = '<span>Check for Updates</span>';
      }
    });
  }

  if (applyUpdateBtn) {
    applyUpdateBtn.addEventListener('click', async () => {
      const ok = confirm(
        'Update now?\n\n' +
          'AutoReiv will snapshot your database, fast-forward the current branch from origin, install dependencies if needed, then restart serve on the same host/port.\n\n' +
          'Continue?',
      );
      if (!ok) return;
      try {
        applyUpdateBtn.disabled = true;
        applyUpdateBtn.textContent = 'Updating...';
        const res = await fetch('/api/system/updates/apply', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          showUpdateBanner('ok', data.message || `Updated to ${data.new_commit}.`);
          await loadSystemVersionInfo();
          await loadUpdateHistory();
        } else {
          showUpdateBanner('err', data.message || data.refusal_reason || 'Update refused.');
          await loadUpdateHistory();
        }
      } catch (err) {
        console.error('[AutoReiv UI] Failed to apply update:', err);
        showUpdateBanner('err', 'Failed to execute update: ' + err.message);
      } finally {
        applyUpdateBtn.disabled = false;
        applyUpdateBtn.textContent = 'Update now';
      }
    });
  }

  if (switchBranchBtn) {
    switchBranchBtn.addEventListener('click', async () => {
      const name = updateBranchSelect?.value?.trim() || '';
      if (!name) {
        alert('Select a branch first.');
        return;
      }
      const ok = confirm(
        `Switch to branch "${name}"?\n\n` +
          'Requires a clean working tree. Serve will restart after a successful switch.\n\nContinue?',
      );
      if (!ok) return;
      try {
        switchBranchBtn.disabled = true;
        const res = await fetch('/api/system/updates/switch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ branch: name }),
        });
        const data = await res.json();
        if (switchBranchStatus) {
          switchBranchStatus.classList.remove('hidden');
          switchBranchStatus.textContent = data.message || '';
          switchBranchStatus.className = `text-[11px] ${data.success ? 'text-emerald-400' : 'text-rose-400'}`;
        }
        if (data.success) {
          showUpdateBanner('ok', data.message || `Switched to ${name}.`);
        } else {
          showUpdateBanner('err', data.message || data.refusal_reason || 'Switch refused.');
        }
        await loadSystemVersionInfo();
        await loadBranchList();
        await loadUpdateHistory();
      } catch (err) {
        console.error('[AutoReiv UI] Branch switch failed:', err);
        showUpdateBanner('err', 'Branch switch failed: ' + err.message);
      } finally {
        switchBranchBtn.disabled = false;
      }
    });
  }

  return {
    loadSystemVersionInfo,
    loadUpdateConfig,
    loadAutoUpdateStatus,
    loadUpdateHistory,
    loadBranchList,
  };
}
