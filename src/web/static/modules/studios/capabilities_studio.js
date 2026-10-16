/**
 * Unified Capabilities Directory Tree Studio [CARD-690, ADR-0065 Slice 4].
 * Browse Agora `skills/<id>/` folders (`SKILL.md`, `references/*.md`, `tools/*.py`),
 * inspect/edit files in place, and toggle colocated Python tools on or off.
 */

import { $, escapeHtml, safeCreateIcons } from '../dom.js';
import { api } from '../services/api.js';
import { showToast } from '../ui/toast.js';
import {
  defaultReferenceMarkdown,
  defaultSkillMarkdown,
  defaultToolPython,
  filterCapabilitiesTree,
  normalizeSkillEntry,
  renderCapabilitiesTreeHtml,
  renderToolStatusCardHtml,
} from './capabilities_tree_model.js';

export const CAPABILITIES_STUDIO_TAB = 'capabilities';
export const CAPABILITIES_STUDIO_LABEL = 'Capabilities';

/**
 * Plan a deep link into the Capabilities directory tree studio.
 * @param {{ skillId?: string|null, filePath?: string|null }} [opts]
 */
export function planCapabilitiesStudioDeepLink({ skillId = null, filePath = null } = {}) {
  const cleanSkill = String(skillId || '').trim();
  const cleanPath = String(filePath || '').trim() || (cleanSkill ? 'SKILL.md' : '');
  return {
    tab: CAPABILITIES_STUDIO_TAB,
    label: CAPABILITIES_STUDIO_LABEL,
    skillId: cleanSkill || null,
    filePath: cleanPath || null,
  };
}

