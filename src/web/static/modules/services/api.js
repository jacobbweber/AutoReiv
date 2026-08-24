/**
 * Central API Client and HTTP Utilities [REQ-FE-001]
 */

/**
 * Standard JSON fetch helper with error handling.
 * @param {string} url 
 * @param {RequestInit} [options={}] 
 * @returns {Promise<any>}
 */
export async function fetchJSON(url, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    let errorDetail = `HTTP ${response.status} ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson && (errJson.detail || errJson.message)) {
        errorDetail = errJson.detail || errJson.message;
      }
    } catch (_) {
      // Non-JSON error body
    }
    throw new Error(errorDetail);
  }
  return response.json();
}
