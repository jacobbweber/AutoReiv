/**
 * Agent Studio skill scoping pills [CARD-419].
 * On = skill id in the durable allowed_skill list. Off = absent.
 * Activating a pill never opens Skill Studio or a runbook editor.
 */

export const SKILL_PILL_ACTION = 'toggle-allowlist';

export function normalizeAllowedSkills(allowed) {
  const seen = new Set();
  const out = [];
  (allowed || []).forEach((raw) => {
    const id = String(raw || '').trim();
    if (!id || seen.has(id)) return;
    seen.add(id);
    out.push(id);
  });
  return out;
}

export function skillPillPressed(allowed, skillId) {
  const id = String(skillId || '').trim();
  if (!id) return false;
  return normalizeAllowedSkills(allowed).includes(id);
}

/**
 * Flip one skill in the allowlist. The result is the save payload slice.
 * opensEditor stays false: a pill is scope-only.
 */
export function toggleSkillInAllowlist(allowed, skillId) {
  const id = String(skillId || '').trim();
  const current = normalizeAllowedSkills(allowed);
  if (!id) {
    return {
      allowed_skill: current,
      pressed: false,
      skillId: '',
      action: SKILL_PILL_ACTION,
      opensEditor: false,
      opensSkillStudio: false,
      opensRunbook: false,
    };
  }
  const pressed = !current.includes(id);
  const next = pressed ? [...current, id] : current.filter((sid) => sid !== id);
  return {
    allowed_skill: next,
    pressed,
    skillId: id,
    action: SKILL_PILL_ACTION,
    opensEditor: false,
    opensSkillStudio: false,
    opensRunbook: false,
  };
}

/**
 * Storage-on forces sqlite-storage into the list, matching the existing Forge save path.
 */
export function allowlistForSave(allowed, { storageEnabled = false } = {}) {
  const skills = normalizeAllowedSkills(allowed);
  if (storageEnabled && !skills.includes('sqlite-storage')) {
    skills.push('sqlite-storage');
  }
  return skills;
}

/**
 * Pill on/off after a reload. Same adjustments Agent Studio already applied
 * when painting checkboxes: storage_enabled implies sqlite-storage;
 * allow_wiki_access false removes wiki.
 */
export function pillsFromPersistedAgent(agent) {
  const profile = agent || {};
  let allowed = normalizeAllowedSkills(profile.allowed_skill);
  if (profile.storage_enabled && !allowed.includes('sqlite-storage')) {
    allowed = [...allowed, 'sqlite-storage'];
  }
  if (profile.allow_wiki_access === false) {
    allowed = allowed.filter((id) => id !== 'wiki');
  }
  return allowed;
}

/**
 * Skill list for Save [CARD-509]: each pill decides for its own skill; a loaded skill
 * without a pill (no row in Studio) is kept exactly as loaded.
 */
export function skillsForSave(loaded, pillElements) {
  const pilled = new Set();
  (pillElements && typeof pillElements.forEach === 'function' ? pillElements : []).forEach((el) => {
    const id = String((el && el.dataset && el.dataset.skillId) || '').trim();
    if (id) pilled.add(id);
  });
  const pressed = pressedSkillIds(pillElements);
  const kept = normalizeAllowedSkills(loaded).filter((id) => !pilled.has(id) || pressed.includes(id));
  return normalizeAllowedSkills([...kept, ...pressed]);
}

export function pressedSkillIds(elements) {
  const ids = [];
  if (!elements || typeof elements.forEach !== 'function') return ids;
  elements.forEach((el) => {
    if (!el || typeof el.getAttribute !== 'function') return;
    if (el.getAttribute('aria-pressed') !== 'true') return;
    const id = String((el.dataset && el.dataset.skillId) || '').trim();
    if (id && !ids.includes(id)) ids.push(id);
  });
  return ids;
}

export function paintSkillPill(button, pressed) {
  if (!button || typeof button.setAttribute !== 'function') return false;
  const on = Boolean(pressed);
  button.setAttribute('aria-pressed', on ? 'true' : 'false');
  return on;
}

/**
 * Pill click updates pressed state and the allowlist callback only.
 * Extra open-editor callbacks are ignored so the control cannot grow a second job.
 */
export function applySkillPillToggle(button, { onToggleSkill } = {}) {
  const closed = {
    action: 'noop',
    opensEditor: false,
    opensSkillStudio: false,
    opensRunbook: false,
    skillId: '',
    pressed: false,
  };
  if (!button || typeof button.getAttribute !== 'function') return closed;
  if (button.dataset && button.dataset.archived === '1') return closed;
  const skillId = String((button.dataset && button.dataset.skillId) || '').trim();
  const nextOn = button.getAttribute('aria-pressed') !== 'true';
  paintSkillPill(button, nextOn);
  if (skillId && typeof onToggleSkill === 'function') onToggleSkill(skillId, nextOn);
  return {
    action: SKILL_PILL_ACTION,
    skillId,
    pressed: nextOn,
    opensEditor: false,
    opensSkillStudio: false,
    opensRunbook: false,
  };
}
