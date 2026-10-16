/**
 * Pure model and HTML formatters for the Agora Capabilities Directory Tree Studio [CARD-690, ADR-0065].
 */

import { escapeHtml } from '../dom.js';

/**
 * Normalize a skill entry from `GET /api/capabilities/tree` into a canonical shape.
 * Supports both the backend `build_capabilities_tree` shape (`id`, `references`, `colocated_tools`, `declared_tools`)
 * and compact test fixtures (`skill_id`, `files.references`, `files.tools`, `bound_tools`).
 * @param {object} skill
 * @returns {object|null}
 */
export function normalizeSkillEntry(skill) {
  if (!skill || typeof skill !== 'object') return null;
  const skillId = String(skill.id || skill.skill_id || '').trim();
  if (!skillId) return null;

  const filesObj = skill.files && !Array.isArray(skill.files) ? skill.files : {};
  const rawRefs = Array.isArray(skill.references)
    ? skill.references
    : Array.isArray(filesObj.references)
      ? filesObj.references
      : [];
  const references = rawRefs
    .map((r) => (typeof r === 'string' ? r : (r && r.path) || ''))
    .filter(Boolean);

  const rawTools = Array.isArray(skill.colocated_tools)
    ? skill.colocated_tools
    : Array.isArray(filesObj.tools)
      ? filesObj.tools
      : [];
  const tools = rawTools
    .filter((t) => t && typeof t === 'object')
    .map((t) => ({
      ...t,
      name: String(t.name || ''),
      path: String(t.relative_path || t.path || `tools/${t.name}.py`),
    }));

  const boundTools = Array.isArray(skill.declared_tools)
    ? skill.declared_tools
    : Array.isArray(skill.bound_tools)
      ? skill.bound_tools
      : [];

  return {
    ...skill,
    id: skillId,
    skill_id: skillId,
    source: skill.source === 'shipped' ? 'platform' : String(skill.source || 'platform'),
    references,
    tools,
    bound_tools: boundTools,
  };
}

/**
 * Filter Agora skill folders by search query across skill metadata, references, and tools.
 * @param {Array<object>} skills
 * @param {string} query
 * @returns {Array<object>}
 */
export function filterCapabilitiesTree(skills, query = '') {
  const list = (Array.isArray(skills) ? skills : []).map(normalizeSkillEntry).filter(Boolean);
  const q = String(query || '').trim().toLowerCase();
  if (!q) return list;

  return list.filter((skill) => {
    const haystacks = [
      skill.skill_id,
      skill.name,
      skill.description,
      ...skill.bound_tools,
      ...skill.references,
    ];
    for (const t of skill.tools) {
      haystacks.push(t.name, t.path, t.description, t.risk);
    }
    return haystacks.some((item) => String(item || '').toLowerCase().includes(q));
  });
}

/**
 * Virtual tree node ID for the MCP Servers attachment panel in Capabilities Studio [CARD-692].
 */
export const MCP_TREE_NODE_ID = '__mcp__';

/**
 * Render the expandable Agora `skills/<id>/` directory tree HTML.
 * @param {Array<object>} skills
 * @param {{ expandedSkills?: Set<string>, selectedSkillId?: string, selectedFilePath?: string }} [opts]
 * @returns {string}
 */
