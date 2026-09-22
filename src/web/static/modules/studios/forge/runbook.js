/**
 * Agent Studio skill rows [CARD-411, CARD-419].
 * Toggle pills scope allowed_skill. Open in Skill Studio is the only skill detail link.
 * There is no inline runbook inspector in Agent Studio.
 */

import { $, $queryAll } from '../../dom.js';
import { escapeHtml } from '../../utils/formatters.js';
import { showToast } from '../../ui/toast.js';
import { renderBaselineTools } from './tools.js';
import { applySkillPillToggle, paintSkillPill } from './skill_pills.js';

export function skillRowHtml(skill, home, archived = false) {
  const id = skill.id || '';
  const name = skill.name || id;
  const desc = skill.description || '';
  const scopeControl = archived
    ? `<span class="inline-flex items-center px-2.5 py-1 rounded-full border border-slate-800 bg-slate-950/80 text-[11px] font-semibold text-slate-500" data-skill-id="${escapeHtml(id)}" data-archived="1">Archived</span>`
    : `<button type="button" class="forge-skill-pill inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-semibold transition bg-slate-900/70 border-slate-700 text-slate-400 aria-pressed:bg-emerald-950/80 aria-pressed:border-emerald-500/70 aria-pressed:text-emerald-100" role="switch" aria-pressed="false" data-skill-id="${escapeHtml(id)}" data-home="${escapeHtml(home)}" data-testid="forge-skill-pill" aria-label="Allow ${escapeHtml(name)} for this agent"><span class="w-1.5 h-1.5 rounded-full bg-current" aria-hidden="true"></span><span>${escapeHtml(name)}</span></button>`;

  const rawTools = Array.isArray(skill.tools) ? skill.tools : [];
  const toolNames = rawTools
    .map((t) => (typeof t === 'string' ? t : (t && t.name) || ''))
    .filter(Boolean);

  const hasRequired = rawTools.some(
    (t) => (typeof t === 'object' && t !== null && t.tier === 'required_platform')
  );
  const reqIndicator = hasRequired
    ? '<span class="ml-2 px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-amber-900/60 text-amber-300 border border-amber-600/40 uppercase">INCLUDES REQUIRED TOOLS</span>'
    : '';

  const toolsChipsHtml = toolNames.length
    ? `
      <div class="mt-2 pt-2 border-t border-slate-800/80 flex flex-wrap items-center gap-1.5">
        <span class="text-[9px] font-mono text-slate-500 uppercase tracking-wider">${toolNames.length} declared tool${toolNames.length === 1 ? '' : 's'}:</span>
        ${toolNames.map((tn) => {
          const tObj = rawTools.find((t) => (typeof t === 'string' ? t : t.name) === tn) || {};
          const isReq = tObj.tier === 'required_platform';
          const badge = isReq ? '<span class="ml-1 px-1 py-0.2 rounded text-[8px] font-mono font-bold bg-emerald-900/80 text-emerald-300 uppercase">REQUIRED</span>' : '';
          return `<span class="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[9px] font-mono bg-slate-950 text-slate-300 border border-slate-800"><i data-lucide="wrench" class="w-2.5 h-2.5 text-brand-400"></i><span>${escapeHtml(tn)}</span>${badge}</span>`;
        }).join('')}
      </div>
    `
    : '';

  const openStudio = archived
    ? ''
    : `<button type="button" class="forge-skill-open-studio px-2 py-1 rounded bg-transparent hover:bg-slate-800 text-[10px] font-semibold text-slate-400 hover:text-sky-300 border border-transparent hover:border-slate-700 transition" data-skill-id="${escapeHtml(id)}" data-testid="forge-skill-open-studio">Open in Skill Studio</button>`;

  return `
    <div class="forge-skill-row rounded-lg bg-slate-900/60 border border-slate-800 p-2.5" data-skill-id="${escapeHtml(id)}" data-home="${escapeHtml(home)}">
      <div class="flex items-start gap-2">
        <div class="flex items-start gap-2 flex-1 min-w-0">
          ${scopeControl}
          <div class="flex-1 min-w-0">
            ${archived ? `<span class="font-mono text-slate-400 inline text-[11px] font-semibold truncate">${escapeHtml(name)}</span>` : ''}
            ${reqIndicator}
            <span class="text-slate-400 block text-[10px] line-clamp-2 leading-tight mt-0.5">${escapeHtml(desc)}</span>
          </div>
        </div>
        <div class="flex items-center space-x-1.5 shrink-0">
          ${openStudio}
        </div>
      </div>
      ${toolsChipsHtml}
    </div>
  `;
}

export function applySkillChecks(lastAllowedSkills = new Set()) {
  const allowed = lastAllowedSkills instanceof Set
    ? lastAllowedSkills
    : new Set(lastAllowedSkills || []);
  $queryAll('.forge-skill-pill').forEach((btn) => {
    paintSkillPill(btn, allowed.has(btn.dataset.skillId || ''));
  });
}

