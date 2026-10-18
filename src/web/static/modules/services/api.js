/**
 * Central API Client and HTTP Utilities [REQ-FE-001, REQ-ARCH-005]
 * Provides standard JSON fetch helper and structured REST methods with error unwrapping.
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
    ...(options.headers || {}),
  };

  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    let errorDetail = `HTTP ${response.status} ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson && (errJson.detail || errJson.message || errJson.error)) {
        errorDetail = errJson.detail || errJson.message || errJson.error;
      }
    } catch {
      // Non-JSON error body
    }
    throw new Error(typeof errorDetail === 'string' ? errorDetail : JSON.stringify(errorDetail));
  }
  return response.json();
}

/**
 * Build a query string from a params object.
 * @param {Object} [params]
 * @returns {string}
 */
export function buildQueryString(params) {
  if (!params || typeof params !== 'object') return '';
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null) {
      searchParams.append(key, String(val));
    }
  });
  const qs = searchParams.toString();
  return qs ? `?${qs}` : '';
}

/**
 * Standardized API client facade with REST verbs and domain namespaces.
 */
export const api = {
  /**
   * Perform a GET request with optional query parameters.
   * @param {string} url
   * @param {Object} [params]
   * @param {RequestInit} [options]
   */
  async get(url, params = null, options = {}) {
    const qs = params ? buildQueryString(params) : '';
    return fetchJSON(`${url}${qs}`, { ...options, method: 'GET' });
  },

  /**
   * Perform a POST request with JSON body.
   * @param {string} url
   * @param {any} [body]
   * @param {RequestInit} [options]
   */
  async post(url, body = null, options = {}) {
    const opts = { ...options, method: 'POST' };
    if (body !== null && body !== undefined) {
      opts.body = typeof body === 'string' ? body : JSON.stringify(body);
    }
    return fetchJSON(url, opts);
  },

  /**
   * Perform a PUT request with JSON body.
   * @param {string} url
   * @param {any} [body]
   * @param {RequestInit} [options]
   */
  async put(url, body = null, options = {}) {
    const opts = { ...options, method: 'PUT' };
    if (body !== null && body !== undefined) {
      opts.body = typeof body === 'string' ? body : JSON.stringify(body);
    }
    return fetchJSON(url, opts);
  },

  /**
   * Perform a DELETE request.
   * @param {string} url
   * @param {RequestInit} [options]
   */
  async delete(url, options = {}) {
    return fetchJSON(url, { ...options, method: 'DELETE' });
  },

  // Domain API Endpoints
  agents: {
    list: () => api.get('/api/agents'),
    get: (id) => api.get(`/api/agents/${encodeURIComponent(id)}`),
  },

  sessions: {
    list: (agentId = null) => api.get('/api/sessions', agentId ? { agent_id: agentId } : null),
    get: (id) => api.get(`/api/sessions/${encodeURIComponent(id)}`),
    delete: (id) => api.delete(`/api/sessions/${encodeURIComponent(id)}`),
  },

  routines: {
    list: () => api.get('/api/routines'),
    get: (id) => api.get(`/api/routines/${encodeURIComponent(id)}`),
    trigger: (id) => api.post(`/api/routines/${encodeURIComponent(id)}/trigger`),
  },

  capabilities: {
    tree: () => api.get('/api/capabilities/tree'),
    readFile: (skillId, relPath = 'SKILL.md') =>
      api.get(`/api/capabilities/skills/${encodeURIComponent(skillId)}/file`, { path: relPath }),
    saveFile: (skillId, relPath, content, sampleArguments = null) =>
      api.put(`/api/capabilities/skills/${encodeURIComponent(skillId)}/file`, {
        path: relPath,
        content,
        ...(sampleArguments ? { sample_arguments: sampleArguments } : {}),
      }),
    toggleTool: (skillId, toolName, enabled) =>
      api.post(
        `/api/capabilities/skills/${encodeURIComponent(skillId)}/tools/${encodeURIComponent(toolName)}/toggle`,
        { enabled: Boolean(enabled) },
      ),
    listMcpServers: (scope = 'platform', agentId = '') => {
      if (scope === 'agent') {
        const cleanAgent = String(agentId || '').trim();
        if (!cleanAgent) return Promise.resolve([]);
        return api.get(`/api/agents/${encodeURIComponent(cleanAgent)}/mcp`);
      }
      return api.get('/api/settings/mcp');
    },
    saveMcpServer: (scope = 'platform', agentId = '', body = {}) => {
      const url =
        scope === 'agent'
          ? `/api/agents/${encodeURIComponent(String(agentId || '').trim())}/mcp`
          : '/api/settings/mcp';
      return api.post(url, body);
    },
    deleteMcpServer: (scope = 'platform', agentId = '', serverName = '') => {
      const cleanName = encodeURIComponent(String(serverName || '').trim());
      const url =
        scope === 'agent'
          ? `/api/agents/${encodeURIComponent(String(agentId || '').trim())}/mcp/${cleanName}`
          : `/api/settings/mcp/${cleanName}`;
      return api.delete(url);
    },
    testMcpServer: (scope = 'platform', agentId = '', body = {}) => {
      const url =
        scope === 'agent'
          ? `/api/agents/${encodeURIComponent(String(agentId || '').trim())}/mcp/test`
          : '/api/settings/mcp/test';
      return api.post(url, body);
    },
    listVaultCredentials: () => api.get('/api/vault/credentials'),
    listRcaProposals: (params = null) => api.get('/api/telemetry/rca-proposals', params),
    dismissRcaProposal: (proposalId) =>
      api.post(`/api/telemetry/rca-proposals/${encodeURIComponent(String(proposalId || '').trim())}/dismiss`),
  },
};

