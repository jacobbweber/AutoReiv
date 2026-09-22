/**
 * Agent Studio: Read-only runbook inspector & skill hierarchy [CARD-411].
 * Inspects SKILL.md metadata. Authoring and tool bindings live in Skill Studio.
 * Keeps the character budget, ADR-0054 lint view, and Platform/Pack skill rows.
 */

import { $, $queryAll, safeCreateIcons } from '../../dom.js';
import { escapeHtml } from '../../utils/formatters.js';
import { formatSafetyLabel } from '../../utils/skill_frontmatter.js';
import { showToast } from '../../ui/toast.js';
import { renderBaselineTools } from './tools.js';

export const CANONICAL_RUNBOOK_TEMPLATE = `# Operating Principles
1. Always verify assumptions against actual runtime state.
2. Structure output concisely with clear next steps.

## Available Tools
- \`activate_skill\`: Activate relevant procedural runbooks.

## Done-When
- Operational checks complete with zero errors.
- Verification criteria satisfied.
`;

let activeRunbookId = '';
let activeRunbookArchived = false;

export function getActiveRunbookId() {
  return activeRunbookId;
}

export function getActiveRunbookArchived() {
  return activeRunbookArchived;
}

export function skillRowHtml(skill, home, archived = false) {
  const id = skill.id || '';
  const name = skill.name || id;
  const desc = skill.description || '';
  const archivedAttr = archived ? ' data-archived="1"' : '';
  const checkbox = archived
    ? ''
    : `<input type="checkbox" value="${escapeHtml(id)}" class="forge-skill-checkbox rounded border-slate-700 text-brand-500 focus:ring-brand-500/20 bg-slate-950 h-4 w-4 shrink-0 mt-0.5" data-home="${escapeHtml(home)}">`;

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

  return `
    <div class="forge-skill-row rounded-lg bg-slate-900/60 border border-slate-800 p-2.5" data-skill-id="${escapeHtml(id)}" data-home="${escapeHtml(home)}">
      <div class="flex items-start gap-2">
        <label class="flex items-start space-x-2.5 flex-1 min-w-0 cursor-pointer">
          ${checkbox}
          <div class="flex-1 min-w-0">
            <span class="font-mono text-slate-200 inline text-[11px] font-semibold truncate">${escapeHtml(name)}</span>
            ${reqIndicator}
            <span class="text-slate-400 block text-[10px] line-clamp-2 leading-tight mt-0.5">${escapeHtml(desc)}</span>
          </div>
        </label>
        <div class="flex items-center space-x-1.5 shrink-0">
          <button type="button" class="studio-runbook-open-btn px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[10px] font-semibold text-brand-300 border border-slate-700 transition" data-pack-id="${escapeHtml(id)}"${archivedAttr}>Inspect</button>
        </div>
      </div>
      ${toolsChipsHtml}
    </div>
  `;
}

export function applySkillChecks(lastAllowedSkills = new Set()) {
  $queryAll('.forge-skill-checkbox').forEach((cb) => {
    cb.checked = lastAllowedSkills.has(cb.value);
  });
}

export function bindSkillRowHandlers(root, { onOpenRunbook = null } = {}) {
  if (!root) return;
  const forgeStorageEnabled = $('forgeStorageEnabled');
  const forgeStorageTypeContainer = $('forgeStorageTypeContainer');

  root.querySelectorAll('.studio-runbook-open-btn').forEach((btn) => {
    btn.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      const row = btn.closest('.forge-skill-row');
      const packId = btn.dataset.packId;
      const isArchived = btn.dataset.archived === '1';
      if (typeof onOpenRunbook === 'function') {
        onOpenRunbook(packId, isArchived, row);
      } else {
        openRunbookEditor(packId, isArchived, row);
      }
    });
  });
  root.querySelectorAll('.forge-skill-checkbox').forEach((cb) => {
    cb.addEventListener('change', () => {
      if (cb.value === 'sqlite-storage') {
        if (forgeStorageEnabled) forgeStorageEnabled.checked = cb.checked;
        if (forgeStorageTypeContainer) forgeStorageTypeContainer.classList.toggle('hidden', !cb.checked);
      }
    });
  });
}

export function setRunbookActionVisibility() {
  const studioRunbookOpenFactoryBtn = $('studioRunbookOpenFactoryBtn');
  if (studioRunbookOpenFactoryBtn) {
    studioRunbookOpenFactoryBtn.classList.toggle('hidden', !activeRunbookId);
  }
}