export function bindSkillRowHandlers(root, {
  onToggleSkill = null,
  onOpenSkillStudio = null,
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
        },
      });
    });
  });
  root.querySelectorAll('.forge-skill-open-studio').forEach((btn) => {
    btn.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      const skillId = btn.dataset.skillId || '';
      if (typeof onOpenSkillStudio === 'function') onOpenSkillStudio(skillId);
    });
  });
}

function skillRowHandlerOpts(options = {}) {
  return {
    onToggleSkill: options.onToggleSkill || null,
    onOpenSkillStudio: options.onOpenSkillStudio || null,
  };
}

export function renderPlatformSkills({
  cachedPlatformSkills = [],
  cachedArchivedSkills = [],
  lastAllowedSkills = new Set(),
  onToggleSkill = null,
  onOpenSkillStudio = null,
} = {}) {
  const forgeSkillsGrid = $('forgeSkillsGrid');
  if (!forgeSkillsGrid) return;
  const platform = cachedPlatformSkills || [];
  const archived = cachedArchivedSkills || [];
  const platformHtml = platform.length
    ? platform.map((s) => skillRowHtml(s, 'platform', false)).join('')
    : '<p class="text-[10px] text-slate-500 px-1">No platform runbooks in the skills data dir.</p>';
  const archivedHtml = archived.length
    ? `<div class="space-y-2 pt-2"><h4 class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Archived</h4>${archived.map((s) => skillRowHtml(s, 'archived', true)).join('')}</div>`
    : '';
  forgeSkillsGrid.innerHTML = `${platformHtml}${archivedHtml}`;
  bindSkillRowHandlers(forgeSkillsGrid, skillRowHandlerOpts({ onToggleSkill, onOpenSkillStudio }));
  applySkillChecks(lastAllowedSkills);
}

export function renderPackSkills({
  activeForgeAgent = null,
  lastAllowedSkills = new Set(),
  onToggleSkill = null,
  onOpenSkillStudio = null,
} = {}) {
  const forgeRunbooksGrid = $('forgeRunbooksGrid');
  if (!forgeRunbooksGrid) return;
  const packSkills = (activeForgeAgent && activeForgeAgent.pack_skills) || [];
  const packHtml = packSkills.length
    ? packSkills.map((s) => skillRowHtml(s, 'pack', false)).join('')
    : '<p class="text-[10px] text-slate-500 px-1">No pack-owned skills yet.</p>';
  forgeRunbooksGrid.innerHTML = packHtml;
  bindSkillRowHandlers(forgeRunbooksGrid, skillRowHandlerOpts({ onToggleSkill, onOpenSkillStudio }));
  applySkillChecks(lastAllowedSkills);
}

export function renderNestedHomes({
  cachedPlatformSkills = [],
  cachedArchivedSkills = [],
  activeForgeAgent = null,
  lastAllowedSkills = new Set(),
  onToggleSkill = null,
  onOpenSkillStudio = null,
} = {}) {
  renderBaselineTools();
  renderPlatformSkills({
    cachedPlatformSkills,
    cachedArchivedSkills,
    lastAllowedSkills,
    onToggleSkill,
    onOpenSkillStudio,
  });
  renderPackSkills({
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
  let archivedSkills = [];
  let updatedCatalog = cachedSkillsCatalog;
  try {
    if (cachedSkillsCatalog && Array.isArray(cachedSkillsCatalog.platform_skills)) {
      platformSkills = cachedSkillsCatalog.platform_skills;
    } else {
      const catRes = await fetch('/api/skills/catalog');
      if (catRes.ok) {
        const catData = await catRes.json();
        updatedCatalog = catData;
        platformSkills = catData.platform_skills || [];
      }
    }
    const archRes = await fetch('/api/skills/archived-packs');
    if (archRes.ok) {
      const archData = await archRes.json();
      archivedSkills = archData.packs || [];
    }
  } catch (e) {
    console.warn('[AutoReiv UI] Failed to load platform skills:', e);
  }

  if (typeof onLoaded === 'function') {
    onLoaded({ platformSkills, archivedSkills, catalog: updatedCatalog });
  }

  renderNestedHomes({
    cachedPlatformSkills: platformSkills,
    cachedArchivedSkills: archivedSkills,
    activeForgeAgent,
    lastAllowedSkills,
    onToggleSkill,
    onOpenSkillStudio,
  });

  return { platformSkills, archivedSkills, catalog: updatedCatalog };
}

/**
 * Section-level Open in Skill Studio. Per-skill links are bound on each pill row [CARD-419].
 */
export function setupRunbookEditor({
  getActiveAgentId = null,
  openSkillStudio = null,
} = {}) {
  const studioOpenFactoryBtn = $('studioOpenFactoryBtn');

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

  if (studioOpenFactoryBtn) {
    studioOpenFactoryBtn.addEventListener('click', () => {
      const agentId = typeof getActiveAgentId === 'function' ? (getActiveAgentId() || '') : '';
      openSkillStudioWindow(agentId, null);
    });
  }
}
