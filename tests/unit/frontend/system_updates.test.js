/**
 * CARD-196 / CARD-724: In-App Software Updates and Upstream Repository Sync UI Tests.
 * Verifies UI controls, bindings, and first-paint rendering in settings/updates.js [REQ-UPD-001..REQ-UPD-005].
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import { initSettingsUpdates } from '../../../src/web/static/modules/studios/settings/updates.js';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

function makeFakeDocument(ids) {
  const elements = new Map();
  function makeEl(id = '') {
    const classes = new Set();
    const attrs = new Map();
    const children = [];
    return {
      id,
      textContent: '',
      innerHTML: '',
      value: '',
      checked: false,
      disabled: false,
      title: '',
      className: '',
      selected: false,
      children,
      get options() {
        return children;
      },
      classList: {
        add: (...names) => names.forEach((n) => classes.add(n)),
        remove: (...names) => names.forEach((n) => classes.delete(n)),
        toggle: (name, force) => {
          const shouldAdd = typeof force === 'boolean' ? force : !classes.has(name);
          if (shouldAdd) classes.add(name);
          else classes.delete(name);
        },
        contains: (name) => classes.has(name),
      },
      setAttribute: (k, v) => attrs.set(k, String(v)),
      getAttribute: (k) => (attrs.has(k) ? attrs.get(k) : null),
      removeAttribute: (k) => attrs.delete(k),
      appendChild: (child) => {
        children.push(child);
        return child;
      },
      addEventListener: () => {},
    };
  }
  ids.forEach((id) => elements.set(id, makeEl(id)));
  return {
    getElementById: (id) => elements.get(id) || null,
    createElement: (tag) => makeEl(tag),
  };
}

describe('System & Software Updates UI [CARD-196, CARD-724, REQ-UPD-001..005]', () => {
  const indexHtml = read('src/web/templates/index.html');
  const settingsJs = read('src/web/static/modules/studios/settings.js');
  const updatesJs = read('src/web/static/modules/studios/settings/updates.js');

  afterEach(() => {
    vi.restoreAllMocks();
    delete globalThis.document;
  });

  // CARD-456: CARD-451 replaced the platform row with commit subject, ahead/behind and last fetch.
  it('renders System & Software Updates card elements in Settings Studio [REQ-UPD-001, CARD-451]', () => {
    expect(indexHtml).toContain('id="settingsSystemUpdatesCard"');
    expect(indexHtml).toContain('id="systemVersionPill"');
    expect(indexHtml).toContain('id="systemDeploymentBadge"');
    expect(indexHtml).toContain('id="systemCommitSha"');
    expect(indexHtml).toContain('id="systemBranchName"');
    expect(indexHtml).toContain('id="systemTreeStatus"');
    expect(indexHtml).toContain('id="systemCommitSubject"');
    expect(indexHtml).toContain('id="systemAheadBehind"');
    expect(indexHtml).toContain('id="systemLastFetch"');
  });

  // CARD-722: Origin URL is pre-populated with official AutoReiv URL and editable with Save/Reset controls.
  it('shows editable Origin URL with default AutoReiv repo and a branch picker [REQ-UPD-002, CARD-722]', () => {
    expect(indexHtml).toMatch(/<input id="updateRemoteName"[^>]*readonly[^>]*value="origin"/);
    expect(indexHtml).toMatch(/<input id="updateRemoteUrl"[^>]*value="https:\/\/github\.com\/jacobbweber\/AutoReiv\.git"/);
    expect(indexHtml).not.toMatch(/<input id="updateRemoteUrl"[^>]*readonly/);
    expect(indexHtml).toContain('id="saveUpdateOriginBtn"');
    expect(indexHtml).toContain('id="resetUpdateOriginBtn"');
    expect(indexHtml).toContain('id="updateBranchSelect"');
    expect(indexHtml).toContain('id="switchBranchBtn"');
    expect(indexHtml).toContain('id="switchBranchStatus"');
    expect(indexHtml).not.toContain('id="updateRepoUrlInput"');
    expect(indexHtml).not.toContain('id="updateBranchInput"');
  });

  it('renders Check for Updates and Apply Update action controls [REQ-UPD-003, REQ-UPD-004]', () => {
    expect(indexHtml).toContain('id="checkForUpdatesBtn"');
    expect(indexHtml).toContain('id="applyUpdateBtn"');
    expect(indexHtml).toContain('id="updateStatusBanner"');
    expect(indexHtml).toContain('id="updateStatusDot"');
    expect(indexHtml).toContain('id="updateStatusMessage"');
    expect(indexHtml).toContain('id="updateNotesContainer"');
    expect(indexHtml).toContain('id="updateReleaseNotesText"');
    expect(indexHtml).toContain('id="updateManualDockerHelper"');
  });

  it('binds System Updates API endpoints in settings/updates.js [REQ-UPD-001..005]', () => {
    expect(updatesJs).toContain('/api/system/version');
    expect(updatesJs).toContain('/api/system/updates/config');
    expect(updatesJs).toContain('/api/system/updates/check');
    expect(updatesJs).toContain('/api/system/updates/apply');
    expect(settingsJs).toContain('loadSystemVersionInfo');
    expect(settingsJs).toContain('loadUpdateConfig');
    expect(updatesJs).toContain('checkForUpdatesBtn');
    expect(updatesJs).toContain('applyUpdateBtn');
  });

  it('populates System & Software Updates card on first paint via initSettingsUpdates [CARD-724]', async () => {
    const ids = [
      'systemVersionPill',
      'systemDeploymentBadge',
      'systemCommitSha',
      'systemCommitSubject',
      'systemBranchName',
      'systemAheadBehind',
      'systemTreeStatus',
      'systemLastFetch',
      'updateRemoteUrl',
      'saveUpdateOriginBtn',
      'resetUpdateOriginBtn',
      'saveUpdateOriginStatus',
      'checkForUpdatesBtn',
      'applyUpdateBtn',
      'updateStatusBanner',
      'updateStatusDot',
      'updateStatusMessage',
      'updateNotesContainer',
      'updateReleaseNotesText',
      'updateManualDockerHelper',
      'updateBranchSelect',
      'switchBranchBtn',
      'switchBranchStatus',
      'autoUpdateEnabled',
      'autoUpdateTime',
      'saveAutoUpdateBtn',
      'saveAutoUpdateStatus',
      'autoUpdateLastResult',
      'updateHistoryList',
      'applyUpdateDisabledReason',
      'updateBranchListHint',
    ];
    for (const id of ids) {
      expect(indexHtml).toContain(`id="${id}"`);
    }
    globalThis.document = makeFakeDocument(ids);

    const mockPayloads = {
      '/api/system/version': {
        current_version: '1.4.0',
        deployment_mode: 'git',
        is_git: true,
        commit: '650fc694',
        subject: 'chore(cards): audit findings',
        branch: 'qa',
        upstream: 'origin/qa',
        ahead: 0,
        behind: 0,
        is_dirty: false,
        last_fetch_at: '2026-10-18T20:00:00Z',
        remote_url: 'https://github.com/jacobbweber/AutoReiv.git',
      },
      '/api/system/updates/config': {
        auto_update_enabled: true,
        auto_update_time: '03:30',
        upstream_repo_url: 'https://github.com/jacobbweber/AutoReiv.git',
      },
      '/api/system/updates/auto-status': {
        last_run_at: '2026-10-18T03:30:00Z',
        last_result: 'success',
        last_message: 'Already up to date.',
      },
      '/api/system/updates/history?limit=15': {
        entries: [
          {
            timestamp: '2026-10-18T03:30:00Z',
            trigger: 'auto',
            result: 'success',
            branch: 'qa',
            from_sha: '1111111',
            to_sha: '650fc69',
            message: 'Fast-forwarded cleanly',
          },
        ],
      },
      '/api/system/updates/branches': {
        branches: [
          { name: 'qa', is_current: true, is_local: true, is_remote: true },
          { name: 'main', is_current: false, is_local: true, is_remote: true },
        ],
      },
    };

    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      const key = String(url);
      if (key in mockPayloads) {
        return {
          ok: true,
          status: 200,
          json: async () => mockPayloads[key],
        };
      }
      return { ok: false, status: 404, json: async () => ({}) };
    });

    const ctrl = initSettingsUpdates();
    await Promise.all([
      ctrl.loadSystemVersionInfo(),
      ctrl.loadUpdateConfig(),
      ctrl.loadAutoUpdateStatus(),
      ctrl.loadUpdateHistory(),
      ctrl.loadBranchList(),
    ]);

    expect(globalThis.document.getElementById('systemVersionPill').textContent).toBe('v1.4.0');
    expect(globalThis.document.getElementById('systemDeploymentBadge').textContent).toBe('Git Clone');
    expect(globalThis.document.getElementById('systemCommitSha').textContent).toBe('650fc694');
    expect(globalThis.document.getElementById('systemCommitSubject').textContent).toBe('chore(cards): audit findings');
    expect(globalThis.document.getElementById('systemBranchName').textContent).toBe('qa');
    expect(globalThis.document.getElementById('systemAheadBehind').textContent).toBe('+0 / -0 vs origin/qa');
    expect(globalThis.document.getElementById('systemTreeStatus').textContent).toBe('Clean');
    expect(globalThis.document.getElementById('updateRemoteUrl').value).toBe('https://github.com/jacobbweber/AutoReiv.git');
    expect(globalThis.document.getElementById('autoUpdateEnabled').checked).toBe(true);
    expect(globalThis.document.getElementById('autoUpdateTime').value).toBe('03:30');
    expect(globalThis.document.getElementById('autoUpdateLastResult').textContent).toContain('Last auto-update: success');
    expect(globalThis.document.getElementById('updateHistoryList').innerHTML).toContain('Fast-forwarded cleanly');
    const branchOpts = globalThis.document.getElementById('updateBranchSelect').options.map((o) => o.value);
    expect(branchOpts).toEqual(['qa', 'main']);
  });
});