export function initCapabilitiesStudio(_state, _callbacks = {}) {
  const treeListEl = $('capabilitiesTreeList');
  const searchInputEl = $('capabilitiesTreeSearch');
  const refreshBtnEl = $('capabilitiesRefreshBtn');
  const newSkillBtnEl = $('capabilitiesNewSkillBtn');
  const createBarEl = $('capabilitiesCreateBar');
  const createKindLabelEl = $('capabilitiesCreateKindLabel');
  const createInputEl = $('capabilitiesCreateNameInput');
  const createConfirmBtnEl = $('capabilitiesCreateConfirmBtn');
  const createCancelBtnEl = $('capabilitiesCreateCancelBtn');
  const activePathEl = $('capabilitiesActivePath');
  const activeSourceBadgeEl = $('capabilitiesActiveSourceBadge');
  const feedbackEl = $('capabilitiesFeedbackBanner');
  const toolStatusCardEl = $('capabilitiesToolStatusCard');
  const editorEl = $('capabilitiesFileEditor');
  const saveBtnEl = $('capabilitiesSaveFileBtn');

  let skillsTree = [];
  const expandedSkills = new Set();
  let selectedSkillId = '';
  let selectedFilePath = 'SKILL.md';
  let pendingCreateMode = null; // { kind: 'skill' | 'reference' | 'tool', skillId?: string }
  let queuedDeepLink = null;

  function setFeedback(message, kind = 'info') {
    if (!feedbackEl) return;
    if (!message) {
      feedbackEl.classList.add('hidden');
      feedbackEl.textContent = '';
      return;
    }
    feedbackEl.classList.remove('hidden');
    if (kind === 'ok') {
      feedbackEl.className =
        'px-3 py-2 rounded-xl border border-emerald-700/60 bg-emerald-950/50 text-emerald-200 text-xs font-medium';
    } else if (kind === 'warn') {
      feedbackEl.className =
        'px-3 py-2 rounded-xl border border-amber-700/60 bg-amber-950/50 text-amber-200 text-xs font-medium';
    } else if (kind === 'error') {
      feedbackEl.className =
        'px-3 py-2 rounded-xl border border-rose-700/60 bg-rose-950/50 text-rose-200 text-xs font-medium';
    } else {
      feedbackEl.className =
        'px-3 py-2 rounded-xl border border-white/[0.08] bg-[#11141d] text-slate-300 text-xs font-medium';
    }
    feedbackEl.textContent = message;
  }

  function findSkill(skillId) {
    return skillsTree.find((s) => s && s.skill_id === skillId) || null;
  }

  function findColocatedTool(skillId, relPath) {
    const skill = findSkill(skillId);
    if (!skill || !Array.isArray(skill.tools)) return null;
    return (
      skill.tools.find(
        (t) => t && (t.path === relPath || `tools/${t.name}.py` === relPath),
      ) || null
    );
  }

  function paintTree() {
    if (!treeListEl) return;
    const query = searchInputEl ? searchInputEl.value : '';
    const filtered = filterCapabilitiesTree(skillsTree, query);
    // When searching, auto-expand matching skills so matched files are immediately clickable
    const effectiveExpanded = new Set(expandedSkills);
    if (String(query || '').trim()) {
      for (const s of filtered) {
        if (s && s.skill_id) effectiveExpanded.add(s.skill_id);
      }
    }
    treeListEl.innerHTML = renderCapabilitiesTreeHtml(filtered, {
      expandedSkills: effectiveExpanded,
      selectedSkillId,
      selectedFilePath,
    });
    safeCreateIcons();
  }

  function paintInspectorHeader() {
    const skill = findSkill(selectedSkillId);
    if (activePathEl) {
      activePathEl.textContent = selectedSkillId
        ? `skills/${selectedSkillId}/${selectedFilePath}`
        : 'Select a skill folder to inspect';
    }
    if (activeSourceBadgeEl) {
      if (!skill) {
        activeSourceBadgeEl.textContent = 'agora';
      } else {
        activeSourceBadgeEl.textContent = skill.source || 'platform';
      }
    }
    if (toolStatusCardEl) {
      const toolSpec =
        selectedSkillId && selectedFilePath.startsWith('tools/')
          ? findColocatedTool(selectedSkillId, selectedFilePath)
          : null;
      if (toolSpec) {
        toolStatusCardEl.classList.remove('hidden');
        toolStatusCardEl.innerHTML = renderToolStatusCardHtml(selectedSkillId, toolSpec);
      } else {
        toolStatusCardEl.classList.add('hidden');
        toolStatusCardEl.innerHTML = '';
      }
    }
  }

  async function selectSkillFile(skillId, relPath = 'SKILL.md', { initialContent = null } = {}) {
    if (!skillId) return;
    selectedSkillId = skillId;
    selectedFilePath = relPath || 'SKILL.md';
    expandedSkills.add(skillId);
    paintTree();
    paintInspectorHeader();

    if (initialContent !== null) {
      if (editorEl) editorEl.value = initialContent;
      return;
    }

    try {
      const data = await api.capabilities.readFile(skillId, selectedFilePath);
      if (editorEl) {
        editorEl.value = typeof data.content === 'string' ? data.content : '';
      }
    } catch (err) {
      console.error('[Capabilities Studio] Failed to read file:', err);
      setFeedback(`Could not load ${skillId}/${selectedFilePath}: ${err.message}`, 'error');
    }
  }

  async function loadCapabilitiesStudio() {
    try {
      const data = await api.capabilities.tree();
      const rawSkills = Array.isArray(data && data.skills) ? data.skills : [];
      skillsTree = rawSkills.map(normalizeSkillEntry).filter(Boolean);
      if (queuedDeepLink && queuedDeepLink.skillId) {
        const targetSkill = queuedDeepLink.skillId;
        const targetPath = queuedDeepLink.filePath || 'SKILL.md';
        queuedDeepLink = null;
        expandedSkills.add(targetSkill);
        await selectSkillFile(targetSkill, targetPath);
        return;
      }
      if (!selectedSkillId && skillsTree.length > 0) {
        const firstId = skillsTree[0].skill_id;
        expandedSkills.add(firstId);
        await selectSkillFile(firstId, 'SKILL.md');
        return;
      }
      paintTree();
      paintInspectorHeader();
    } catch (err) {
      console.error('[Capabilities Studio] Failed to load Agora tree:', err);
      if (treeListEl) {
        treeListEl.innerHTML = `<div class="p-4 text-xs text-rose-300">Failed to load Capabilities tree: ${escapeHtml(err.message)}</div>`;
      }
    }
  }

  function openCreateBar(kind, skillId = '') {
    pendingCreateMode = { kind, skillId };
    if (!createBarEl || !createInputEl || !createKindLabelEl) return;
    createBarEl.classList.remove('hidden');
    if (kind === 'skill') {
      createKindLabelEl.textContent = 'New skill folder ID (slug):';
      createInputEl.placeholder = 'e.g. my-new-skill';
    } else if (kind === 'reference') {
      createKindLabelEl.textContent = `New reference in ${skillId}/references/:`;
      createInputEl.placeholder = 'e.g. architecture.md';
    } else {
      createKindLabelEl.textContent = `New Python tool in ${skillId}/tools/:`;
      createInputEl.placeholder = 'e.g. compute_metric.py';
    }
    createInputEl.value = '';
    createInputEl.focus();
  }

  function closeCreateBar() {
    pendingCreateMode = null;
    if (createBarEl) createBarEl.classList.add('hidden');
    if (createInputEl) createInputEl.value = '';
  }

  async function handleConfirmCreate() {
    if (!pendingCreateMode || !createInputEl) return;
    const raw = String(createInputEl.value || '').trim();
    if (!raw) {
      setFeedback('Enter a name first.', 'warn');
      return;
    }
    const { kind, skillId } = pendingCreateMode;
    closeCreateBar();

    if (kind === 'skill') {
      const slug = raw
        .toLowerCase()
        .replace(/[^a-z0-9_-]+/g, '-')
        .replace(/^-+|-+$/g, '');
      if (!slug) {
        setFeedback('Skill ID must contain letters or digits.', 'error');
        return;
      }
      const starter = defaultSkillMarkdown(slug);
      try {
        await api.capabilities.saveFile(slug, 'SKILL.md', starter);
        setFeedback(`Created skill folder skills/${slug}/SKILL.md`, 'ok');
        showToast(`Created skill folder ${slug}`, 'success');
        expandedSkills.add(slug);
        selectedSkillId = slug;
        selectedFilePath = 'SKILL.md';
        await loadCapabilitiesStudio();
        await selectSkillFile(slug, 'SKILL.md');
      } catch (err) {
        console.error('[Capabilities Studio] Failed to create skill folder:', err);
        setFeedback(`Failed to create skill folder: ${err.message}`, 'error');
      }
      return;
    }

    if (kind === 'reference') {
      const stem = raw.replace(/^references\//, '').replace(/\.md$/i, '');
      const relPath = `references/${stem}.md`;
      const starter = defaultReferenceMarkdown(stem);
      await selectSkillFile(skillId, relPath, { initialContent: starter });
      setFeedback(`Drafted ${skillId}/${relPath} — click Save File to persist.`, 'info');
      return;
    }

    if (kind === 'tool') {
      const stem = raw
        .replace(/^tools\//, '')
        .replace(/\.py$/i, '')
        .replace(/[^a-zA-Z0-9_]/g, '_');
      const relPath = `tools/${stem}.py`;
      const starter = defaultToolPython(stem);
      await selectSkillFile(skillId, relPath, { initialContent: starter });
      setFeedback(`Drafted ${skillId}/${relPath} — click Save File to check & persist.`, 'info');
    }
  }

  async function handleSaveCurrentFile() {
    if (!selectedSkillId || !selectedFilePath || !editorEl) return;
    const content = editorEl.value;
    if (saveBtnEl) saveBtnEl.disabled = true;
    try {
      const result = await api.capabilities.saveFile(selectedSkillId, selectedFilePath, content);
      await loadCapabilitiesStudio();
      await selectSkillFile(selectedSkillId, selectedFilePath);
      if (result.kind === 'tool') {
        if (result.auto_enabled) {
          setFeedback(
            `Saved & auto-enabled ${selectedSkillId}/${selectedFilePath} (pure read_only, check passed).`,
            'ok',
          );
          showToast(`Saved & auto-enabled ${result.tool && result.tool.name}`, 'success');
        } else {
          setFeedback(
            `Saved ${selectedSkillId}/${selectedFilePath} as Disabled (needs approval: outside access detected).`,
            'warn',
          );
          showToast('Tool saved (disabled until approved)', 'info');
        }
      } else {
        setFeedback(`Saved skills/${selectedSkillId}/${selectedFilePath}.`, 'ok');
        showToast(`Saved ${selectedFilePath}`, 'success');
      }
    } catch (err) {
      console.error('[Capabilities Studio] Save failed:', err);
      setFeedback(`Save failed: ${err.message}`, 'error');
      showToast(`Save failed: ${err.message}`, 'error');
    } finally {
      if (saveBtnEl) saveBtnEl.disabled = false;
    }
  }

  async function handleToggleTool(skillId, toolName, nextEnabled) {
    try {
      const res = await api.capabilities.toggleTool(skillId, toolName, nextEnabled);
      await loadCapabilitiesStudio();
      paintInspectorHeader();
      const stateLabel = res.enabled ? 'Enabled' : 'Disabled';
      setFeedback(`${toolName} in ${skillId} is now ${stateLabel}.`, res.enabled ? 'ok' : 'warn');
      showToast(`${toolName}: ${stateLabel}`, 'success');
    } catch (err) {
      console.error('[Capabilities Studio] Toggle tool failed:', err);
      setFeedback(`Could not toggle ${toolName}: ${err.message}`, 'error');
      showToast(`Toggle failed: ${err.message}`, 'error');
    }
  }

  if (searchInputEl) {
    searchInputEl.addEventListener('input', () => paintTree());
  }
  if (refreshBtnEl) {
    refreshBtnEl.addEventListener('click', () => loadCapabilitiesStudio());
  }
  if (newSkillBtnEl) {
    newSkillBtnEl.addEventListener('click', () => openCreateBar('skill'));
  }
  if (createConfirmBtnEl) {
    createConfirmBtnEl.addEventListener('click', () => handleConfirmCreate());
  }
  if (createCancelBtnEl) {
    createCancelBtnEl.addEventListener('click', () => closeCreateBar());
  }
  if (saveBtnEl) {
    saveBtnEl.addEventListener('click', () => handleSaveCurrentFile());
  }

  if (treeListEl) {
    treeListEl.addEventListener('click', (event) => {
      const btn = event.target.closest('[data-action]');
      if (!btn) return;
      const action = btn.getAttribute('data-action');
      const skillId = btn.getAttribute('data-skill-id') || '';
      if (action === 'toggle-skill-folder' && skillId) {
        if (expandedSkills.has(skillId)) {
          expandedSkills.delete(skillId);
          paintTree();
        } else {
          expandedSkills.add(skillId);
          selectSkillFile(skillId, 'SKILL.md');
        }
      } else if (action === 'select-skill-file' && skillId) {
        const relPath = btn.getAttribute('data-skill-file') || 'SKILL.md';
        selectSkillFile(skillId, relPath);
      } else if (action === 'new-reference-file' && skillId) {
        openCreateBar('reference', skillId);
      } else if (action === 'new-tool-file' && skillId) {
        openCreateBar('tool', skillId);
      }
    });
  }

  if (toolStatusCardEl) {
    toolStatusCardEl.addEventListener('click', (event) => {
      const btn = event.target.closest('[data-action="toggle-colocated-tool"]');
      if (!btn) return;
      const skillId = btn.getAttribute('data-skill-id') || '';
      const toolName = btn.getAttribute('data-tool-name') || '';
      const nextEnabled = btn.getAttribute('data-next-enabled') === 'true';
      if (skillId && toolName) {
        handleToggleTool(skillId, toolName, nextEnabled);
      }
    });
  }

  return {
    loadCapabilitiesStudio,
    selectSkillFile,
    queueDeepLink: (opts = {}) => {
      queuedDeepLink = planCapabilitiesStudioDeepLink(opts);
    },
  };
}