function renderInspectorTools(toolIds) {
  const studioRunbookTools = $('studioRunbookTools');
  if (!studioRunbookTools) return;
  const ids = Array.isArray(toolIds) ? toolIds.filter(Boolean) : [];
  if (!ids.length) {
    studioRunbookTools.innerHTML = '<span class="text-[10px] text-slate-500 italic">No required tools</span>';
    return;
  }
  studioRunbookTools.innerHTML = ids.map((toolId) => (
    `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-950 text-slate-300 border border-slate-800">${escapeHtml(toolId)}</span>`
  )).join('');
}

function lockRunbookFields() {
  ['studioRunbookName', 'studioRunbookBlurb', 'studioRunbookTier', 'studioRunbookSafety', 'studioRunbookBody'].forEach((id) => {
    const el = $(id);
    if (el) el.readOnly = true;
  });
}

export function updateRunbookCharCount() {
  const studioRunbookCharCount = $('studioRunbookCharCount');
  const studioRunbookBody = $('studioRunbookBody');
  if (!studioRunbookCharCount || !studioRunbookBody) return;
  const len = studioRunbookBody.value.length;
  const limit = 8000;
  studioRunbookCharCount.textContent = `${len.toLocaleString()} / ${limit.toLocaleString()} chars`;
  if (len > limit) {
    studioRunbookCharCount.classList.add('text-rose-400');
    studioRunbookCharCount.classList.remove('text-slate-500');
  } else {
    studioRunbookCharCount.classList.remove('text-rose-400');
    studioRunbookCharCount.classList.add('text-slate-500');
  }
}

export function clearRunbookLintStatus() {
  const studioRunbookLintStatus = $('studioRunbookLintStatus');
  if (!studioRunbookLintStatus) return;
  studioRunbookLintStatus.innerHTML = '';
  studioRunbookLintStatus.className = 'hidden rounded-lg p-2.5 text-xs transition-all';
}

export function renderRunbookLintReport(report) {
  const studioRunbookLintStatus = $('studioRunbookLintStatus');
  if (!studioRunbookLintStatus) return;
  studioRunbookLintStatus.classList.remove('hidden');

  if (report.valid && (!report.violations || report.violations.length === 0)) {
    studioRunbookLintStatus.className = 'rounded-lg p-3 text-xs bg-emerald-950/60 border border-emerald-700/60 text-emerald-200 transition-all flex items-center justify-between';
    const toolsCount = report.contract ? report.contract.tools_count : 0;
    studioRunbookLintStatus.innerHTML = `
      <div class="flex items-center space-x-2">
        <i data-lucide="check-circle-2" class="w-4 h-4 text-emerald-400 shrink-0"></i>
        <span class="font-medium">Runbook contract valid! Clean ADR-0054 compliance (${toolsCount} declared tool${toolsCount === 1 ? '' : 's'}).</span>
      </div>
      <span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-900/80 text-emerald-300 border border-emerald-600/50 uppercase">PASS</span>
    `;
    safeCreateIcons();
    return;
  }

  const errorCount = report.error_count || 0;
  const warnCount = report.warning_count || 0;
  const isError = errorCount > 0;

  studioRunbookLintStatus.className = isError
    ? 'rounded-lg p-3 text-xs bg-rose-950/60 border border-rose-700/60 text-rose-200 transition-all space-y-2'
    : 'rounded-lg p-3 text-xs bg-amber-950/60 border border-amber-700/60 text-amber-200 transition-all space-y-2';

  const header = `
    <div class="flex items-center justify-between border-b ${isError ? 'border-rose-800/80' : 'border-amber-800/80'} pb-1.5 mb-1.5">
      <div class="flex items-center space-x-2">
        <i data-lucide="${isError ? 'alert-octagon' : 'alert-triangle'}" class="w-4 h-4 ${isError ? 'text-rose-400' : 'text-amber-400'} shrink-0"></i>
        <span class="font-semibold">${isError ? 'Contract Violations Found' : 'Contract Warnings'} (${errorCount} error${errorCount === 1 ? '' : 's'}, ${warnCount} warning${warnCount === 1 ? '' : 's'})</span>
      </div>
      <span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${isError ? 'bg-rose-900/80 text-rose-300 border border-rose-600/50' : 'bg-amber-900/80 text-amber-300 border border-amber-600/50'} uppercase">${isError ? 'FAIL' : 'WARN'}</span>
    </div>
  `;

  const violationsList = (report.violations || []).map((v) => {
    const isErr = (v.severity || '').toLowerCase() === 'error';
    const badgeClass = isErr ? 'bg-rose-900/80 text-rose-300 border-rose-700/60' : 'bg-amber-900/80 text-amber-300 border-amber-700/60';
    return `
      <div class="flex items-start space-x-2 text-[11px] leading-snug">
        <span class="px-1 py-0.2 rounded font-mono font-bold text-[9px] border uppercase shrink-0 ${badgeClass}">${escapeHtml(v.rule_id || v.rule || 'LINT')}</span>
        <span class="text-slate-200 flex-1">${escapeHtml(v.message)}</span>
      </div>
    `;
  }).join('');

  studioRunbookLintStatus.innerHTML = `${header}<div class="space-y-1.5">${violationsList}</div>`;
  safeCreateIcons();
}

