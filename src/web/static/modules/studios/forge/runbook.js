/**
 * Agent Studio skill rows [CARD-411, CARD-419, CARD-430, CARD-656].
 * Each row is the skill name, a one-line description and an on/off switch that scopes allowed_skill.
 * Rows sit in two groups, Enabled and Available, each sorted by name; a search box filters both.
 * Skill Studio is reached from the section header's "Manage skills" link only.
 */

import { $, $queryAll } from '../../dom.js';
import { escapeHtml } from '../../utils/formatters.js';
import { showToast } from '../../ui/toast.js';
import { renderBaselineTools } from './tools.js';
import { applySkillPillToggle, paintSkillPill } from './skill_pills.js';

const SKILL_HOME_LABELS = {
  platform: 'Platform',
  operator: 'Operator',
  agent: 'Agent',
};

export function skillHomeLabel(home) {
  return SKILL_HOME_LABELS[home] || '';
}

function oneLine(text) {
  return String(text || '').split(/\r?\n/).map((s) => s.trim()).find(Boolean) || '';
}

function skillSortKey(skill) {
  return String((skill && (skill.name || skill.id)) || '').toLowerCase();
}

function byName(a, b) {
  return skillSortKey(a).localeCompare(skillSortKey(b)) || String(a.id).localeCompare(String(b.id));
}

/** "4 of 12 enabled" [CARD-656]. */
export function skillCountText(enabled, total) {
  return `${Number(enabled) || 0} of ${Number(total) || 0} enabled`;
}

/** True when the skill's name or description contains the query (case-insensitive); empty query matches all. */
export function skillMatchesSearch(skill, query) {
  const q = String(query || '').trim().toLowerCase();
  if (!q) return true;
  const s = skill || {};
  return skillSearchText(s).includes(q);
}

/** What the search box matches: the name, the id and the one description line the row shows. */
function skillSearchText(skill) {
  const s = skill || {};
  return `${s.name || ''} ${s.id || ''} ${oneLine(s.description)}`.toLowerCase();
}

/**
 * One row: name, one-line description, switch on the right [CARD-656].
 * The switch keeps the CARD-419 contract (.forge-skill-pill, role=switch, aria-pressed, data-skill-id)
 * so Save reads it exactly as before.
 */
export function skillRowHtml(skill, home, archived = false, pressed = false) {
  const id = escapeHtml(skill.id || '');
  const name = escapeHtml(skill.name || skill.id || '');
  const desc = escapeHtml(oneLine(skill.description));
  const control = archived
    ? `<span class="forge-skill-archived-tag" data-skill-id="${id}" data-archived="1" data-testid="forge-skill-archived">Archived</span>`
    : `<button type="button" class="forge-skill-pill forge-skill-switch" role="switch" aria-pressed="${pressed ? 'true' : 'false'}" data-skill-id="${id}" data-home="${escapeHtml(home)}" data-testid="forge-skill-pill" aria-label="Enable ${name} for this agent"><span class="forge-skill-switch-knob" aria-hidden="true"></span></button>`;
  return `<div class="forge-skill-row" data-skill-id="${id}" data-home="${escapeHtml(home)}" data-search="${escapeHtml(skillSearchText(skill))}">
      <div class="forge-skill-text">
        <div class="forge-skill-name" data-testid="forge-skill-name">${name}</div>
        ${desc ? `<div class="forge-skill-desc" data-testid="forge-skill-desc" title="${desc}">${desc}</div>` : ''}
      </div>
      ${control}
    </div>`;
}

export function applySkillChecks(lastAllowedSkills = new Set()) {
  const allowed = lastAllowedSkills instanceof Set
    ? lastAllowedSkills
    : new Set(lastAllowedSkills || []);
  $queryAll('.forge-skill-pill').forEach((btn) => {
    paintSkillPill(btn, allowed.has(btn.dataset.skillId || ''));
  });
  regroupSkillRows();
}

