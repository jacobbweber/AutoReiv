/**
 * Pure formatting utilities [REQ-FE-004, REQ-UNIT-003]
 */

/**
 * Format raw byte count into human-readable SI format.
 * @param {number} bytes
 * @returns {string}
 */
export function formatBytes(bytes) {
  if (!bytes || isNaN(bytes) || bytes <= 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(k)), sizes.length - 1);
  if (i === 0) return `${bytes} B`;
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

/**
 * Format token count into compact string.
 * @param {number} count
 * @returns {string}
 */
export function formatTokenCount(count) {
  if (count == null || isNaN(count) || count <= 0) return '0';
  const num = Number(count);
  if (num >= 1_000_000_000) {
    return `${(num / 1_000_000_000).toFixed(1)}B`;
  }
  if (num >= 1_000_000) {
    return `${(num / 1_000_000).toFixed(1)}M`;
  }
  if (num >= 1_000) {
    return `${(num / 1_000).toFixed(1)}k`;
  }
  return String(num);
}

/**
 * Format a unix timestamp (seconds or ms) or ISO string to localized date/time string.
 * @param {number|string} timestamp
 * @returns {string}
 */
export function formatTimestamp(timestamp) {
  if (!timestamp) return '';
  let date;
  if (typeof timestamp === 'number') {
    date = new Date(timestamp > 1e11 ? timestamp : timestamp * 1000);
  } else {
    date = new Date(timestamp);
  }
  if (isNaN(date.getTime())) return '';
  return date.toLocaleString();
}

/**
 * Format a timestamp into a compact shorthand date/time string for session cards (e.g. "Sep 03, 11:50 AM") [CARD-150, REQ-CHAT-001].
 * @param {number|string} timestamp
 * @returns {string}
 */
export function formatSessionTimestamp(timestamp) {
  if (!timestamp) return '';
  let date;
  if (typeof timestamp === 'number') {
    date = new Date(timestamp > 1e11 ? timestamp : timestamp * 1000);
  } else {
    date = new Date(timestamp);
  }
  if (isNaN(date.getTime())) return '';

  return date.toLocaleString('en-US', {
    month: 'short',
    day: '2-digit',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

/**
 * Pure HTML escaping function.
 * @param {string} text
 * @returns {string}
 */
export function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/**
 * Gracefully parses and formats raw JSON deliverable strings into structured Markdown [REQ-MOB-STREAM-004].
 * @param {string} text
 * @returns {string}
 */
export function formatJsonDeliverableToMarkdown(text) {
  if (!text || typeof text !== 'string') return text || '';
  const trimmed = text.trim();
  if (!trimmed.startsWith('{') || !trimmed.endsWith('}')) return text;

  try {
    const obj = JSON.parse(trimmed);
    if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return text;

    // Check if this looks like a structured deliverable dictionary
    const hasDeliverableKeys = ['goal', 'action_plan', 'wiki_inventory_summary', 'steps', 'summary', 'status'].some(
      (k) => k in obj
    );
    if (!hasDeliverableKeys) return text;

    const sections = [];

    if (obj.goal) {
      sections.push(`## 🎯 Goal: ${obj.goal}\n`);
    }

    if (obj.status) {
      sections.push(`**Status**: \`${obj.status}\`\n`);
    }

    if (obj.wiki_inventory_summary && typeof obj.wiki_inventory_summary === 'object') {
      sections.push('### 📊 Inventory Summary\n');
      const inv = obj.wiki_inventory_summary;
      for (const [k, v] of Object.entries(inv)) {
        const label = k.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
        if (Array.isArray(v)) {
          sections.push(`- **${label}**:`);
          v.forEach((item) => sections.push(`  - ${item}`));
        } else {
          sections.push(`- **${label}**: \`${v}\``);
        }
      }
      sections.push('');
    }

    if (obj.action_plan && typeof obj.action_plan === 'object') {
      const ap = obj.action_plan;
      const title = ap.title || 'Action Plan';
      sections.push(`### 📋 Action Plan: ${title}\n`);
      if (Array.isArray(ap.steps)) {
        ap.steps.forEach((s, idx) => {
          const num = s.step_number || idx + 1;
          const sTitle = s.title || `Step ${num}`;
          sections.push(`#### **Step ${num}: ${sTitle}**`);
          if (s.objective) sections.push(`- **Objective**: ${s.objective}`);
          if (s.actions && Array.isArray(s.actions)) {
            sections.push('- **Actions**:');
            s.actions.forEach((a) => sections.push(`  - ${a}`));
          }
          if (s.success_metric) sections.push(`- **Success Metric**: ${s.success_metric}`);
          sections.push('');
        });
      }
    } else if (Array.isArray(obj.steps)) {
      sections.push('### 📋 Execution Steps\n');
      obj.steps.forEach((s, idx) => {
        const num = s.step_number || idx + 1;
        const sTitle = s.title || `Step ${num}`;
        sections.push(`#### **Step ${num}: ${sTitle}**`);
        if (s.description || s.objective) sections.push(`- ${s.description || s.objective}`);
      });
      sections.push('');
    }

    // Append any remaining top-level keys not handled above
    const handledKeys = new Set(['goal', 'status', 'wiki_inventory_summary', 'action_plan', 'steps']);
    for (const [k, v] of Object.entries(obj)) {
      if (handledKeys.has(k)) continue;
      const label = k.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
      if (typeof v === 'string') {
        sections.push(`### ${label}\n\n${v}\n`);
      } else if (Array.isArray(v)) {
        sections.push(`### ${label}\n`);
        v.forEach((item) => sections.push(`- ${typeof item === 'object' ? JSON.stringify(item) : item}`));
        sections.push('');
      }
    }

    return sections.join('\n').trim();
  } catch {
    return text;
  }
}