export async function validateActiveRunbook(isPreSave = false) {
  const studioRunbookName = $('studioRunbookName');
  const studioRunbookBlurb = $('studioRunbookBlurb');
  const studioRunbookBody = $('studioRunbookBody');
  const studioRunbookValidateBtn = $('studioRunbookValidateBtn');

  const name = studioRunbookName ? studioRunbookName.value.trim() : '';
  const description = studioRunbookBlurb ? studioRunbookBlurb.value.trim() : '';
  const instructions = studioRunbookBody ? studioRunbookBody.value : '';

  if (!instructions.trim()) {
    showToast('Runbook body cannot be empty', 'error');
    return false;
  }

  if (studioRunbookValidateBtn) {
    studioRunbookValidateBtn.disabled = true;
  }

  try {
    const res = await fetch('/api/skills/lint', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description, instructions }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || `HTTP ${res.status}`);
    }

    renderRunbookLintReport(data);

    if (!data.valid && !isPreSave) {
      showToast(`Runbook validation failed: ${data.error_count} error(s)`, 'error');
    } else if (data.valid && !isPreSave) {
      showToast('Runbook passed contract validation', 'success');
    }

    return data.valid;
  } catch (err) {
    showToast(`Lint check error: ${err.message || err}`, 'error');
    return false;
  } finally {
    if (studioRunbookValidateBtn) {
      studioRunbookValidateBtn.disabled = false;
    }
  }
}

export function hideRunbookEditor() {
  activeRunbookId = '';
  activeRunbookArchived = false;
  const studioRunbookEditor = $('studioRunbookEditor');
  const studioRunbookName = $('studioRunbookName');
  const studioRunbookBlurb = $('studioRunbookBlurb');
  const studioRunbookBody = $('studioRunbookBody');
  const studioRunbookPath = $('studioRunbookPath');

  if (studioRunbookEditor) studioRunbookEditor.classList.add('hidden');
  if (studioRunbookName) studioRunbookName.value = '';
  if (studioRunbookBlurb) studioRunbookBlurb.value = '';
  if (studioRunbookBody) studioRunbookBody.value = '';
  if (studioRunbookPath) studioRunbookPath.textContent = '';
  const studioRunbookTier = $('studioRunbookTier');
  const studioRunbookSafety = $('studioRunbookSafety');
  if (studioRunbookTier) studioRunbookTier.value = '';
  if (studioRunbookSafety) studioRunbookSafety.value = '';
  renderInspectorTools([]);
  clearRunbookLintStatus();
  updateRunbookCharCount();
  setRunbookActionVisibility();
}

export function applyRunbook(data, archivedHint, targetRow = null) {
  const studioRunbookEditor = $('studioRunbookEditor');
  const studioRunbookName = $('studioRunbookName');
  const studioRunbookBlurb = $('studioRunbookBlurb');
  const studioRunbookBody = $('studioRunbookBody');
  const studioRunbookPath = $('studioRunbookPath');

  const manifest = data.manifest || {};
  const frontmatter = data.frontmatter || {};
  activeRunbookId = manifest.id || activeRunbookId;
  activeRunbookArchived = Boolean(archivedHint || data.archived || manifest.origin === 'archived');
  lockRunbookFields();
  if (studioRunbookName) studioRunbookName.value = frontmatter.name || manifest.name || data.name || '';
  if (studioRunbookBlurb) studioRunbookBlurb.value = frontmatter.description || manifest.description || data.description || '';
  const studioRunbookTier = $('studioRunbookTier');
  const studioRunbookSafety = $('studioRunbookSafety');
  if (studioRunbookTier) studioRunbookTier.value = frontmatter.tier || 'pack';
  if (studioRunbookSafety) studioRunbookSafety.value = formatSafetyLabel(frontmatter.safety);
  renderInspectorTools(frontmatter.requires_tools || []);
  const bodyContent = data.instructions || '';
  if (studioRunbookBody) {
    studioRunbookBody.value = bodyContent || CANONICAL_RUNBOOK_TEMPLATE;
  }
  if (studioRunbookPath) studioRunbookPath.textContent = manifest.path || '';
  updateRunbookCharCount();
  clearRunbookLintStatus();
  if (studioRunbookEditor) {
    if (targetRow) {
      targetRow.after(studioRunbookEditor);
    }
    studioRunbookEditor.classList.remove('hidden');
    studioRunbookEditor.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
  setRunbookActionVisibility();
  safeCreateIcons();
}

export async function openRunbookEditor(packId, archived, targetRow = null) {
  if (!packId) return;
  try {
    const res = await fetch(`/api/skills/user-packs/${encodeURIComponent(packId)}`);
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `HTTP ${res.status}`);
    }
    const data = await res.json();
    applyRunbook(data, archived, targetRow);
  } catch (err) {
    showToast(String(err.message || err), 'error');
  }
}