/**
 * Put each row in the group that matches its switch, keep both groups sorted by name and update
 * the count [CARD-656]. `moved` (a skill id) gets a brief highlight so a toggled row is easy to find.
 */
export function regroupSkillRows(root = null, moved = '') {
  const grid = root || $('forgeSkillsGrid');
  if (!grid || typeof grid.querySelector !== 'function') return;
  const enabledList = grid.querySelector('[data-skill-group-list="enabled"]');
  const availableList = grid.querySelector('[data-skill-group-list="available"]');
  if (!enabledList || !availableList) return;
  const rows = [...grid.querySelectorAll('.forge-skill-row')].filter((row) => row.querySelector('.forge-skill-pill'));
  const name = (row) => (row.querySelector('.forge-skill-name')?.textContent || '').toLowerCase();
  rows.sort((a, b) => name(a).localeCompare(name(b)));
  let enabled = 0;
  rows.forEach((row) => {
    const on = row.querySelector('.forge-skill-pill').getAttribute('aria-pressed') === 'true';
    if (on) enabled += 1;
    (on ? enabledList : availableList).appendChild(row);
  });
  grid.querySelectorAll('[data-skill-group-empty]').forEach((el) => {
    const list = el.dataset.skillGroupEmpty === 'enabled' ? enabledList : availableList;
    el.classList.toggle('hidden', list.querySelector('.forge-skill-row') !== null);
  });
  const count = $('forgeSkillCount');
  if (count) count.textContent = skillCountText(enabled, rows.length);
  if (moved) {
    const row = rows.find((r) => r.dataset.skillId === moved);
    if (row) {
      row.classList.remove('forge-skill-row-moved');
      void row.offsetWidth; // restart the highlight
      row.classList.add('forge-skill-row-moved');
      setTimeout(() => row.classList.remove('forge-skill-row-moved'), 1600);
      if (typeof row.scrollIntoView === 'function') row.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }
  filterSkillRows(grid);
}

/** Show only rows matching the search box (both groups) [CARD-656]. */
export function filterSkillRows(root = null, query = null) {
  const grid = root || $('forgeSkillsGrid');
  if (!grid || typeof grid.querySelectorAll !== 'function') return;
  const input = $('forgeSkillSearch');
  const q = String(query !== null ? query : (input ? input.value : '')).trim().toLowerCase();
  let shown = 0;
  grid.querySelectorAll('.forge-skill-row').forEach((row) => {
    const hit = !q || (row.dataset.search || '').includes(q);
    row.classList.toggle('hidden', !hit);
    if (hit) shown += 1;
  });
  const none = grid.querySelector('[data-testid="forge-skill-no-match"]');
  if (none) none.classList.toggle('hidden', !q || shown > 0);
}

// CARD-656: no per-row Skill Studio link; the header's Manage skills opens Skill Studio.
export function bindSkillRowHandlers(root, {
  onToggleSkill = null,
} = {}) {
  if (!root) return;
  const forgeStorageEnabled = $('forgeStorageEnabled');
  const forgeStorageTypeContainer = $('forgeStorageTypeContainer');

  root.querySelectorAll('.forge-skill-pill').forEach((btn) => {
    btn.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      applySkillPillToggle(btn, {
        onToggleSkill: (skillId, pressed) => {
          if (skillId === 'sqlite-storage') {
            if (forgeStorageEnabled) forgeStorageEnabled.checked = pressed;
            if (forgeStorageTypeContainer) forgeStorageTypeContainer.classList.toggle('hidden', !pressed);
          }
          if (typeof onToggleSkill === 'function') onToggleSkill(skillId, pressed);
          regroupSkillRows(root, skillId);
        },
      });
    });
  });
}

function skillRowHandlerOpts(options = {}) {
  return {
    onToggleSkill: options.onToggleSkill || null,
  };
}

