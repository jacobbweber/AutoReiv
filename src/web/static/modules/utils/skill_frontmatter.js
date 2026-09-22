/**
 * SKILL.md frontmatter helpers for the Factory workshop [CARD-411].
 * Structured metadata is the editor source of truth. The markdown body is preserved.
 */

const FIELD_ORDER = ['name', 'description', 'version', 'author', 'tier', 'requires_tools', 'safety', 'verification'];
export const SKILL_TIERS = ['platform', 'pack', 'user'];
export const SAFETY_KEYS = ['read_only', 'requires_hitl', 'untrusted_input_allowed'];

function coerceScalar(raw) {
  const text = String(raw ?? '').trim();
  if (text === 'true') return true;
  if (text === 'false') return false;
  if (text === 'null' || text === '~' || text === '') return text === '' ? '' : null;
  if ((text.startsWith('"') && text.endsWith('"')) || (text.startsWith("'") && text.endsWith("'"))) {
    try {
      return JSON.parse(text.startsWith("'") ? `"${text.slice(1, -1).replace(/"/g, '\\"')}"` : text);
    } catch {
      return text.slice(1, -1);
    }
  }
  return text;
}

function parseSimpleYaml(yamlText) {
  const lines = String(yamlText || '').split('\n');
  const root = {};
  const stack = [{ indent: -1, container: root }];
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    if (!line.trim() || line.trim().startsWith('#')) continue;
    const indent = (line.match(/^ */) || [''])[0].length;
    const content = line.slice(indent);
    while (stack.length > 1 && indent <= stack[stack.length - 1].indent) {
      stack.pop();
    }
    const parent = stack[stack.length - 1].container;
    if (content.startsWith('- ')) {
      if (Array.isArray(parent)) parent.push(coerceScalar(content.slice(2)));
      continue;
    }
    const colon = content.indexOf(':');
    if (colon === -1) continue;
    const key = content.slice(0, colon).trim();
    const rest = content.slice(colon + 1).trim();
    if (rest === '' || rest === '|' || rest === '>') {
      const next = lines[i + 1] || '';
      const nextIndent = (next.match(/^ */) || [''])[0].length;
      const nextContent = next.slice(nextIndent).trim();
      if (next && nextIndent > indent && nextContent.startsWith('- ')) {
        const arr = [];
        parent[key] = arr;
        stack.push({ indent, container: arr });
      } else if (next && nextIndent > indent) {
        const obj = {};
        parent[key] = obj;
        stack.push({ indent, container: obj });
      } else {
        parent[key] = '';
      }
      continue;
    }
    parent[key] = coerceScalar(rest);
  }
  return root;
}

function emitScalar(value) {
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (value === null || value === undefined) return '""';
  const text = String(value);
  if (text === '' || /[:#\n]/.test(text) || /^\s|\s$/.test(text) || /^(true|false|null)$/i.test(text)) {
    return JSON.stringify(text);
  }
  return text;
}

function emitNode(lines, key, value, indent) {
  const pad = ' '.repeat(indent);
  if (Array.isArray(value)) {
    lines.push(`${pad}${key}:`);
    value.forEach((item) => {
      if (item && typeof item === 'object') {
        lines.push(`${pad}  -`);
      } else {
        lines.push(`${pad}  - ${emitScalar(item)}`);
      }
    });
    return;
  }
  if (value && typeof value === 'object') {
    lines.push(`${pad}${key}:`);
    Object.keys(value).forEach((child) => {
      emitNode(lines, child, value[child], indent + 2);
    });
    return;
  }
  lines.push(`${pad}${key}: ${emitScalar(value)}`);
}

export function splitSkillMarkdown(text) {
  const raw = String(text || '').replace(/\r\n/g, '\n');
  if (!raw.startsWith('---')) return { meta: {}, body: raw };
  const match = raw.match(/^---\n([\s\S]*?)\n---\n?/);
  if (!match) return { meta: {}, body: raw };
  const loaded = parseSimpleYaml(match[1]);
  const meta = loaded && typeof loaded === 'object' && !Array.isArray(loaded) ? loaded : {};
  return { meta, body: raw.slice(match[0].length) };
}

export function normalizeToolIds(toolIds, catalogIds) {
  const catalog = catalogIds == null
    ? null
    : new Set((catalogIds || []).map((item) => String(item).trim()).filter(Boolean));
  const accepted = [];
  const rejected = [];
  (toolIds || []).forEach((raw) => {
    const toolId = String(raw || '').trim();
    if (!toolId || accepted.includes(toolId) || rejected.includes(toolId)) return;
    if (catalog && !catalog.has(toolId)) {
      rejected.push(toolId);
      return;
    }
    accepted.push(toolId);
  });
  return { accepted, rejected };
}

function normalizeSafety(safety) {
  const source = safety && typeof safety === 'object' ? safety : {};
  return {
    read_only: Boolean(source.read_only),
    requires_hitl: Boolean(source.requires_hitl),
    untrusted_input_allowed: Boolean(source.untrusted_input_allowed),
  };
}

export function serializeSkillMarkdown(meta, body) {
  const source = meta && typeof meta === 'object' ? meta : {};
  const keys = [
    ...FIELD_ORDER.filter((key) => source[key] !== undefined && source[key] !== null),
    ...Object.keys(source).filter((key) => !FIELD_ORDER.includes(key)),
  ];
  const lines = [];
  keys.forEach((key) => emitNode(lines, key, source[key], 0));
  let bodyOut = body || '';
  if (bodyOut && !bodyOut.startsWith('\n')) bodyOut = `\n${bodyOut}`;
  return `---\n${lines.join('\n')}\n---\n${bodyOut}`;
}

export function applyWorkshopMetadata(markdown, fields = {}, catalogIds = null) {
  const { meta, body } = splitSkillMarkdown(markdown);
  const next = { ...meta };
  if (fields.name != null) next.name = String(fields.name).trim();
  if (fields.description != null) next.description = String(fields.description).trim();
  if (fields.tier != null) {
    const tier = String(fields.tier).trim().toLowerCase();
    next.tier = SKILL_TIERS.includes(tier) ? tier : 'pack';
  } else if (next.tier == null) {
    next.tier = 'pack';
  }
  next.safety = normalizeSafety(fields.safety != null ? fields.safety : next.safety);
  const rawTools = fields.requires_tools != null
    ? fields.requires_tools
    : (next.requires_tools || next.tools || []);
  const { accepted, rejected } = normalizeToolIds(rawTools, catalogIds);
  next.requires_tools = accepted;
  delete next.tools;
  return {
    markdown: serializeSkillMarkdown(next, body),
    meta: next,
    rejected,
    requires_tools: accepted,
  };
}

export function formatSafetyLabel(safety) {
  const flags = normalizeSafety(safety);
  const parts = [];
  if (flags.read_only) parts.push('read-only');
  if (flags.requires_hitl) parts.push('requires approval');
  if (flags.untrusted_input_allowed) parts.push('untrusted input');
  return parts.length ? parts.join(', ') : 'no extra safety flags';
}
