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
