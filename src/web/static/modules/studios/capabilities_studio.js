/**
 * Unified Capabilities Directory Tree Studio [CARD-690, ADR-0065 Slice 4].
 * Browse Agora `skills/<id>/` folders (`SKILL.md`, `references/*.md`, `tools/*.py`),
 * inspect/edit files in place, and toggle colocated Python tools on or off.
 */

import { $, escapeHtml, safeCreateIcons } from '../dom.js';
import { api } from '../services/api.js';
import { showToast } from '../ui/toast.js';
import {
  MCP_TREE_NODE_ID,
  defaultReferenceMarkdown,
  defaultSkillMarkdown,
  defaultToolPython,
  filterCapabilitiesTree,
  normalizeSkillEntry,
  renderCapabilitiesTreeHtml,
  renderToolStatusCardHtml,
} from './capabilities_tree_model.js';
import {
  buildMcpSaveBody,
  formatMcpCommandText,
  renderMcpServerListMarkup,
  serverToSaveBody,
} from './tools_studio_catalog.js';
import { setupRcaProposalsPanel } from './rca_proposals_panel.js';

export const CAPABILITIES_STUDIO_TAB = 'capabilities';
export const CAPABILITIES_STUDIO_LABEL = 'Capabilities';

/**
 * Plan a deep link into the Capabilities directory tree studio [CARD-690, CARD-692].
 * Supports:
 * - skill folder / file (`skillId`, `filePath`)
 * - MCP server panel (`mode: 'mcp'`, `scope`, `agentId`)
 * - capability gap draft (`gap`, `agentId`)
 * @param {{ skillId?: string|null, filePath?: string|null, mode?: string|null, scope?: string|null, agentId?: string|null, gap?: object|null }} [opts]
 */
export function planCapabilitiesStudioDeepLink({
  skillId = null,
  filePath = null,
  mode = null,
  scope = null,
  agentId = null,
  gap = null,
} = {}) {
  const cleanAgent = String(agentId || '').trim() || null;
  if (mode === 'mcp' || (!skillId && !gap && scope)) {
    const cleanScope = scope === 'agent' && cleanAgent ? 'agent' : 'platform';
    return {
      tab: CAPABILITIES_STUDIO_TAB,
      label: CAPABILITIES_STUDIO_LABEL,
      mode: 'mcp',
      scope: cleanScope,
      agentId: cleanScope === 'agent' ? cleanAgent : null,
      skillId: MCP_TREE_NODE_ID,
      filePath: null,
      gap: null,
    };
  }
  if (gap && typeof gap === 'object') {
    return {
      tab: CAPABILITIES_STUDIO_TAB,
      label: CAPABILITIES_STUDIO_LABEL,
      mode: 'gap',
      scope: cleanAgent ? 'agent' : 'platform',
      agentId: cleanAgent,
      skillId: null,
      filePath: 'SKILL.md',
      gap,
    };
  }
  const cleanSkill = String(skillId || '').trim();
  const cleanPath = String(filePath || '').trim() || (cleanSkill ? 'SKILL.md' : '');
  return {
    tab: CAPABILITIES_STUDIO_TAB,
    label: CAPABILITIES_STUDIO_LABEL,
    mode: 'skill',
    scope: cleanAgent ? 'agent' : 'platform',
    agentId: cleanAgent,
    skillId: cleanSkill || null,
    filePath: cleanPath || null,
    gap: null,
  };
}