/** Enabled / Available / Archived rows, each sorted by name [CARD-656]. */
export function skillListModel({
  platformSkills = [],
  operatorSkills = [],
  ownSkillRows = [],
  archivedSkills = [],
  allowed = [],
} = {}) {
  const on = allowed instanceof Set ? allowed : new Set(allowed || []);
  const seen = new Set();
  const live = [];
  const add = (skill, home) => {
    if (!skill || !skill.id || seen.has(skill.id)) return;
    seen.add(skill.id);
    live.push({ ...skill, home });
  };
  (platformSkills || []).forEach((s) => add(s, 'platform'));
  (operatorSkills || []).map(operatorSkillPillModel).forEach((s) => add(s, 'operator'));
  (ownSkillRows || []).forEach((s) => add(s, 'agent'));
  const archived = (archivedSkills || []).filter((s) => s && s.id && !seen.has(s.id)).sort(byName);
  const enabled = live.filter((s) => on.has(s.id)).sort(byName);
  const available = live.filter((s) => !on.has(s.id)).sort(byName);
  return { enabled, available, archived, enabledCount: enabled.length, total: live.length };
}

function skillGroupHtml(key, title, skills) {
  const rows = skills.map((s) => skillRowHtml(s, s.home, false, key === 'enabled')).join('');
  const empty = key === 'enabled' ? 'No skills enabled for this agent.' : 'Every skill is enabled.';
  return `<div class="forge-skill-group" data-testid="forge-skill-group-${key}">
      <h4 class="forge-skill-group-title">${title}</h4>
      <div class="forge-skill-group-list" data-skill-group-list="${key}">${rows}</div>
      <p class="forge-skill-group-empty${skills.length ? ' hidden' : ''}" data-skill-group-empty="${key}">${empty}</p>
    </div>`;
}

export function assignedSkillListHtml({
  platformSkills = [],
  operatorSkills = [],
  ownSkillRows = [],
  archivedSkills = [],
  allowed = [],
} = {}) {
  const model = skillListModel({ platformSkills, operatorSkills, ownSkillRows, archivedSkills, allowed });
  if (!model.total && !model.archived.length) {
    return '<p class="text-[10px] text-slate-500 px-1" data-testid="forge-skills-empty">No skills for this agent yet.</p>';
  }
  const archived = model.archived.length
    ? `<details class="forge-skill-group forge-skill-archived-group" data-testid="forge-skill-group-archived">
        <summary class="forge-skill-group-title">Archived (${model.archived.length})</summary>
        <div class="forge-skill-group-list">${model.archived.map((s) => skillRowHtml(s, 'archived', true)).join('')}</div>
      </details>`
    : '';
  return [
    skillGroupHtml('enabled', 'Enabled', model.enabled),
    skillGroupHtml('available', 'Available', model.available),
    '<p class="forge-skill-group-empty hidden" data-testid="forge-skill-no-match">No skills match your search.</p>',
    archived,
  ].join('');
}

export function renderAssignedSkills({
  cachedPlatformSkills = [],
  cachedOperatorSkills = [],
  cachedArchivedSkills = [],
  activeForgeAgent = null,
  lastAllowedSkills = new Set(),
  onToggleSkill = null,
  onOpenSkillStudio = null,
} = {}) {
  const forgeSkillsGrid = $('forgeSkillsGrid');
  if (!forgeSkillsGrid) return;
  const ownSkillRows = (activeForgeAgent && activeForgeAgent.own_skills) || [];
  forgeSkillsGrid.innerHTML = assignedSkillListHtml({
    platformSkills: cachedPlatformSkills,
    operatorSkills: cachedOperatorSkills,
    ownSkillRows,
    archivedSkills: cachedArchivedSkills,
    allowed: lastAllowedSkills,
  });
  bindSkillRowHandlers(forgeSkillsGrid, skillRowHandlerOpts({ onToggleSkill, onOpenSkillStudio }));
  applySkillChecks(lastAllowedSkills);
}

