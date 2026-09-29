/**
 * CARD-570: runtime-built tools live in the data dir (tools/<name>/). An agent can save one, but it is
 * only mounted once Jacob enables it here; new code changes the hash and needs re-approval.
 * These buttons are the only caller of /api/tools/native/<name>/enable and /disable.
 */

export function runtimeToolApprovalText(row) {
  const state = row && row.approval;
  if (state === 'enabled') return 'Enabled (approved code).';
  if (state === 'needs_reapproval') return 'Code changed since you approved it. Not mounted until you approve again.';
  return 'Not enabled. No agent can use it until you enable it.';
}

export function mountRuntimeTools({ host, fetchImpl = (...a) => fetch(...a), toast = () => {}, onChanged = async () => {} }) {
  if (!host) return { refresh: async () => {} };

  function button(label, testid, onClick) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = label;
    b.dataset.testid = testid;
    b.className = 'px-2.5 py-1 rounded-lg border border-cyan-700/50 text-cyan-200 hover:bg-cyan-900/30 text-[11px]';
    b.addEventListener('click', onClick);
    return b;
  }

  async function post(url, okMsg) {
    try {
      const resp = await fetchImpl(url, { method: 'POST' });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) throw new Error((data && data.detail && (data.detail.message || data.detail)) || `HTTP ${resp.status}`);
      toast(okMsg, 'success');
      await refresh();
      await onChanged();
    } catch (err) {
      toast(`Failed: ${err.message || err}`, 'error');
    }
  }

  async function refresh() {
    let rows;
    try {
      const resp = await fetchImpl('/api/tools/native');
      const data = resp && resp.ok ? await resp.json() : {};
      rows = (data && Array.isArray(data.tools)) ? data.tools : [];
    } catch {
      rows = [];
    }
    host.replaceChildren();
    host.classList.toggle('hidden', rows.length === 0);
    if (!rows.length) return;
    const title = document.createElement('p');
    title.className = 'text-[11px] font-semibold text-slate-200';
    title.textContent = 'Runtime-built tools';
    host.append(title);
    rows.forEach((row) => {
      const name = String(row.name || '');
      const line = document.createElement('div');
      line.className = 'flex flex-wrap items-center gap-2 text-[11px] text-slate-300';
      line.dataset.testid = `runtime-tool-${name}`;
      const label = document.createElement('span');
      label.className = 'font-mono text-slate-100';
      label.textContent = name;
      const state = document.createElement('span');
      state.textContent = runtimeToolApprovalText(row);
      line.append(label, state);
      const id = encodeURIComponent(name);
      if (row.approval === 'enabled') {
        line.append(button('Disable', `runtime-tool-disable-${name}`, () => post(`/api/tools/native/${id}/disable`, `${name} is disabled.`)));
      } else {
        const verb = row.approval === 'needs_reapproval' ? 'Approve new code' : 'Enable';
        line.append(button(verb, `runtime-tool-enable-${name}`, () => post(`/api/tools/native/${id}/enable`, `${name} is enabled.`)));
      }
      host.append(line);
    });
  }

  return { refresh };
}