export function initCapabilitiesStudio(state, _callbacks = {}) {
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
  const mcpPaneEl = $('capabilitiesMcpPane');
  const mcpScopeSelectEl = $('capabilitiesMcpScopeSelect');
  const mcpAgentFieldEl = $('capabilitiesMcpAgentField');
  const mcpAgentSelectEl = $('capabilitiesMcpAgentSelect');
  const mcpAddBtnEl = $('capabilitiesMcpAddBtn');
  const mcpFormEl = $('capabilitiesMcpForm');
  const mcpNameInputEl = $('capabilitiesMcpNameInput');
  const mcpTransportSelectEl = $('capabilitiesMcpTransportSelect');
  const mcpCommandGroupEl = $('capabilitiesMcpCommandGroup');
  const mcpCommandInputEl = $('capabilitiesMcpCommandInput');
  const mcpUrlGroupEl = $('capabilitiesMcpUrlGroup');
  const mcpUrlInputEl = $('capabilitiesMcpUrlInput');
  const mcpCredentialSelectEl = $('capabilitiesMcpCredentialSelect');
  const mcpAuthTypeSelectEl = $('capabilitiesMcpAuthTypeSelect');
  const mcpAuthHeaderGroupEl = $('capabilitiesMcpAuthHeaderGroup');
  const mcpAuthHeaderInputEl = $('capabilitiesMcpAuthHeaderInput');
  const mcpManageVaultBtnEl = $('capabilitiesMcpManageVaultBtn');
  const mcpEnabledCheckboxEl = $('capabilitiesMcpEnabledCheckbox');
  const mcpCancelBtnEl = $('capabilitiesMcpCancelBtn');
  const mcpSaveBtnEl = $('capabilitiesMcpSaveBtn');
  const mcpListEl = $('capabilitiesMcpList');
  const editorContainerEl = $('capabilitiesFileEditorContainer');
  const editorEl = $('capabilitiesFileEditor');
  const saveBtnEl = $('capabilitiesSaveFileBtn');

  let skillsTree = [];
  const expandedSkills = new Set();
  let selectedSkillId = '';
  let selectedFilePath = 'SKILL.md';
  let pendingCreateMode = null; // { kind: 'skill' | 'reference' | 'tool', skillId?: string }
  let queuedDeepLink = null;
  let mcpServersCache = [];
  let vaultCredentialsCache = [];

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

  function syncMcpAgentOptions(preferredAgentId = '') {
    if (!mcpAgentSelectEl) return;
    const agents = Array.isArray(state && state.agents) ? state.agents : [];
    const current = preferredAgentId || mcpAgentSelectEl.value || '';
    const opts = ['<option value="">Select an agent</option>'];
    for (const ag of agents) {
      const id = String(ag.id || ag.agent_id || '');
      if (!id) continue;
      const name = String(ag.name || id);
      const sel = id === current ? ' selected' : '';
      opts.push(`<option value="${escapeHtml(id)}"${sel}>${escapeHtml(name)} (${escapeHtml(id)})</option>`);
    }
    if (current && !agents.some((a) => String(a.id || a.agent_id || '') === current)) {
      opts.push(`<option value="${escapeHtml(current)}" selected>${escapeHtml(current)}</option>`);
    }
    mcpAgentSelectEl.innerHTML = opts.join('');
  }

  function syncMcpAuthChrome() {
    if (!mcpAuthHeaderGroupEl) return;
    const scheme = mcpAuthTypeSelectEl ? mcpAuthTypeSelectEl.value : 'bearer';
    const hasCustomHeader = Boolean(mcpAuthHeaderInputEl && String(mcpAuthHeaderInputEl.value || '').trim());
    const showHeaderField = scheme === 'header' || scheme === 'env' || hasCustomHeader;
    mcpAuthHeaderGroupEl.classList.toggle('hidden', !showHeaderField);
  }

  async function syncMcpVaultCredentials(preferredCredId = '') {
    if (!mcpCredentialSelectEl) return;
    const current = preferredCredId !== undefined && preferredCredId !== null
      ? String(preferredCredId)
      : (mcpCredentialSelectEl.value || '');
    try {
      const creds = await api.capabilities.listVaultCredentials();
      vaultCredentialsCache = Array.isArray(creds) ? creds : [];
    } catch {
      vaultCredentialsCache = Array.isArray(state && state.vaultCredentials) ? state.vaultCredentials : [];
    }
    const opts = ['<option value="">None (No Vault credential)</option>'];
    for (const cred of vaultCredentialsCache) {
      const id = String((cred && cred.id) || '').trim();
      if (!id) continue;
      const name = String(cred.name || id);
      const ctype = String(cred.type || 'token');
      const sel = id === current ? ' selected' : '';
      opts.push(`<option value="${escapeHtml(id)}" data-cred-type="${escapeHtml(ctype)}"${sel}>${escapeHtml(name)} (${escapeHtml(id)} · ${escapeHtml(ctype)})</option>`);
    }
    if (current && !vaultCredentialsCache.some((c) => String((c && c.id) || '') === current)) {
      opts.push(`<option value="${escapeHtml(current)}" selected>${escapeHtml(current)}</option>`);
    }
    mcpCredentialSelectEl.innerHTML = opts.join('');
  }

  async function loadMcpInspector({ scope = null, agentId = null } = {}) {
    const nextScope = scope || (mcpScopeSelectEl ? mcpScopeSelectEl.value : 'platform') || 'platform';
    if (mcpScopeSelectEl) mcpScopeSelectEl.value = nextScope;
    syncMcpAgentOptions(agentId || '');
    await syncMcpVaultCredentials();
    syncMcpAuthChrome();
    if (mcpAgentFieldEl) {
      mcpAgentFieldEl.classList.toggle('hidden', nextScope !== 'agent');
    }
    const targetAgent = nextScope === 'agent' ? (agentId || (mcpAgentSelectEl ? mcpAgentSelectEl.value : '')) : '';
    try {
      const raw = await api.capabilities.listMcpServers(nextScope, targetAgent);
      mcpServersCache = Array.isArray(raw) ? raw : [];
      if (mcpListEl) {
        mcpListEl.innerHTML = renderMcpServerListMarkup(mcpServersCache, {
          scope: nextScope,
          agentId: targetAgent,
        });
      }
    } catch (err) {
      if (mcpListEl) {
        mcpListEl.innerHTML = `<p class="text-xs text-rose-300">Failed to load MCP servers: ${escapeHtml(err.message)}</p>`;
      }
    }
  }

  async function selectMcpNode({ scope = null, agentId = null } = {}) {
    selectedSkillId = MCP_TREE_NODE_ID;
    selectedFilePath = '';
    paintTree();
    paintInspectorHeader();
    await loadMcpInspector({ scope, agentId });
  }

  function paintInspectorHeader() {
    const isMcp = selectedSkillId === MCP_TREE_NODE_ID;
    const skill = !isMcp ? findSkill(selectedSkillId) : null;
    if (activePathEl) {
      if (isMcp) {
        activePathEl.textContent = 'mcp/ (MCP Servers)';
      } else {
        activePathEl.textContent = selectedSkillId
          ? `skills/${selectedSkillId}/${selectedFilePath}`
          : 'Select a skill folder to inspect';
      }
    }
    if (activeSourceBadgeEl) {
      if (isMcp) {
        activeSourceBadgeEl.textContent = 'mcp';
      } else if (!skill) {
        activeSourceBadgeEl.textContent = 'agora';
      } else {
        activeSourceBadgeEl.textContent = skill.source || 'platform';
      }
    }
    if (saveBtnEl) {
      saveBtnEl.classList.toggle('hidden', isMcp);
    }
    if (mcpPaneEl) {
      mcpPaneEl.classList.toggle('hidden', !isMcp);
    }
    if (editorContainerEl) {
      editorContainerEl.classList.toggle('hidden', isMcp);
    }
    if (toolStatusCardEl) {
      const toolSpec =
        !isMcp && selectedSkillId && selectedFilePath.startsWith('tools/')
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

  const rcaPanel = setupRcaProposalsPanel({
    callbacks: _callbacks,
    onInspectTool: (skillId, filePath) => selectSkillFile(skillId, filePath),
  });

  async function loadCapabilitiesStudio() {
    try {
      await rcaPanel.refreshRcaProposals();
      const data = await api.capabilities.tree();
      const rawSkills = Array.isArray(data && data.skills) ? data.skills : [];
      skillsTree = rawSkills.map(normalizeSkillEntry).filter(Boolean);
      if (queuedDeepLink) {
        const link = queuedDeepLink;
        queuedDeepLink = null;
        if (link.mode === 'mcp') {
          await selectMcpNode({ scope: link.scope, agentId: link.agentId });
          return;
        }
        if (link.mode === 'gap' && link.gap) {
          const rawSlug = String(
            link.gap.suggested_tool_name || link.gap.missing_capability || 'new-capability',
          )
            .toLowerCase()
            .replace(/[^a-z0-9_-]+/g, '-')
            .replace(/^-+|-+$/g, '');
          openCreateBar('skill');
          if (createInputEl && rawSlug) {
            createInputEl.value = rawSlug;
          }
          setFeedback(
            `Drafting Agora skill folder for capability gap "${rawSlug}" — confirm Create to initialize.`,
            'info',
          );
          paintTree();
          paintInspectorHeader();
          return;
        }
        if (link.skillId) {
          const targetSkill = link.skillId;
          const targetPath = link.filePath || 'SKILL.md';
          expandedSkills.add(targetSkill);
          await selectSkillFile(targetSkill, targetPath);
          return;
        }
      }
      if (selectedSkillId === MCP_TREE_NODE_ID) {
        paintTree();
        paintInspectorHeader();
        await loadMcpInspector();
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
  if (createInputEl) {
    createInputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); handleConfirmCreate(); }
      else if (e.key === 'Escape') { e.preventDefault(); closeCreateBar(); }
    });
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
      if (action === 'select-mcp-node') {
        selectMcpNode();
      } else if (action === 'toggle-skill-folder' && skillId) {
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

  if (mcpScopeSelectEl) {
    mcpScopeSelectEl.addEventListener('change', () => {
      loadMcpInspector({ scope: mcpScopeSelectEl.value });
    });
  }
  if (mcpAgentSelectEl) {
    mcpAgentSelectEl.addEventListener('change', () => {
      loadMcpInspector({
        scope: mcpScopeSelectEl ? mcpScopeSelectEl.value : 'agent',
        agentId: mcpAgentSelectEl.value,
      });
    });
  }
  if (mcpAddBtnEl && mcpFormEl) {
    mcpAddBtnEl.addEventListener('click', async () => {
      await syncMcpVaultCredentials('');
      if (mcpNameInputEl) mcpNameInputEl.value = '';
      if (mcpCommandInputEl) mcpCommandInputEl.value = '';
      if (mcpUrlInputEl) mcpUrlInputEl.value = '';
      if (mcpCredentialSelectEl) mcpCredentialSelectEl.value = '';
      if (mcpAuthTypeSelectEl) mcpAuthTypeSelectEl.value = 'bearer';
      if (mcpAuthHeaderInputEl) mcpAuthHeaderInputEl.value = '';
      if (mcpEnabledCheckboxEl) mcpEnabledCheckboxEl.checked = true;
      syncMcpAuthChrome();
      mcpFormEl.classList.remove('hidden');
      if (mcpNameInputEl) mcpNameInputEl.focus();
    });
  }
  if (mcpCancelBtnEl && mcpFormEl) {
    mcpCancelBtnEl.addEventListener('click', () => {
      mcpFormEl.classList.add('hidden');
    });
  }
  if (mcpTransportSelectEl) {
    mcpTransportSelectEl.addEventListener('change', () => {
      const isSse = mcpTransportSelectEl.value === 'sse';
      if (mcpCommandGroupEl) mcpCommandGroupEl.classList.toggle('hidden', isSse);
      if (mcpUrlGroupEl) mcpUrlGroupEl.classList.toggle('hidden', !isSse);
    });
  }
  if (mcpCredentialSelectEl) {
    mcpCredentialSelectEl.addEventListener('change', () => {
      const cid = mcpCredentialSelectEl.value;
      const cred = vaultCredentialsCache.find((c) => c && String(c.id) === cid);
      if (cred && mcpAuthTypeSelectEl) {
        const ctype = String(cred.type || 'token').toLowerCase();
        if (ctype === 'basic_auth' || ctype === 'password') {
          mcpAuthTypeSelectEl.value = 'basic';
        } else if (ctype === 'api_key') {
          mcpAuthTypeSelectEl.value = 'header';
        } else {
          mcpAuthTypeSelectEl.value = 'bearer';
        }
      }
      syncMcpAuthChrome();
    });
  }
  if (mcpAuthTypeSelectEl) {
    mcpAuthTypeSelectEl.addEventListener('change', () => syncMcpAuthChrome());
  }
  if (mcpManageVaultBtnEl) {
    mcpManageVaultBtnEl.addEventListener('click', () => {
      if (typeof _callbacks.switchTab === 'function') {
        _callbacks.switchTab('settings');
      }
      const connDetails = document.querySelector('[data-settings-section="connections"]');
      if (connDetails) connDetails.open = true;
      const addCredBtn = $('addCredentialBtn');
      if (addCredBtn && typeof addCredBtn.scrollIntoView === 'function') {
        addCredBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    });
  }
  if (mcpSaveBtnEl) {
    mcpSaveBtnEl.addEventListener('click', async () => {
      const scopeVal = mcpScopeSelectEl ? mcpScopeSelectEl.value : 'platform';
      const agentVal = mcpAgentSelectEl ? mcpAgentSelectEl.value : '';
      const built = buildMcpSaveBody({
        name: mcpNameInputEl ? mcpNameInputEl.value : '',
        transport: mcpTransportSelectEl ? mcpTransportSelectEl.value : 'stdio',
        commandText: mcpCommandInputEl ? mcpCommandInputEl.value : '',
        url: mcpUrlInputEl ? mcpUrlInputEl.value : '',
        headersText: '',
        env: {},
        credentialId: mcpCredentialSelectEl ? mcpCredentialSelectEl.value : '',
        authType: mcpAuthTypeSelectEl ? mcpAuthTypeSelectEl.value : 'bearer',
        authHeader: mcpAuthHeaderInputEl ? mcpAuthHeaderInputEl.value : '',
        enabled: mcpEnabledCheckboxEl ? Boolean(mcpEnabledCheckboxEl.checked) : true,
      });
      if (!built.ok) {
        setFeedback(built.error || 'Invalid MCP server configuration.', 'error');
        return;
      }
      try {
        await api.capabilities.saveMcpServer(scopeVal, agentVal, built.body);
        if (mcpFormEl) mcpFormEl.classList.add('hidden');
        setFeedback(`Saved MCP server "${built.body.name}".`, 'ok');
        showToast(`Saved MCP server ${built.body.name}`, 'success');
        await loadMcpInspector({ scope: scopeVal, agentId: agentVal });
      } catch (err) {
        setFeedback(`Could not save MCP server: ${err.message}`, 'error');
      }
    });
  }
  if (mcpListEl) {
    mcpListEl.addEventListener('click', async (event) => {
      const btn = event.target.closest('[data-action]');
      if (!btn) return;
      const action = btn.getAttribute('data-action');
      const serverName = btn.getAttribute('data-server-name') || '';
      const scopeVal = mcpScopeSelectEl ? mcpScopeSelectEl.value : 'platform';
      const agentVal = mcpAgentSelectEl ? mcpAgentSelectEl.value : '';
      if (action === 'delete' && serverName) {
        try {
          await api.capabilities.deleteMcpServer(scopeVal, agentVal, serverName);
          setFeedback(`Removed MCP server "${serverName}".`, 'info');
          showToast(`Removed MCP server ${serverName}`, 'info');
          await loadMcpInspector({ scope: scopeVal, agentId: agentVal });
        } catch (err) {
          setFeedback(`Failed to remove MCP server "${serverName}": ${err.message}`, 'error');
          showToast(`Failed to remove MCP server: ${err.message}`, 'error');
        }
      } else if (action === 'toggle' && serverName) {
        const current = mcpServersCache.find((s) => s && s.name === serverName);
        if (!current) return;
        try {
          const nextEnabled = !current.enabled;
          const body = serverToSaveBody(current, nextEnabled);
          await api.capabilities.saveMcpServer(scopeVal, agentVal, body);
          showToast(`MCP server ${serverName} ${nextEnabled ? 'enabled' : 'disabled'}`, 'info');
          await loadMcpInspector({ scope: scopeVal, agentId: agentVal });
        } catch (err) {
          setFeedback(`Failed to toggle MCP server "${serverName}": ${err.message}`, 'error');
          showToast(`Failed to toggle MCP server: ${err.message}`, 'error');
        }
      } else if (action === 'edit' && serverName) {
        const current = mcpServersCache.find((s) => s && s.name === serverName);
        if (!current || !mcpFormEl) return;
        await syncMcpVaultCredentials(current.credential_id || '');
        const isSse = (current.transport || (current.url ? 'sse' : 'stdio')) === 'sse';
        if (mcpNameInputEl) mcpNameInputEl.value = current.name || '';
        if (mcpTransportSelectEl) mcpTransportSelectEl.value = isSse ? 'sse' : 'stdio';
        if (mcpCommandGroupEl) mcpCommandGroupEl.classList.toggle('hidden', isSse);
        if (mcpUrlGroupEl) mcpUrlGroupEl.classList.toggle('hidden', !isSse);
        if (mcpCommandInputEl) mcpCommandInputEl.value = formatMcpCommandText(current.command);
        if (mcpUrlInputEl) mcpUrlInputEl.value = current.url || '';
        if (mcpCredentialSelectEl) mcpCredentialSelectEl.value = current.credential_id || '';
        if (mcpAuthTypeSelectEl) mcpAuthTypeSelectEl.value = current.auth_type || 'bearer';
        if (mcpAuthHeaderInputEl) mcpAuthHeaderInputEl.value = current.auth_header || '';
        if (mcpEnabledCheckboxEl) mcpEnabledCheckboxEl.checked = current.enabled !== false;
        syncMcpAuthChrome();
        mcpFormEl.classList.remove('hidden');
      } else if (action === 'test-saved' && serverName) {
        const current = mcpServersCache.find((s) => s && s.name === serverName);
        if (!current) return;
        try {
          const probe = await api.capabilities.testMcpServer(
            scopeVal,
            agentVal,
            serverToSaveBody(current, current.enabled !== false),
          );
          if (probe && probe.status === 'ok') {
            setFeedback(`Handshake OK for "${serverName}" (${probe.tools_count || 0} tools).`, 'ok');
            showToast(`Handshake OK for ${serverName}`, 'success');
          } else {
            const msg = (probe && probe.error) || 'unknown error';
            setFeedback(`Handshake failed for "${serverName}": ${msg}`, 'error');
            showToast(`Handshake failed for ${serverName}: ${msg}`, 'error');
          }
        } catch (err) {
          setFeedback(`Handshake failed for "${serverName}": ${err.message}`, 'error');
          showToast(`Handshake failed for ${serverName}: ${err.message}`, 'error');
        }
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
    selectMcpNode,
    queueDeepLink: (opts = {}) => {
      queuedDeepLink = planCapabilitiesStudioDeepLink(opts);
    },
  };
}