export function operatorSkillPillModel(row) {
  const source = row && typeof row === 'object' ? row : {};
  const id = String(source.id || '').trim();
  const tools = Array.isArray(source.tools)
    ? source.tools.map((item) => String((item && item.name) || item || '').trim()).filter(Boolean)
    : [];
  return {
    id,
    name: String(source.name || id),
    description: String(source.description || ''),
    tools,
  };
}

export function renderNestedHomes({
  cachedPlatformSkills = [],
  cachedOperatorSkills = [],
  cachedArchivedSkills = [],
  activeForgeAgent = null,
  lastAllowedSkills = new Set(),
  onToggleSkill = null,
  onOpenSkillStudio = null,
} = {}) {
  renderBaselineTools();
  renderAssignedSkills({
    cachedPlatformSkills,
    cachedOperatorSkills,
    cachedArchivedSkills,
    activeForgeAgent,
    lastAllowedSkills,
    onToggleSkill,
    onOpenSkillStudio,
  });
}

export async function loadPlatformSkills({
  cachedSkillsCatalog = null,
  activeForgeAgent = null,
  lastAllowedSkills = new Set(),
  onToggleSkill = null,
  onOpenSkillStudio = null,
  onLoaded = null,
} = {}) {
  let platformSkills = [];
  let operatorSkills = [];
  let archivedSkills = [];
  let updatedCatalog = cachedSkillsCatalog;
  try {
    if (cachedSkillsCatalog && Array.isArray(cachedSkillsCatalog.platform_skills)) {
      platformSkills = cachedSkillsCatalog.platform_skills;
      operatorSkills = Array.isArray(cachedSkillsCatalog.operator_skills)
        ? cachedSkillsCatalog.operator_skills
        : [];
    } else {
      const catRes = await fetch('/api/skills/catalog');
      if (catRes.ok) {
        const catData = await catRes.json();
        updatedCatalog = catData;
        platformSkills = catData.platform_skills || [];
        operatorSkills = catData.operator_skills || [];
      }
    }
    const archRes = await fetch('/api/skills/archived-skills');
    if (archRes.ok) {
      const archData = await archRes.json();
      archivedSkills = archData.skills || [];
    }
  } catch (e) {
    console.warn('[AutoReiv UI] Failed to load platform skills:', e);
  }

  if (typeof onLoaded === 'function') {
    onLoaded({ platformSkills, operatorSkills, archivedSkills, catalog: updatedCatalog });
  }

  renderNestedHomes({
    cachedPlatformSkills: platformSkills,
    cachedOperatorSkills: operatorSkills,
    cachedArchivedSkills: archivedSkills,
    activeForgeAgent,
    lastAllowedSkills,
    onToggleSkill,
    onOpenSkillStudio,
  });

  return { platformSkills, operatorSkills, archivedSkills, catalog: updatedCatalog };
}

/**
 * Header "Manage skills" opens Skill Studio; the search box filters both groups [CARD-419, CARD-656].
 */
export function setupRunbookEditor({
  getActiveAgentId = null,
  openSkillStudio = null,
} = {}) {
  const studioOpenSkillStudioBtn = $('studioOpenSkillStudioBtn');

  function openSkillStudioWindow(agentId, skillId) {
    if (typeof openSkillStudio === 'function') {
      openSkillStudio(agentId || '', skillId || null);
      return;
    }
    if (typeof window !== 'undefined' && typeof window.openSkillStudioForSkill === 'function') {
      window.openSkillStudioForSkill({ agentId: agentId || '', skillId: skillId || null });
      return;
    }
    showToast('Skill Studio is not ready yet', 'error');
  }

  const forgeSkillSearch = $('forgeSkillSearch');
  if (forgeSkillSearch) {
    forgeSkillSearch.addEventListener('input', () => filterSkillRows(null, forgeSkillSearch.value));
  }

  if (studioOpenSkillStudioBtn) {
    studioOpenSkillStudioBtn.addEventListener('click', () => {
      const agentId = typeof getActiveAgentId === 'function' ? (getActiveAgentId() || '') : '';
      openSkillStudioWindow(agentId, null);
    });
  }
}
