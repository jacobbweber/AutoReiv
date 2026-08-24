/**
 * Safe local storage wrapper with fallback [REQ-FE-004]
 */

export function storageGet(key, fallback = null) {
  try {
    if (typeof localStorage === 'undefined') return fallback;
    const item = localStorage.getItem(key);
    return item !== null ? item : fallback;
  } catch (e) {
    return fallback;
  }
}

export function storageSet(key, value) {
  try {
    if (typeof localStorage === 'undefined') return;
    localStorage.setItem(key, typeof value === 'string' ? value : JSON.stringify(value));
  } catch (e) {
    // Storage quota exceeded or disabled
  }
}

export function storageRemove(key) {
  try {
    if (typeof localStorage === 'undefined') return;
    localStorage.removeItem(key);
  } catch (e) {
    // Ignored
  }
}
