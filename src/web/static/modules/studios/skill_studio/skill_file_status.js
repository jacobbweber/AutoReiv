/**
 * CARD-570: Skill Studio file status. Shipped skills live in platform/skills; a save writes a user copy
 * in the data dir that wins. "Use shipped version" deletes that copy; "Hide skill" hides a shipped skill
 * (it grants no tools); hidden skills are listed with Unhide.
 */

export function skillFileStatusText(status) {
  if (!status) return '';
  if (status.hidden) return 'Hidden shipped skill. It grants no tools until you unhide it.';
  if (status.edited && status.shipped_changed) return 'Edited copy of a shipped skill. The shipped version changed since you edited this.';
  if (status.edited) return 'Edited copy of a shipped skill.';
  if (status.shipped) return 'Shipped skill.';
  return 'Your skill.';
}

export function mountSkillFileStatus({ host, fetchImpl = (...a) => fetch(...a), toast = () => {}, onChanged = async () => {} }) {
  if (!host) return { render: () => {}, refreshHidden: async () => {} };
  const text = document.createElement('p');
  text.className = 'text-[11px] text-slate-300';
  text.dataset.testid = 'skill-file-status-text';
  const buttons = document.createElement('div');
  buttons.className = 'flex flex-wrap gap-2';
  const hiddenList = document.createElement('div');
  hiddenList.className = 'flex flex-wrap gap-2 text-[11px] text-slate-400';
  hiddenList.dataset.testid = 'skill-hidden-list';
  host.append(text, buttons, hiddenList);

  async function post(url, okMsg) {
    try {
      const resp = await fetchImpl(url, { method: 'POST' });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) throw new Error((data && data.detail) || `HTTP ${resp.status}`);
      toast(okMsg, 'success');
      await onChanged();
      await refreshHidden();
      return true;
    } catch (err) {
      toast(`Failed: ${err.message || err}`, 'error');
      return false;
    }
  }

  function button(label, testid, onClick) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = label;
    b.dataset.testid = testid;
    b.className = 'px-2.5 py-1 rounded-lg border border-sky-700/50 text-sky-200 hover:bg-sky-900/30 text-[11px]';
    b.addEventListener('click', onClick);
    return b;
  }

  function render(status, skillId) {
    buttons.replaceChildren();
    text.textContent = skillFileStatusText(status);
    host.classList.toggle('hidden', !status && !hiddenList.childElementCount);
    if (!status || !skillId) return;
    const id = encodeURIComponent(skillId);
    if (status.edited) {
      buttons.append(button('Use shipped version', 'skill-use-shipped', () => post(`/api/skill_studio/skills/${id}/use-shipped`, `${skillId} is back to the shipped version.`)));
    }
    if (status.shipped && !status.hidden) {
      buttons.append(button('Hide skill', 'skill-hide', () => post(`/api/skill_studio/skills/${id}/hide`, `${skillId} is hidden.`)));
    }
    if (status.hidden) {
      buttons.append(button('Unhide', 'skill-unhide', () => post(`/api/skill_studio/skills/${id}/unhide`, `${skillId} is shown again.`)));
    }
  }

  async function refreshHidden() {
    try {
      const resp = await fetchImpl('/api/skill_studio/hidden-skills');
      const data = await resp.json().catch(() => ({}));
      const ids = (data && data.hidden) || [];
      hiddenList.replaceChildren();
      if (ids.length) {
        const label = document.createElement('span');
        label.textContent = 'Hidden skills:';
        hiddenList.append(label);
        ids.forEach((sid) => hiddenList.append(button(`Unhide ${sid}`, `skill-unhide-${sid}`, () => post(`/api/skill_studio/skills/${encodeURIComponent(sid)}/unhide`, `${sid} is shown again.`))));
        host.classList.remove('hidden');
      }
    } catch {
      /* the list is optional */
    }
  }

  return { render, refreshHidden };
}