export function renderPlatformSkills({
  cachedPlatformSkills = [],
  cachedArchivedSkills = [],
  lastAllowedSkills = new Set(),
  onOpenRunbook = null,
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
  bindSkillRowHandlers(forgeSkillsGrid, { onOpenRunbook });
  applySkillChecks(lastAllowedSkills);
}

export function renderPackSkills({
  activeForgeAgent = null,
  lastAllowedSkills = new Set(),
  onOpenRunbook = null,
} = {}) {
  const forgeRunbooksGrid = $('forgeRunbooksGrid');
  if (!forgeRunbooksGrid) return;
  const packSkills = (activeForgeAgent && activeForgeAgent.pack_skills) || [];
  const packHtml = packSkills.length
    ? packSkills.map((s) => skillRowHtml(s, 'pack', false)).join('')
    : '<p class="text-[10px] text-slate-500 px-1">No pack-owned skills yet.</p>';
  forgeRunbooksGrid.innerHTML = packHtml;
  bindSkillRowHandlers(forgeRunbooksGrid, { onOpenRunbook });
  applySkillChecks(lastAllowedSkills);
}

export function renderNestedHomes({
  cachedPlatformSkills = [],
  cachedArchivedSkills = [],
  activeForgeAgent = null,
  lastAllowedSkills = new Set(),
  onOpenRunbook = null,
} = {}) {
  renderBaselineTools();
  renderPlatformSkills({ cachedPlatformSkills, cachedArchivedSkills, lastAllowedSkills, onOpenRunbook });
  renderPackSkills({ activeForgeAgent, lastAllowedSkills, onOpenRunbook });
}

export async function loadPlatformSkills({
  cachedSkillsCatalog = null,
  activeForgeAgent = null,
  lastAllowedSkills = new Set(),
  onOpenRunbook = null,
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
    onOpenRunbook,
  });

  return { platformSkills, archivedSkills, catalog: updatedCatalog };
}

/**
 * Sets up the read-only runbook inspector, Factory handoff, validate, and input listeners [CARD-411].
 */
export function setupRunbookEditor({
  getActiveAgentId = null,
  openSkillStudio = null,
} = {}) {
  const studioRunbookCloseBtn = $('studioRunbookCloseBtn');
  const studioRunbookCancelBtn = $('studioRunbookCancelBtn');
  const studioRunbookValidateBtn = $('studioRunbookValidateBtn');
  const studioRunbookBody = $('studioRunbookBody');
  const studioRunbookOpenFactoryBtn = $('studioRunbookOpenFactoryBtn');
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

  if (studioRunbookCloseBtn) {
    studioRunbookCloseBtn.addEventListener('click', () => hideRunbookEditor());
  }

  if (studioRunbookCancelBtn) {
    studioRunbookCancelBtn.addEventListener('click', () => hideRunbookEditor());
  }

  if (studioRunbookValidateBtn) {
    studioRunbookValidateBtn.addEventListener('click', () => {
      validateActiveRunbook(false);
    });
  }

  if (studioRunbookBody) {
    studioRunbookBody.addEventListener('input', () => {
      updateRunbookCharCount();
    });
  }

  if (studioRunbookOpenFactoryBtn) {
    studioRunbookOpenFactoryBtn.addEventListener('click', () => {
      if (!activeRunbookId) {
        showToast('Open a runbook first', 'error');
        return;
      }
      const agentId = typeof getActiveAgentId === 'function' ? (getActiveAgentId() || '') : '';
      openSkillStudioWindow(agentId, activeRunbookId);
    });
  }

  if (studioOpenFactoryBtn) {
    studioOpenFactoryBtn.addEventListener('click', () => {
      const agentId = typeof getActiveAgentId === 'function' ? (getActiveAgentId() || '') : '';
      openSkillStudioWindow(agentId, null);
    });
  }

  return {
    openRunbookEditor,
    hideRunbookEditor,
    validateActiveRunbook,
    applyRunbook,
  };
}