export function renderCapabilitiesTreeHtml(skills, opts = {}) {
  const list = (Array.isArray(skills) ? skills : []).map(normalizeSkillEntry).filter(Boolean);
  const expanded = opts.expandedSkills instanceof Set ? opts.expandedSkills : new Set();
  const selectedSkillId = String(opts.selectedSkillId || '');
  const selectedFilePath = String(opts.selectedFilePath || '');

  const isMcpSelected = selectedSkillId === MCP_TREE_NODE_ID;
  const mcpHeaderClass = isMcpSelected
    ? 'bg-cyan-950/70 border-cyan-500/60 text-white'
    : 'bg-[#11141d] hover:bg-slate-800/60 border-white/[0.06] text-slate-200';
  const mcpNodeHtml = `
    <div class="rounded-xl border border-white/[0.04] bg-[#0b0d13]/80 p-1.5" data-mcp-node="true">
      <button type="button"
        data-action="select-mcp-node"
        data-testid="capabilities-mcp-tree-node"
        class="w-full text-left flex items-center justify-between gap-2 px-2.5 py-2 rounded-lg border transition ${mcpHeaderClass}">
        <div class="min-w-0 flex items-center gap-2">
          <span class="text-xs font-mono text-cyan-300 shrink-0">🔌</span>
          <div class="min-w-0">
            <div class="flex items-center gap-1.5">
              <span class="font-mono text-xs font-semibold truncate">mcp/</span>
              <span class="text-[10px] font-sans text-cyan-300 font-medium">MCP Servers</span>
            </div>
            <p class="text-[10px] text-slate-400 truncate">Platform &amp; per-agent MCP server attachments</p>
          </div>
        </div>
        <span class="px-1.5 py-0.5 rounded bg-cyan-950/80 border border-cyan-700/50 text-[10px] font-mono text-cyan-300 shrink-0">mcp</span>
      </button>
    </div>
  `;

  if (list.length === 0) {
    return `
      ${mcpNodeHtml}
      <div class="p-4 text-center text-slate-400 text-xs space-y-1" data-testid="capabilities-tree-empty">
        <p class="font-semibold text-slate-300">No matching skill folders</p>
        <p class="text-[11px] text-slate-500">Clear the filter or click + New Skill to create an Agora skill folder.</p>
      </div>
    `;
  }

  const rows = list.map((skill) => {
    const skillId = skill.skill_id;
    const isExpanded = expanded.has(skillId);
    const refs = skill.references;
    const colocatedTools = skill.tools;
    const boundTools = skill.bound_tools;
    const pendingCount = colocatedTools.filter((t) => t && !t.enabled).length;
    const totalTools = colocatedTools.length + boundTools.length;
    const sourceBadge =
      skill.source === 'user'
        ? '<span class="px-1.5 py-0.5 rounded bg-brand-950/80 border border-brand-700/50 text-[10px] font-mono text-brand-300">user</span>'
        : '<span class="px-1.5 py-0.5 rounded bg-slate-900 border border-white/[0.08] text-[10px] font-mono text-slate-400">platform</span>';
    const pendingDot =
      pendingCount > 0
        ? `<span class="w-2 h-2 rounded-full bg-amber-400 shrink-0" title="${pendingCount} tool(s) awaiting approval"></span>`
        : '';

    const isFolderActive = selectedSkillId === skillId;
    const folderHeaderClass = isFolderActive
      ? 'bg-slate-800/90 border-brand-500/50 text-white'
      : 'bg-[#11141d] hover:bg-slate-800/60 border-white/[0.06] text-slate-200';

    const skillMdActive = isFolderActive && selectedFilePath === 'SKILL.md';
    const skillMdClass = skillMdActive
      ? 'bg-brand-950/70 border-brand-500/60 text-white font-semibold'
      : 'hover:bg-white/[0.04] border-transparent text-slate-300';

    const refItemsHtml = refs
      .map((refPath) => {
        const active = isFolderActive && selectedFilePath === refPath;
        const cls = active
          ? 'bg-brand-950/70 border-brand-500/60 text-white font-semibold'
          : 'hover:bg-white/[0.04] border-transparent text-slate-300';
        const shortName = String(refPath).replace(/^references\//, '');
        return `
          <button type="button"
            data-action="select-skill-file"
            data-skill-id="${escapeHtml(skillId)}"
            data-skill-file="${escapeHtml(refPath)}"
            class="w-full text-left flex items-center justify-between gap-2 pl-6 pr-2 py-1 rounded-lg border text-[11px] font-mono transition ${cls}">
            <span class="truncate">📄 ${escapeHtml(shortName)}</span>
            <span class="text-[10px] text-slate-500 shrink-0">md</span>
          </button>
        `;
      })
      .join('');

    const colocatedToolsHtml = colocatedTools
      .map((tool) => {
        const toolPath = String(tool.path || `tools/${tool.name}.py`);
        const active = isFolderActive && selectedFilePath === toolPath;
        const cls = active
          ? 'bg-brand-950/70 border-brand-500/60 text-white font-semibold'
          : 'hover:bg-white/[0.04] border-transparent text-slate-300';
        const shortName = String(toolPath).replace(/^tools\//, '');
        const statePill = tool.enabled
          ? '<span class="px-1.5 py-0.5 rounded bg-emerald-950/80 border border-emerald-700/50 text-[9px] font-mono text-emerald-300 shrink-0">Enabled</span>'
          : '<span class="px-1.5 py-0.5 rounded bg-amber-950/80 border border-amber-700/60 text-[9px] font-mono text-amber-300 shrink-0">Needs approval</span>';
        return `
          <button type="button"
            data-action="select-skill-file"
            data-skill-id="${escapeHtml(skillId)}"
            data-skill-file="${escapeHtml(toolPath)}"
            class="w-full text-left flex items-center justify-between gap-1.5 pl-6 pr-2 py-1 rounded-lg border text-[11px] font-mono transition ${cls}">
            <span class="truncate">🐍 ${escapeHtml(shortName)}</span>
            ${statePill}
          </button>
        `;
      })
      .join('');

    const boundToolsHtml = boundTools
      .map(
        (toolName) => `
          <div class="flex items-center justify-between gap-1.5 pl-6 pr-2 py-1 text-[11px] font-mono text-slate-400">
            <span class="truncate">🔧 ${escapeHtml(toolName)}</span>
            <span class="text-[9px] text-slate-500 shrink-0">bound</span>
          </div>
        `,
      )
      .join('');

    const childrenHtml = isExpanded
      ? `
        <div class="pl-3 pr-1 py-1.5 space-y-1 border-l border-white/[0.08] ml-3 mt-1" data-testid="capabilities-folder-children-${escapeHtml(skillId)}">
          <button type="button"
            data-action="select-skill-file"
            data-skill-id="${escapeHtml(skillId)}"
            data-skill-file="SKILL.md"
            class="w-full text-left flex items-center justify-between gap-2 px-2.5 py-1 rounded-lg border text-[11px] font-mono transition ${skillMdClass}">
            <span class="truncate">📘 SKILL.md</span>
            <span class="text-[10px] text-sky-400 shrink-0">entry</span>
          </button>

          <div class="pt-1">
            <div class="flex items-center justify-between px-2 py-0.5 text-[10px] font-mono text-slate-400">
              <span>📂 references/ (${refs.length})</span>
              <button type="button"
                data-action="new-reference-file"
                data-skill-id="${escapeHtml(skillId)}"
                class="px-1.5 py-0.5 rounded bg-white/[0.04] hover:bg-white/[0.1] text-sky-300 text-[10px] font-sans font-medium transition"
                title="Add reference markdown file">+ Ref</button>
            </div>
            <div class="space-y-0.5 mt-0.5">
              ${refItemsHtml || '<div class="pl-6 py-0.5 text-[10px] text-slate-600 italic">No reference files</div>'}
            </div>
          </div>

          <div class="pt-1">
            <div class="flex items-center justify-between px-2 py-0.5 text-[10px] font-mono text-slate-400">
              <span>📂 tools/ (${totalTools})</span>
              <button type="button"
                data-action="new-tool-file"
                data-skill-id="${escapeHtml(skillId)}"
                class="px-1.5 py-0.5 rounded bg-white/[0.04] hover:bg-white/[0.1] text-emerald-300 text-[10px] font-sans font-medium transition"
                title="Add colocated Python tool">+ Tool</button>
            </div>
            <div class="space-y-0.5 mt-0.5">
              ${colocatedToolsHtml}
              ${boundToolsHtml}
              ${!colocatedToolsHtml && !boundToolsHtml ? '<div class="pl-6 py-0.5 text-[10px] text-slate-600 italic">No tools in folder</div>' : ''}
            </div>
          </div>
        </div>
      `
      : '';

    return `
      <div class="rounded-xl border border-white/[0.04] bg-[#0b0d13]/80 p-1.5" data-skill-folder="${escapeHtml(skillId)}">
        <button type="button"
          data-action="toggle-skill-folder"
          data-skill-id="${escapeHtml(skillId)}"
          aria-expanded="${isExpanded ? 'true' : 'false'}"
          class="w-full text-left flex items-center justify-between gap-2 px-2.5 py-2 rounded-lg border transition ${folderHeaderClass}">
          <div class="min-w-0 flex items-center gap-2">
            <span class="text-xs font-mono text-amber-300 shrink-0">${isExpanded ? '📂' : '📁'}</span>
            <div class="min-w-0">
              <div class="flex items-center gap-1.5">
                <span class="font-mono text-xs font-semibold truncate">${escapeHtml(skillId)}/</span>
                ${pendingDot}
              </div>
              <p class="text-[10px] text-slate-400 truncate">${escapeHtml(skill.description || skill.name || '')}</p>
            </div>
          </div>
          <div class="flex items-center gap-1.5 shrink-0">
            ${sourceBadge}
            <span class="px-1.5 py-0.5 rounded bg-[#08090c] border border-white/[0.06] text-[10px] font-mono text-slate-400">${totalTools}t</span>
          </div>
        </button>
        ${childrenHtml}
      </div>
    `;
  });

  return `
    <div class="space-y-1.5" data-testid="capabilities-agora-root">
      ${mcpNodeHtml}
      <div class="px-2 py-1 text-[11px] font-mono text-slate-400 flex items-center justify-between">
        <span>📦 skills/ (${list.length} folders)</span>
        <span class="text-[10px] text-slate-500">Agora layout</span>
      </div>
      ${rows.join('')}
    </div>
  `;
}

/**
 * Render the colocated tool status & enable/disable toggle bar when viewing `tools/<name>.py`.
 * @param {string} skillId
 * @param {object|null} toolSpec
 * @returns {string}
 */
export function renderToolStatusCardHtml(skillId, toolSpec) {
  if (!toolSpec || typeof toolSpec !== 'object') return '';
  const name = String(toolSpec.name || '');
  const risk = String(toolSpec.risk || 'read_only');
  const accessList = Array.isArray(toolSpec.access) ? toolSpec.access : [];
  const accessText = accessList.length > 0 ? accessList.join(', ') : 'none (pure)';
  const checkStatus = String(toolSpec.check_status || 'passed');
  const enabled = Boolean(toolSpec.enabled);
  const props = (toolSpec.parameters && toolSpec.parameters.properties) || {};
  const required = new Set((toolSpec.parameters && toolSpec.parameters.required) || []);
  const paramSummary =
    Object.keys(props).length > 0
      ? Object.entries(props)
          .map(([k, v]) => `${k}: ${(v && v.type) || 'any'}${required.has(k) ? ' (req)' : ''}`)
          .join(', ')
      : 'no parameters';

  const statusBadge = enabled
    ? '<span class="px-2 py-0.5 rounded-full bg-emerald-950/90 border border-emerald-600/60 text-emerald-300 text-[11px] font-mono font-semibold" data-testid="capabilities-tool-state-badge">Enabled</span>'
    : '<span class="px-2 py-0.5 rounded-full bg-amber-950/90 border border-amber-600/60 text-amber-300 text-[11px] font-mono font-semibold" data-testid="capabilities-tool-state-badge">Disabled (needs approval)</span>';

  const btnClass = enabled
    ? 'bg-slate-800 hover:bg-rose-950/80 text-slate-200 hover:text-rose-200 border border-white/[0.1]'
    : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm shadow-emerald-600/30';
  const btnLabel = enabled ? 'Disable Tool' : 'Enable Tool';

  return `
    <div class="p-3 rounded-xl bg-[#11141d] border border-white/[0.08] flex flex-col sm:flex-row sm:items-center justify-between gap-3" data-testid="capabilities-tool-status-inner">
      <div class="space-y-1 min-w-0">
        <div class="flex flex-wrap items-center gap-2">
          <span class="font-mono text-xs font-bold text-white">${escapeHtml(name)}</span>
          ${statusBadge}
          <span class="px-2 py-0.5 rounded bg-[#08090c] border border-white/[0.08] text-[10px] font-mono text-sky-300">risk: ${escapeHtml(risk)}</span>
          <span class="px-2 py-0.5 rounded bg-[#08090c] border border-white/[0.08] text-[10px] font-mono text-purple-300">access: ${escapeHtml(accessText)}</span>
          <span class="px-2 py-0.5 rounded bg-[#08090c] border border-white/[0.08] text-[10px] font-mono text-slate-400">check: ${escapeHtml(checkStatus)}</span>
        </div>
        <p class="text-[11px] text-slate-300">${escapeHtml(toolSpec.description || 'Colocated Python tool')}</p>
        <p class="text-[10px] font-mono text-slate-400">Schema: ${escapeHtml(paramSummary)}</p>
      </div>
      <div class="shrink-0 flex items-center gap-2">
        <button type="button"
          id="capabilitiesToggleToolBtn"
          data-testid="capabilities-toggle-tool-btn"
          data-action="toggle-colocated-tool"
          data-skill-id="${escapeHtml(skillId)}"
          data-tool-name="${escapeHtml(name)}"
          data-next-enabled="${enabled ? 'false' : 'true'}"
          class="px-3 py-1.5 rounded-lg text-xs font-semibold transition ${btnClass}">
          ${btnLabel}
        </button>
      </div>
    </div>
  `;
}

/**
 * Starter template for a new Agora `SKILL.md` file.
 * @param {string} skillId
 * @param {string} [title]
 * @returns {string}
 */
export function defaultSkillMarkdown(skillId, title = '') {
  const cleanTitle =
    String(title || '').trim() ||
    String(skillId || 'new-skill')
      .replace(/[-_]+/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  return [
    '---',
    `name: ${cleanTitle}`,
    `description: Describe when agents should activate ${cleanTitle}.`,
    'tools: []',
    '---',
    `# ${cleanTitle}`,
    '',
    '## Overview',
    'Explain how to use this skill folder, its `references/*.md` guides, and its `tools/*.py` callables.',
    '',
  ].join('\n');
}

/**
 * Starter template for a new `references/<name>.md` file.
 * @param {string} stem
 * @returns {string}
 */
export function defaultReferenceMarkdown(stem) {
  const clean = String(stem || 'guide')
    .replace(/\.md$/i, '')
    .replace(/[-_]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
  return `# ${clean}\n\nDetailed reference notes, API payloads, and domain rules.\n`;
}

/**
 * Starter template for a new `tools/<name>.py` colocated Python tool.
 * @param {string} stem
 * @returns {string}
 */
export function defaultToolPython(stem) {
  const fnName = String(stem || 'custom_tool')
    .replace(/\.py$/i, '')
    .replace(/[^a-zA-Z0-9_]/g, '_');
  return [
    `"""${fnName}: describe what this tool does."""`,
    '',
    'RISK = "read_only"',
    '',
    '',
    'def run(query: str) -> dict:',
    '    """Execute the tool and return a JSON-serializable result."""',
    '    return {"query": query, "ok": True}',
    '',
  ].join('\n');
}
