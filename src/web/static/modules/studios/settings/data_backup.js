/**
 * Settings Studio — Data Directory, Wiki Path, Backup/Restore, and Migrate handlers.
 * Extracted from settings.js for CARD-716 modularization.
 */

import { $ } from '../../dom.js';

export function initSettingsDataAndBackups() {
  async function loadDataDir() {
    const rootEl = $('dataDirRoot');
    if (!rootEl) return;
    try {
      const res = await fetch('/api/data-dir');
      if (!res.ok) return;
      const data = await res.json();
      rootEl.textContent = data.root || '-';
      const dbEl = $('dataDirDb');
      const wikiEl = $('dataDirWiki');
      const wikiStatusEl = $('dataDirWikiStatus');
      const skillsEl = $('dataDirSkills');
      if (dbEl) dbEl.textContent = data.db_path || '-';
      if (wikiEl) wikiEl.textContent = data.wiki_path || data.wiki_structural_path || '(not configured)';
      if (wikiStatusEl) wikiStatusEl.textContent = data.wiki_status || '-';
      if (skillsEl) skillsEl.textContent = data.skills_path || '-';
      const srcEl = $('dataDirMigrateSource');
      if (srcEl) srcEl.value = data.root || '';
      const wikiInput = $('wikiPathInput');
      if (wikiInput) {
        const pref = data.wiki_path || data.wiki_structural_path || '';
        if (pref) wikiInput.value = pref;
      }
      const confirmEl = $('wikiScaffoldConfirm');
      if (confirmEl && confirmEl.checked === false && !(data.wiki_path)) {
        confirmEl.checked = true;
      }
      const msg = $('wikiPathStatusMsg');
      if (msg && data.wiki_message) {
        msg.textContent = data.wiki_message;
        msg.classList.remove('hidden');
        msg.classList.toggle(
          'text-rose-400',
          data.wiki_status === 'missing' || data.wiki_status === 'unset' || data.wiki_status === 'docker_required',
        );
      }
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load data dir:', err);
    }
  }

  async function saveWikiPath() {
    const input = $('wikiPathInput');
    const confirmEl = $('wikiScaffoldConfirm');
    const msg = $('wikiPathStatusMsg');
    const path = (input && input.value ? input.value : '').trim();
    if (!path) {
      if (msg) {
        msg.textContent = 'Enter a wiki folder path (default lives under your data directory).';
        msg.classList.remove('hidden');
        msg.classList.add('text-rose-400');
      }
      return;
    }
    try {
      const res = await fetch('/api/settings/wiki-path', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path,
          confirm_scaffold: Boolean(confirmEl && confirmEl.checked),
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      if (msg) {
        msg.textContent = data.wiki_message || 'Wiki path saved.';
        msg.classList.remove('hidden', 'text-rose-400');
      }
      await loadDataDir();
    } catch (err) {
      console.error('[AutoReiv UI] Save wiki path failed:', err);
      if (msg) {
        msg.textContent = `Save failed: ${err.message}`;
        msg.classList.remove('hidden');
        msg.classList.add('text-rose-400');
      }
    }
  }

  function setDataDirStatus(message, isError) {
    const statusEl = $('dataDirBackupStatus');
    if (!statusEl) return;
    statusEl.textContent = message || '';
    statusEl.classList.toggle('hidden', !message);
    statusEl.classList.toggle('text-rose-400', Boolean(isError));
    statusEl.classList.toggle('text-slate-400', !isError);
  }

  function filenameFromDisposition(header, fallback) {
    if (!header) return fallback;
    const star = /filename\*=UTF-8''([^;]+)/i.exec(header);
    if (star && star[1]) {
      try {
        return decodeURIComponent(star[1]);
      } catch {
        return star[1];
      }
    }
    const quoted = /filename="([^"]+)"/i.exec(header);
    if (quoted && quoted[1]) return quoted[1];
    const plain = /filename=([^;]+)/i.exec(header);
    if (plain && plain[1]) return plain[1].trim();
    return fallback;
  }

  async function backupDataDir() {
    const btn = $('backupDataDirBtn');
    try {
      if (btn) btn.disabled = true;
      setDataDirStatus('Creating backup...');
      const res = await fetch('/api/data-dir/backup', { method: 'POST' });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || `HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const filename = filenameFromDisposition(
        res.headers.get('Content-Disposition'),
        'autoreiv-data.zip',
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setDataDirStatus(`Backup downloaded: ${filename}`);
    } catch (err) {
      console.error('[AutoReiv UI] Backup failed:', err);
      setDataDirStatus(`Backup failed: ${err.message}`, true);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function restoreDataDir(file) {
    if (!file) return;
    const ok = window.confirm(
      'Restore will replace the data directory with this backup. The live tree is replaced, not merged. Continue?',
    );
    if (!ok) {
      setDataDirStatus('Restore cancelled; live tree unchanged.');
      return;
    }
    const btn = $('restoreDataDirBtn');
    try {
      if (btn) btn.disabled = true;
      setDataDirStatus('Restoring...');
      const fd = new FormData();
      fd.append('archive', file);
      fd.append('confirm', 'true');
      const res = await fetch('/api/data-dir/restore', { method: 'POST', body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      setDataDirStatus('Restore complete. Reloading paths...');
      await loadDataDir();
    } catch (err) {
      console.error('[AutoReiv UI] Restore failed:', err);
      setDataDirStatus(`Restore failed: ${err.message}`, true);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function setMigrateStatus(message, isError) {
    const statusEl = $('dataDirMigrateStatus');
    if (!statusEl) return;
    statusEl.textContent = message || '';
    statusEl.classList.toggle('hidden', !message);
    statusEl.classList.toggle('text-rose-400', Boolean(isError));
    statusEl.classList.toggle('text-emerald-400', Boolean(message) && !isError);
    statusEl.classList.toggle('text-slate-400', !message || isError);
  }

  async function migrateDataDir() {
    const destEl = $('dataDirMigrateDest');
    const btn = $('migrateDataDirBtn');
    const destination = (destEl && destEl.value ? destEl.value : '').trim();
    if (!destination) {
      setMigrateStatus('Destination path is required.', true);
      return;
    }
    const srcEl = $('dataDirMigrateSource');
    const source = (srcEl && srcEl.value) || '';
    const ok = window.confirm(
      `Migrate will copy\n  ${source || '(current root)'}\nto\n  ${destination}\nthen rename the old root to *_backup_<timestamp> and persist AUTOREIV_DATA_DIR. Continue?`,
    );
    if (!ok) {
      setMigrateStatus('Migrate cancelled; live tree unchanged.');
      return;
    }
    try {
      if (btn) btn.disabled = true;
      setMigrateStatus('Migrating data directory...');
      const res = await fetch('/api/data-dir/migrate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ destination }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data.detail || data.message || `HTTP ${res.status}`;
        throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
      }
      const backup = data.backup_path ? ` Backup: ${data.backup_path}.` : '';
      setMigrateStatus(`Migrated to ${data.root}.${backup} Restart recommended so all services reopen on the new root.`);
      await loadDataDir();
      if (destEl) destEl.value = '';
    } catch (err) {
      console.error('[AutoReiv UI] Migrate failed:', err);
      setMigrateStatus(`Migrate failed: ${err.message}`, true);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  const migrateDataDirBtn = $('migrateDataDirBtn');
  if (migrateDataDirBtn) {
    migrateDataDirBtn.addEventListener('click', () => migrateDataDir());
  }
  const saveWikiPathBtn = $('saveWikiPathBtn');
  if (saveWikiPathBtn) {
    saveWikiPathBtn.addEventListener('click', () => saveWikiPath());
  }
  const backupDataDirBtn = $('backupDataDirBtn');
  if (backupDataDirBtn) {
    backupDataDirBtn.addEventListener('click', () => backupDataDir());
  }
  const restoreDataDirBtn = $('restoreDataDirBtn');
  const restoreDataDirFile = $('restoreDataDirFile');
  if (restoreDataDirBtn && restoreDataDirFile) {
    restoreDataDirBtn.addEventListener('click', () => restoreDataDirFile.click());
    restoreDataDirFile.addEventListener('change', () => {
      const file = restoreDataDirFile.files && restoreDataDirFile.files[0];
      restoreDataDir(file).finally(() => {
        restoreDataDirFile.value = '';
      });
    });
  }

  function setBackupConfigStatus(message, isError) {
    const statusEl = $('backupConfigStatus');
    if (!statusEl) return;
    statusEl.textContent = message || '';
    statusEl.classList.toggle('hidden', !message);
    statusEl.classList.toggle('text-rose-400', Boolean(isError));
    statusEl.classList.toggle('text-emerald-400', Boolean(message) && !isError);
    statusEl.classList.toggle('text-slate-400', !message || isError);
  }

  function renderBackupCatalogTable(backups) {
    const tbody = $('backupCatalogTbody');
    if (!tbody) return;
    tbody.replaceChildren();

    if (!backups || backups.length === 0) {
      const tr = document.createElement('tr');
      const td = document.createElement('td');
      td.colSpan = 4;
      td.className = 'py-3 px-3 text-center text-slate-500 font-sans text-xs';
      td.textContent = 'No backups found yet.';
      tr.appendChild(td);
      tbody.appendChild(tr);
      return;
    }

    backups.forEach((b) => {
      const tr = document.createElement('tr');
      tr.className = 'hover:bg-white/[0.02] transition-colors';

      const tdName = document.createElement('td');
      tdName.className = 'py-2 px-3 flex items-center space-x-1.5';
      const nameSpan = document.createElement('span');
      nameSpan.className = 'truncate max-w-[200px] text-slate-200';
      nameSpan.title = b.filename;
      nameSpan.textContent = b.filename;
      tdName.appendChild(nameSpan);
      if (b.is_pre_restore) {
        const badge = document.createElement('span');
        badge.className = 'text-[9px] px-1 py-0.5 bg-amber-500/20 text-amber-300 rounded font-sans';
        badge.textContent = 'pre-restore';
        tdName.appendChild(badge);
      }
      tr.appendChild(tdName);

      const tdCreated = document.createElement('td');
      tdCreated.className = 'py-2 px-3 text-slate-400 whitespace-nowrap';
      tdCreated.textContent = (b.created_at || '').replace('T', ' ').replace('Z', '');
      tr.appendChild(tdCreated);

      const tdSize = document.createElement('td');
      tdSize.className = 'py-2 px-3 text-slate-400 whitespace-nowrap';
      tdSize.textContent = `${b.size_mb} MB`;
      tr.appendChild(tdSize);

      const tdActions = document.createElement('td');
      tdActions.className = 'py-2 px-3 text-right space-x-1.5 whitespace-nowrap';

      const downloadBtn = document.createElement('button');
      downloadBtn.type = 'button';
      downloadBtn.className = 'px-2 py-0.5 text-xs text-brand-400 hover:text-brand-300 transition-colors backup-download-btn';
      downloadBtn.dataset.filename = b.filename;
      downloadBtn.textContent = 'Download';
      tdActions.appendChild(downloadBtn);

      const restoreBtn = document.createElement('button');
      restoreBtn.type = 'button';
      restoreBtn.className = 'px-2 py-0.5 text-xs text-amber-400 hover:text-amber-300 transition-colors backup-restore-btn';
      restoreBtn.dataset.filename = b.filename;
      restoreBtn.textContent = 'Restore';
      tdActions.appendChild(restoreBtn);

      const deleteBtn = document.createElement('button');
      deleteBtn.type = 'button';
      deleteBtn.className = 'px-2 py-0.5 text-xs text-rose-400 hover:text-rose-300 transition-colors backup-delete-btn';
      deleteBtn.dataset.filename = b.filename;
      deleteBtn.textContent = 'Delete';
      tdActions.appendChild(deleteBtn);

      tr.appendChild(tdActions);
      tbody.appendChild(tr);
    });
  }

  async function loadBackupCatalogAndConfig() {
    try {
      const res = await fetch('/api/data-dir/backups');
      if (!res.ok) return;
      const data = await res.json();
      const dirInput = $('backupDirPath');
      if (dirInput && data.config && data.config.backup_dir) {
        dirInput.value = data.config.backup_dir;
      }
      const schedSelect = $('backupSchedule');
      if (schedSelect && data.config && data.config.schedule) {
        schedSelect.value = data.config.schedule;
      }
      const retInput = $('backupRetentionCount');
      if (retInput && data.config && data.config.retention_count) {
        retInput.value = data.config.retention_count;
      }
      const countEl = $('backupCatalogCount');
      const backups = Array.isArray(data.backups) ? data.backups : [];
      if (countEl) {
        countEl.textContent = `${backups.length} archive${backups.length === 1 ? '' : 's'}`;
      }
      renderBackupCatalogTable(backups);
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load backup catalog:', err);
    }
  }

  async function saveBackupConfig() {
    const btn = $('saveBackupConfigBtn');
    const dirInput = $('backupDirPath');
    const schedSelect = $('backupSchedule');
    const retInput = $('backupRetentionCount');

    const backupDir = (dirInput ? dirInput.value : '').trim();
    const schedule = schedSelect ? schedSelect.value : 'disabled';
    const retentionCount = retInput ? parseInt(retInput.value, 10) : 7;

    try {
      if (btn) btn.disabled = true;
      setBackupConfigStatus('Saving backup settings...');
      const res = await fetch('/api/data-dir/backup-config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          backup_dir: backupDir,
          schedule: schedule,
          retention_count: retentionCount,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      setBackupConfigStatus('Backup settings saved successfully.');
      await loadBackupCatalogAndConfig();
    } catch (err) {
      console.error('[AutoReiv UI] Save backup config failed:', err);
      setBackupConfigStatus(`Failed to save settings: ${err.message}`, true);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function runImmediateBackup() {
    const btn = $('runBackupBtn');
    try {
      if (btn) btn.disabled = true;
      setBackupConfigStatus('Creating backup and enforcing retention...');
      const res = await fetch('/api/data-dir/backups/run', { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      const prunedMsg = data.pruned && data.pruned.length > 0 ? ` (pruned ${data.pruned.length} older)` : '';
      setBackupConfigStatus(`Backup created: ${data.filename}${prunedMsg}`);
      await loadBackupCatalogAndConfig();
    } catch (err) {
      console.error('[AutoReiv UI] Run backup failed:', err);
      setBackupConfigStatus(`Backup failed: ${err.message}`, true);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  const saveBackupConfigBtn = $('saveBackupConfigBtn');
  if (saveBackupConfigBtn) {
    saveBackupConfigBtn.addEventListener('click', () => saveBackupConfig());
  }
  const runBackupBtn = $('runBackupBtn');
  if (runBackupBtn) {
    runBackupBtn.addEventListener('click', () => runImmediateBackup());
  }

  const backupCatalogTbody = $('backupCatalogTbody');
  if (backupCatalogTbody) {
    backupCatalogTbody.addEventListener('click', async (e) => {
      const dlBtn = e.target.closest('.backup-download-btn');
      if (dlBtn) {
        const fn = dlBtn.dataset.filename;
        if (!fn) return;
        const a = document.createElement('a');
        a.href = `/api/data-dir/backups/${encodeURIComponent(fn)}/download`;
        a.download = fn;
        document.body.appendChild(a);
        a.click();
        a.remove();
        return;
      }
      const resBtn = e.target.closest('.backup-restore-btn');
      if (resBtn) {
        const fn = resBtn.dataset.filename;
        if (!fn) return;
        const ok = window.confirm(
          `Restore will replace the current data directory with archive:\n  ${fn}\nA safety pre-restore backup will be taken automatically. Continue?`,
        );
        if (!ok) return;
        try {
          setBackupConfigStatus(`Restoring from ${fn}...`);
          const res = await fetch(`/api/data-dir/backups/${encodeURIComponent(fn)}/restore`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ confirm: true }),
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok) {
            throw new Error(data.detail || `HTTP ${res.status}`);
          }
          setBackupConfigStatus(`Restored successfully from ${fn}. Reloading paths...`);
          await loadDataDir();
          await loadBackupCatalogAndConfig();
        } catch (err) {
          console.error('[AutoReiv UI] Restore failed:', err);
          setBackupConfigStatus(`Restore failed: ${err.message}`, true);
        }
        return;
      }
      const delBtn = e.target.closest('.backup-delete-btn');
      if (delBtn) {
        const fn = delBtn.dataset.filename;
        if (!fn) return;
        const ok = window.confirm(`Permanently delete backup archive "${fn}"?`);
        if (!ok) return;
        try {
          const res = await fetch(`/api/data-dir/backups/${encodeURIComponent(fn)}`, {
            method: 'DELETE',
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok) {
            throw new Error(data.detail || `HTTP ${res.status}`);
          }
          setBackupConfigStatus(`Deleted backup archive: ${fn}`);
          await loadBackupCatalogAndConfig();
        } catch (err) {
          console.error('[AutoReiv UI] Delete failed:', err);
          setBackupConfigStatus(`Delete failed: ${err.message}`, true);
        }
      }
    });
  }

  return {
    loadDataDir,
    loadBackupCatalogAndConfig,
  };
}
