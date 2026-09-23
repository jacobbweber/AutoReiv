/**
 * Operator-facing slug helper shared by Factory and Skill Studio.
 * @param {string} text
 * @returns {string}
 */
export function toSnakeCase(text) {
  return (text || '')
    .toString()
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
}
