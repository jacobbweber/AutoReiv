/**
 * Settings Studio — Credential Vault and Remote SSH Hosts handlers.
 * Extracted from settings.js for CARD-716 modularization.
 */

import { $, safeCreateIcons } from '../../dom.js';
import { escapeHtml } from '../../utils/formatters.js';

export function initSettingsVaultAndRemoteHosts(state, { populateVaultCredDropdown }) {
  // --- Credential Vault [CARD-168, CARD-188] ---
  const addCredentialBtn = $('addCredentialBtn');
  const credentialFormContainer = $('credentialFormContainer');
  const cancelCredentialBtn = $('cancelCredentialBtn');
  const saveCredentialBtn = $('saveCredentialBtn');
  const credNameInput = $('credNameInput');
  const credIdInput = $('credIdInput');
  const credTypeSelect = $('credTypeSelect');
  const credSecretInput = $('credSecretInput');
  const toggleCredSecretVisibilityBtn = $('toggleCredSecretVisibilityBtn');
  const credDescInput = $('credDescInput');
  const credentialsTableBody = $('credentialsTableBody');

  if (toggleCredSecretVisibilityBtn && credSecretInput) {
    toggleCredSecretVisibilityBtn.addEventListener('click', () => {
      const isPassword = credSecretInput.type === 'password';
      credSecretInput.type = isPassword ? 'text' : 'password';
      toggleCredSecretVisibilityBtn.innerHTML = isPassword
        ? '<i data-lucide="eye-off" class="w-3.5 h-3.5"></i>'
        : '<i data-lucide="eye" class="w-3.5 h-3.5"></i>';
      safeCreateIcons();
    });
  }

  if (addCredentialBtn && credentialFormContainer) {
    addCredentialBtn.addEventListener('click', () => {
      credentialFormContainer.classList.toggle('hidden');
      if (!credentialFormContainer.classList.contains('hidden')) {
        if (credNameInput) credNameInput.value = '';
        if (credIdInput) {
          credIdInput.value = '';
          credIdInput.disabled = false;
        }
        if (credSecretInput) {
          credSecretInput.value = '';
          credSecretInput.placeholder = 'Paste sensitive token or key...';
          credSecretInput.type = 'password';
        }
        if (toggleCredSecretVisibilityBtn) {
          toggleCredSecretVisibilityBtn.innerHTML = '<i data-lucide="eye" class="w-3.5 h-3.5"></i>';
        }
        if (credDescInput) credDescInput.value = '';
        if (saveCredentialBtn) saveCredentialBtn.textContent = 'Save & Encrypt';
        if (credNameInput) credNameInput.focus();
        safeCreateIcons();
      }
    });
  }

  if (cancelCredentialBtn && credentialFormContainer) {
    cancelCredentialBtn.addEventListener('click', () => {
      credentialFormContainer.classList.add('hidden');
      if (credIdInput) credIdInput.disabled = false;
    });
  }

  async function loadCredentials() {
    try {
      const res = await fetch('/api/vault/credentials');
      if (!res.ok) return;
      const creds = await res.json();
      state.vaultCredentials = creds;
      populateVaultCredDropdown(creds);
      if (!credentialsTableBody) return;
      if (!creds || creds.length === 0) {
        credentialsTableBody.innerHTML = `<tr><td colspan="5" class="p-3 text-center text-slate-500 italic">No credentials in vault. Click 'Add Credential' to encrypt a new secret.</td></tr>`;
        return;
      }
      credentialsTableBody.innerHTML = creds.map(c => `
        <tr class="hover:bg-slate-800/40 transition">
          <td class="p-2.5">
            <div class="font-medium text-slate-100">${escapeHtml(c.name)}</div>
            <div class="font-mono text-[10px] text-slate-500">${escapeHtml(c.id)}</div>
          </td>
          <td class="p-2.5">
            <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-brand-300 border border-slate-700">${escapeHtml(c.type || 'token')}</span>
          </td>
          <td class="p-2.5 text-slate-400 text-xs">${escapeHtml(c.description || '-')}</td>
          <td class="p-2.5">
            <div class="flex items-center space-x-1.5">
              <span id="cred-preview-${escapeHtml(c.id)}" class="font-mono text-[11px] text-emerald-400">${escapeHtml(c.masked_preview || '••••••••')}</span>
              <button data-reveal-cred="${escapeHtml(c.id)}" class="p-1 hover:bg-slate-700 text-slate-400 hover:text-slate-200 rounded transition" title="Show/Hide Secret">
                <i data-lucide="eye" class="w-3.5 h-3.5"></i>
              </button>
            </div>
          </td>
          <td class="p-2.5 text-right">
            <button data-edit-cred="${escapeHtml(c.id)}" class="p-1.5 hover:bg-slate-700 text-slate-400 hover:text-slate-200 rounded transition mr-1" title="Edit Credential">
              <i data-lucide="pencil" class="w-3.5 h-3.5"></i>
            </button>
            <button data-delete-cred="${escapeHtml(c.id)}" class="p-1.5 hover:bg-rose-900/50 text-slate-400 hover:text-rose-300 rounded transition" title="Delete Credential">
              <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
            </button>
          </td>
        </tr>
      `).join('');
      safeCreateIcons();

      credentialsTableBody.querySelectorAll('[data-reveal-cred]').forEach(btn => {
        btn.addEventListener('click', async () => {
          const id = btn.getAttribute('data-reveal-cred');
          const previewEl = $(`cred-preview-${id}`);
          if (!previewEl) return;
          const isRevealed = btn.getAttribute('data-revealed') === 'true';
          if (isRevealed) {
            const credObj = (state.vaultCredentials || []).find(x => x.id === id);
            previewEl.textContent = credObj?.masked_preview || '••••••••';
            btn.setAttribute('data-revealed', 'false');
            btn.innerHTML = '<i data-lucide="eye" class="w-3.5 h-3.5"></i>';
            safeCreateIcons();
          } else {
            try {
              btn.disabled = true;
              const res = await fetch(`/api/vault/credentials/${id}/reveal`);
              if (!res.ok) throw new Error(`HTTP ${res.status}`);
              const data = await res.json();
              previewEl.textContent = data.secret;
              btn.setAttribute('data-revealed', 'true');
              btn.innerHTML = '<i data-lucide="eye-off" class="w-3.5 h-3.5"></i>';
              safeCreateIcons();
            } catch (err) {
              console.error('[AutoReiv UI] Failed to reveal credential:', err);
              alert(`Could not reveal credential: ${err.message}`);
            } finally {
              btn.disabled = false;
            }
          }
        });
      });

      credentialsTableBody.querySelectorAll('[data-edit-cred]').forEach(btn => {
        btn.addEventListener('click', () => {
          const id = btn.getAttribute('data-edit-cred');
          const cred = (state.vaultCredentials || []).find(x => x.id === id);
          if (!cred) return;
          if (credentialFormContainer) credentialFormContainer.classList.remove('hidden');
          if (credNameInput) credNameInput.value = cred.name || '';
          if (credIdInput) {
            credIdInput.value = cred.id;
            credIdInput.disabled = true;
          }
          if (credTypeSelect) credTypeSelect.value = cred.type || 'token';
          if (credDescInput) credDescInput.value = cred.description || '';
          if (credSecretInput) {
            credSecretInput.value = '';
            credSecretInput.placeholder = 'Leave blank to keep existing secret';
            credSecretInput.type = 'password';
          }
          if (toggleCredSecretVisibilityBtn) {
            toggleCredSecretVisibilityBtn.innerHTML = '<i data-lucide="eye" class="w-3.5 h-3.5"></i>';
          }
          if (saveCredentialBtn) saveCredentialBtn.textContent = 'Update & Encrypt';
          if (credNameInput) credNameInput.focus();
          safeCreateIcons();
        });
      });

      credentialsTableBody.querySelectorAll('[data-delete-cred]').forEach(btn => {
        btn.addEventListener('click', async () => {
          const id = btn.getAttribute('data-delete-cred');
          if (!confirm(`Are you sure you want to delete credential '${id}' from the vault? Agents granted this credential will lose access immediately.`)) return;
          try {
            await fetch(`/api/vault/credentials/${id}`, { method: 'DELETE' });
            await loadCredentials();
          } catch (err) {
            console.error('[AutoReiv UI] Failed to delete credential:', err);
          }
        });
      });
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load credentials:', err);
    }
  }

  if (saveCredentialBtn) {
    saveCredentialBtn.addEventListener('click', async () => {
      const name = credNameInput?.value.trim();
      const secret = credSecretInput?.value.trim();
      const isEdit = credIdInput?.disabled;
      if (!name) {
        alert('Name is required.');
        return;
      }
      if (!isEdit && !secret) {
        alert('Name and Secret Value are required.');
        return;
      }
      const payload = {
        name,
        secret: secret || undefined,
        id: credIdInput?.value.trim() || undefined,
        type: credTypeSelect?.value || 'token',
        description: credDescInput?.value.trim() || '',
      };
      try {
        saveCredentialBtn.textContent = isEdit ? 'Updating...' : 'Encrypting...';
        const res = await fetch('/api/vault/credentials', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        if (credNameInput) credNameInput.value = '';
        if (credIdInput) {
          credIdInput.value = '';
          credIdInput.disabled = false;
        }
        if (credSecretInput) {
          credSecretInput.value = '';
          credSecretInput.placeholder = 'Paste sensitive token or key...';
          credSecretInput.type = 'password';
        }
        if (credDescInput) credDescInput.value = '';
        if (credentialFormContainer) credentialFormContainer.classList.add('hidden');
        saveCredentialBtn.textContent = 'Save & Encrypt';
        await loadCredentials();
      } catch (err) {
        console.error('[AutoReiv UI] Failed to save credential:', err);
        saveCredentialBtn.textContent = 'Error!';
        setTimeout(() => (saveCredentialBtn.textContent = isEdit ? 'Update & Encrypt' : 'Save & Encrypt'), 2000);
      }
    });
  }

  // --- Remote SSH Hosts [CARD-160, CARD-188] ---
  const addRemoteHostBtn = $('addRemoteHostBtn');
  const remoteHostFormContainer = $('remoteHostFormContainer');
  const closeRemoteHostFormBtn = $('closeRemoteHostFormBtn');
  const cancelRemoteHostBtn = $('cancelRemoteHostBtn');
  const saveRemoteHostBtn = $('saveRemoteHostBtn');
  const hostLabelInput = $('hostLabelInput');
  const hostIdInput = $('hostIdInput');
  const hostAddressInput = $('hostAddressInput');
  const hostPortInput = $('hostPortInput');
  const hostAuthTypeSelect = $('hostAuthTypeSelect');
  const hostUsernameInput = $('hostUsernameInput');
  const hostCredentialSelect = $('hostCredentialSelect');
  const remoteHostsTableBody = $('remoteHostsTableBody');

  function populateHostCredentialSelect() {
    if (!hostCredentialSelect) return;
    const creds = state.vaultCredentials || [];
    const currentVal = hostCredentialSelect.value;
    hostCredentialSelect.innerHTML = '<option value="">-- No Vault Credential --</option>' +
      creds.map(c => `<option value="${escapeHtml(c.id)}">${escapeHtml(c.name)} (${escapeHtml(c.id)})</option>`).join('');
    if (currentVal) hostCredentialSelect.value = currentVal;
  }

  if (addRemoteHostBtn && remoteHostFormContainer) {
    addRemoteHostBtn.addEventListener('click', () => {
      remoteHostFormContainer.classList.toggle('hidden');
      if (!remoteHostFormContainer.classList.contains('hidden')) {
        populateHostCredentialSelect();
        if (hostLabelInput) hostLabelInput.value = '';
        if (hostIdInput) {
          hostIdInput.value = '';
          hostIdInput.disabled = false;
        }
        if (hostAddressInput) hostAddressInput.value = '';
        if (hostPortInput) hostPortInput.value = '22';
        if (hostUsernameInput) hostUsernameInput.value = '';
        if (hostCredentialSelect) hostCredentialSelect.value = '';
        if (saveRemoteHostBtn) saveRemoteHostBtn.textContent = 'Save Remote Host';
        if (hostLabelInput) hostLabelInput.focus();
      }
    });
  }

  if (closeRemoteHostFormBtn && remoteHostFormContainer) {
    closeRemoteHostFormBtn.addEventListener('click', () => {
      remoteHostFormContainer.classList.add('hidden');
      if (hostIdInput) hostIdInput.disabled = false;
    });
  }

  if (cancelRemoteHostBtn && remoteHostFormContainer) {
    cancelRemoteHostBtn.addEventListener('click', () => {
      remoteHostFormContainer.classList.add('hidden');
      if (hostIdInput) hostIdInput.disabled = false;
    });
  }

  async function loadRemoteHosts() {
    if (!remoteHostsTableBody) return;
    try {
      const res = await fetch('/api/remote_hosts');
      if (!res.ok) return;
      const hosts = await res.json();
      state.remoteHosts = hosts;
      if (!hosts || hosts.length === 0) {
        remoteHostsTableBody.innerHTML = `<tr><td colspan="6" class="p-3 text-center text-slate-500 italic">No remote hosts configured. Click 'Add Remote Host' to configure an SSH connection.</td></tr>`;
        return;
      }
      remoteHostsTableBody.innerHTML = hosts.map(h => `
        <tr class="hover:bg-slate-800/40 transition">
          <td class="p-2.5">
            <div class="font-medium text-slate-100">${escapeHtml(h.label)}</div>
            <div class="font-mono text-[10px] text-slate-500">${escapeHtml(h.id)}</div>
          </td>
          <td class="p-2.5 font-mono text-xs text-sky-400">${escapeHtml(h.host)}</td>
          <td class="p-2.5 font-mono text-xs text-slate-300">${escapeHtml(String(h.port || 22))}</td>
          <td class="p-2.5 font-mono text-xs text-slate-300">${escapeHtml(h.username)}</td>
          <td class="p-2.5">
            <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-brand-300 border border-slate-700">${escapeHtml(h.credential_id || 'None')}</span>
          </td>
          <td class="p-2.5 text-right">
            <button data-edit-host="${escapeHtml(h.id)}" class="p-1.5 hover:bg-slate-700 text-slate-400 hover:text-slate-200 rounded transition mr-1" title="Edit Host">
              <i data-lucide="pencil" class="w-3.5 h-3.5"></i>
            </button>
            <button data-test-host="${escapeHtml(h.id)}" class="p-1.5 hover:bg-sky-900/50 text-slate-400 hover:text-sky-300 rounded transition mr-1" title="Test SSH Handshake">
              <i data-lucide="activity" class="w-3.5 h-3.5"></i>
            </button>
            <button data-delete-host="${escapeHtml(h.id)}" class="p-1.5 hover:bg-rose-900/50 text-slate-400 hover:text-rose-300 rounded transition" title="Delete Host">
              <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
            </button>
          </td>
        </tr>
      `).join('');
      safeCreateIcons();

      remoteHostsTableBody.querySelectorAll('[data-edit-host]').forEach(btn => {
        btn.addEventListener('click', () => {
          const id = btn.getAttribute('data-edit-host');
          const host = (state.remoteHosts || []).find(x => x.id === id);
          if (!host) return;
          if (remoteHostFormContainer) remoteHostFormContainer.classList.remove('hidden');
          populateHostCredentialSelect();
          if (hostLabelInput) hostLabelInput.value = host.label || '';
          if (hostIdInput) {
            hostIdInput.value = host.id;
            hostIdInput.disabled = true;
          }
          if (hostAddressInput) hostAddressInput.value = host.host || '';
          if (hostPortInput) hostPortInput.value = host.port || 22;
          if (hostAuthTypeSelect) hostAuthTypeSelect.value = host.auth_type || 'password';
          if (hostUsernameInput) hostUsernameInput.value = host.username || '';
          if (hostCredentialSelect) hostCredentialSelect.value = host.credential_id || '';
          if (saveRemoteHostBtn) saveRemoteHostBtn.textContent = 'Update Remote Host';
          if (hostLabelInput) hostLabelInput.focus();
        });
      });

      remoteHostsTableBody.querySelectorAll('[data-test-host]').forEach(btn => {
        btn.addEventListener('click', async () => {
          const id = btn.getAttribute('data-test-host');
          btn.disabled = true;
          const originalHtml = btn.innerHTML;
          btn.innerHTML = '<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i>';
          safeCreateIcons();
          try {
            const res = await fetch(`/api/remote_hosts/${id}/test`, { method: 'POST' });
            const data = await res.json();
            if (res.ok && data.status === 'ok') {
              alert(`SSH connection to '${id}' successful! Latency: ${data.latency_ms}ms`);
            } else {
              alert(`SSH connection probe failed for '${id}':\n${data.message || 'Unknown error'}`);
            }
          } catch (err) {
            alert(`SSH probe failed: ${err.message}`);
          } finally {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
            safeCreateIcons();
          }
        });
      });

      remoteHostsTableBody.querySelectorAll('[data-delete-host]').forEach(btn => {
        btn.addEventListener('click', async () => {
          const id = btn.getAttribute('data-delete-host');
          if (!confirm(`Are you sure you want to delete remote host '${id}'?`)) return;
          try {
            await fetch(`/api/remote_hosts/${id}`, { method: 'DELETE' });
            await loadRemoteHosts();
          } catch (err) {
            console.error('[AutoReiv UI] Failed to delete remote host:', err);
          }
        });
      });
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load remote hosts:', err);
    }
  }

  if (saveRemoteHostBtn) {
    saveRemoteHostBtn.addEventListener('click', async () => {
      const label = hostLabelInput?.value.trim();
      const host = hostAddressInput?.value.trim();
      const username = hostUsernameInput?.value.trim();
      const port = parseInt(hostPortInput?.value.trim() || '22', 10);
      const authType = hostAuthTypeSelect?.value || 'password';
      const credentialId = hostCredentialSelect?.value || '';
      const customId = hostIdInput?.value.trim() || undefined;

      if (!label || !host || !username) {
        alert('Friendly Label, Hostname/IP, and Username are required.');
        return;
      }

      const payload = {
        label,
        host,
        port: isNaN(port) ? 22 : port,
        username,
        auth_type: authType,
        credential_id: credentialId || null,
        id: customId,
      };

      try {
        saveRemoteHostBtn.textContent = hostIdInput?.disabled ? 'Updating...' : 'Saving...';
        const res = await fetch('/api/remote_hosts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        if (hostLabelInput) hostLabelInput.value = '';
        if (hostIdInput) {
          hostIdInput.value = '';
          hostIdInput.disabled = false;
        }
        if (hostAddressInput) hostAddressInput.value = '';
        if (hostPortInput) hostPortInput.value = '22';
        if (hostUsernameInput) hostUsernameInput.value = '';
        if (hostCredentialSelect) hostCredentialSelect.value = '';
        if (remoteHostFormContainer) remoteHostFormContainer.classList.add('hidden');
        saveRemoteHostBtn.textContent = 'Save Remote Host';
        await loadRemoteHosts();
      } catch (err) {
        console.error('[AutoReiv UI] Failed to save remote host:', err);
        saveRemoteHostBtn.textContent = 'Error!';
        setTimeout(() => (saveRemoteHostBtn.textContent = 'Save Remote Host'), 2000);
      }
    });
  }

  return {
    loadCredentials,
    loadRemoteHosts,
  };
}
