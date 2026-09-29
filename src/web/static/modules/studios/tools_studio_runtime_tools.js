/**
 * CARD-570: runtime-built tools live in the data dir (tools/<name>/). An agent can save one, but it is
 * only mounted once Jacob enables it here; new code changes the hash and needs re-approval.
 * These buttons are the only caller of /api/tools/native/<name>/enable and /disable.
 * CARD-571: Jacob reads the code here, sees what it can reach (network, files, programs), and
 * enabling also accepts the tool's pending attach proposal.
 */

export function runtimeToolApprovalText(row) {
  const state = row && row.approval;
  if (state === 'enabled') return 'Enabled (approved code).';
  if (state === 'needs_reapproval') return 'Code changed since you approved it. Not mounted until you approve again.';
  return 'Not enabled. No agent can use it until you enable it.';
}

/** What enabling will also do: attach proposals it accepts [CARD-571 D5]. */
export function runtimeToolAttachText(row) {
  const items = (row && Array.isArray(row.pending_attach)) ? row.pending_attach : [];
  if (!items.length) return '';
  const parts = items.map((p) => `${p.agent_id} (skill ${p.skill_id})`);
  return `Enabling also gives it to: ${parts.join(', ')}.`;
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
      const attached = (data && Array.isArray(data.accepted_attach)) ? data.accepted_attach : [];
      const extra = attached.length ? ` Also gave it to ${attached.map((a) => a.agent_id).join(', ')}.` : '';
      if (data && data.attach_error) toast(data.attach_error, 'error');
      toast(`${okMsg}${extra}`, 'success');
      await refresh();
      await onChanged();
    } catch (err) {
      toast(`Failed: ${err.message || err}`, 'error');
    }
  }

  async function toggleCode(id, box) {
    if (!box.classList.contains('hidden')) {
      box.classList.add('hidden');
      return;
    }
    try {
      const resp = await fetchImpl(`/api/tools/native/${id}`);
      const data = await resp.json().catch(() => ({}));
      box.textContent = resp.ok ? String(data.code || '') : `Could not load the code (HTTP ${resp.status}).`;
    } catch (err) {
      box.textContent = `Could not load the code: ${err.message || err}`;
    }
    box.classList.remove('hidden');
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
      const codeBox = document.createElement('pre');
      codeBox.className = 'hidden w-full max-h-64 overflow-auto rounded-lg bg-slate-950/80 border border-slate-700 p-2 text-[11px] text-slate-200 font-mono whitespace-pre';
      codeBox.dataset.testid = `runtime-tool-code-${name}`;
      line.append(button('Show code', `runtime-tool-show-code-${name}`, () => toggleCode(id, codeBox)));
      if (row.approval === 'enabled') {
        line.append(button('Disable', `runtime-tool-disable-${name}`, () => post(`/api/tools/native/${id}/disable`, `${name} is disabled.`)));
      } else {
        const verb = row.approval === 'needs_reapproval' ? 'Approve new code' : 'Enable';
        line.append(button(verb, `runtime-tool-enable-${name}`, () => post(`/api/tools/native/${id}/enable`, `${name} is enabled.`)));
      }
      const warning = String(row.access_warning || '');
      if (warning) {
        const warn = document.createElement('p');
        warn.className = 'w-full text-[11px] text-amber-300';
        warn.dataset.testid = `runtime-tool-access-${name}`;
        warn.textContent = `Warning: ${warning}`;
        line.append(warn);
      }
      const attach = runtimeToolAttachText(row);
      if (attach && row.approval !== 'enabled') {
        const note = document.createElement('p');
        note.className = 'w-full text-[11px] text-slate-400';
        note.dataset.testid = `runtime-tool-attach-${name}`;
        note.textContent = attach;
        line.append(note);
      }
      line.append(codeBox);
      host.append(line);
    });
  }

  return { refresh };
}
