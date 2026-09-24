/**
 * CARD-450: Agent Studio platform defaults badge, Reset, and backup Restore.
 * REQ-450-001..004, REQ-450-007..009
 */

import { describe, it, expect } from 'vitest';
import { loadPageHtml } from './template_helper.js';
import {
  RESET_KEPT,
  RESET_REPLACED,
  backupReasonLabel,
  formatBackupTime,
  humanizePackField,
  performBackupRestore,
  performPlatformReset,
  platformSyncEntryFor,
  platformUpdateBadge,
  renderBackupsListMarkup,
  renderResetDialogMarkup,
  restoreDialogMessage,
} from '../../../src/web/static/modules/studios/forge/platform_defaults.js';

const RAW_FIELD = /system_prompt|allowed_skill|pack_tool_names|allowed_tool_names|max_turns|user_modified/;
const CARD_REF = /CARD-\d+|REQ-\d+/;

const report = {
  triggered_at: '2026-09-24T21:00:00+00:00',
  results: [
    { pack_id: 'developer', status: 'skipped_user_modified', reason: 'user_modified=true; platform pack promotion refused', skipped_fields: [] },
    { pack_id: 'tutor', status: 'unchanged', reason: 'seed_content_hash already matches', skipped_fields: [] },
  ],
};

function fakeFetch(routes) {
  const calls = [];
  const impl = async (url, init = {}) => {
    const method = (init.method || 'GET').toUpperCase();
    calls.push(`${method} ${url}`);
    const body = routes[`${method} ${url}`];
    if (body === undefined) return { ok: false, status: 404, json: async () => ({ detail: 'not found' }) };
    return { ok: true, status: 200, json: async () => body };
  };
  return { impl, calls };
}

describe('platform update badge [REQ-450-001/002/007]', () => {
  it('names the edited system prompt and points at Reset for a skipped agent', () => {
    const badge = platformUpdateBadge(platformSyncEntryFor(report, 'developer'));
    expect(badge.text).toBe('Platform update skipped because the system prompt was edited.');
    expect(badge.hint).toContain('Reset to platform defaults');
    expect(badge.text + badge.hint).not.toMatch(RAW_FIELD);
  });

  it('uses customized wording for a first-boot divergence', () => {
    const badge = platformUpdateBadge({ pack_id: 'x', status: 'skipped_user_modified', reason: 'cutover: live profile diverged from seed' });
    expect(badge.text).toBe("Platform update skipped because this agent's instructions, skills, or tools were customized.");
  });

  it('lists kept fields in plain words for a partial update', () => {
    const badge = platformUpdateBadge({ pack_id: 'x', status: 'promoted_partial', skipped_fields: ['system_prompt', 'allowed_skill'] });
    expect(badge.text).toBe('Platform update partly applied. Kept your edited system prompt and skill list.');
    expect(badge.text).not.toMatch(RAW_FIELD);
  });

  it('shows no badge when the agent is up to date or has no entry', () => {
    for (const status of ['unchanged', 'promoted', 'force_reset', 'missing_source']) {
      expect(platformUpdateBadge({ pack_id: 'tutor', status })).toBeNull();
    }
    expect(platformUpdateBadge(platformSyncEntryFor(report, 'tutor'))).toBeNull();
    expect(platformUpdateBadge(platformSyncEntryFor(report, 'nobody'))).toBeNull();
    expect(platformSyncEntryFor(null, 'developer')).toBeNull();
  });

  it('humanizes known fields and falls back to spaced words', () => {
    expect(humanizePackField('system_prompt')).toBe('system prompt');
    expect(humanizePackField('pack_tool_names')).toBe('tool list');
    expect(humanizePackField('some_new_field')).toBe('some new field');
  });
});

describe('reset confirm dialog [REQ-450-004]', () => {
  it('lists replaced vs kept from the promotion contract and mentions the backup', () => {
    expect(RESET_REPLACED.join(' ')).toMatch(/system prompt/i);
    expect(RESET_REPLACED.join(' ')).toMatch(/skill files/i);
    expect(RESET_KEPT.join(' ')).toMatch(/max turns/i);
    expect(RESET_KEPT.join(' ')).toMatch(/model/i);
    expect(RESET_KEPT.join(' ')).toMatch(/provider/i);
    const markup = renderResetDialogMarkup('Developer');
    expect(markup).toContain('Replaced');
    expect(markup).toContain('Kept');
    expect(markup).toContain('A backup of the current version is saved first');
    expect(markup).not.toMatch(RAW_FIELD);
    expect(markup).not.toMatch(CARD_REF);
    expect(renderResetDialogMarkup('<b>x</b>')).not.toContain('<b>x</b>');
  });
});

describe('backups list [REQ-450-008/009]', () => {
  const backups = [
    { id: 'developer-20260924T220000', reason: 'reset_to_platform_defaults', backed_up_at: '2026-09-24T22:00:00+00:00', system_prompt: 'p' },
    { id: 'developer-2', reason: 'force_reset_keep_customizations_off', backed_up_at: '2026-09-23T10:00:00+00:00' },
  ];

  it('formats local readable time with the ISO string kept for the tooltip', () => {
    const t = formatBackupTime('2026-09-24T22:00:00+00:00');
    expect(t.iso).toBe('2026-09-24T22:00:00+00:00');
    expect(t.label).not.toBe(t.iso);
    expect(t.label.length).toBeGreaterThan(5);
    expect(formatBackupTime('garbage').label).toBe('Unknown time');
  });

  it('maps backup reasons to plain words', () => {
    expect(backupReasonLabel('reset_to_platform_defaults')).toBe('Before reset to platform defaults');
    expect(backupReasonLabel('accept_platform_seed')).toBe('Before reset to platform defaults');
    expect(backupReasonLabel('force_reset_keep_customizations_off')).toBe('Before automatic reset (keep customizations was off)');
    expect(backupReasonLabel('')).toBe('Saved snapshot');
  });

  it('renders rows with tooltip, restore buttons, and no inline handlers', () => {
    const markup = renderBackupsListMarkup(backups);
    expect(markup).toContain('title="2026-09-24T22:00:00+00:00"');
    expect(markup).toContain('data-backup-id="developer-20260924T220000"');
    expect((markup.match(/>Restore</g) || []).length).toBe(2);
    expect(markup).not.toMatch(/onclick/i);
    expect(markup).not.toMatch(RAW_FIELD);
    expect(markup).not.toMatch(CARD_REF);
    expect(renderBackupsListMarkup([])).toContain('No backups yet.');
    expect(renderBackupsListMarkup([{ id: '"><script>', reason: '', backed_up_at: '' }])).not.toContain('<script>');
  });

  it('restore dialog says what comes back and what does not', () => {
    const msg = restoreDialogMessage(backups[0]);
    expect(msg).toContain(formatBackupTime(backups[0].backed_up_at).label);
    expect(msg).toMatch(/instructions, skill list, tool list, max turns, and model/);
    expect(msg).toMatch(/Skill files on disk are not changed/);
    expect(msg).toMatch(/platform updates will skip/i);
    expect(msg).toMatch(/Keep my agent customizations/);
    expect(msg).not.toMatch(RAW_FIELD);
  });
});

describe('reset and restore refresh Studio [REQ-450-003/009]', () => {
  const routes = {
    'POST /api/agents/developer/accept-platform-seed': { agent_id: 'developer', sync: { results: [] } },
    'POST /api/agents/developer/pack-content-backups/b1/restore': { agent_id: 'developer' },
    'GET /api/agents/developer': { id: 'developer', max_turns: 77 },
    'GET /api/platform-packs/sync-status': {
      results: [{ pack_id: 'developer', status: 'force_reset' }, { pack_id: 'tutor', status: 'unchanged' }],
    },
    'GET /api/agents/developer/pack-content-backups': { backups: [{ id: 'b1' }] },
  };

  it('posts reset then re-reads the agent, sync status, and backups; badge clears', async () => {
    const { impl, calls } = fakeFetch(routes);
    const out = await performPlatformReset('developer', impl);
    expect(calls).toEqual([
      'POST /api/agents/developer/accept-platform-seed',
      'GET /api/agents/developer',
      'GET /api/platform-packs/sync-status',
      'GET /api/agents/developer/pack-content-backups',
    ]);
    expect(out.agent.max_turns).toBe(77);
    expect(platformUpdateBadge(out.entry)).toBeNull();
    expect(out.backups).toHaveLength(1);
  });

  it('posts restore then refreshes the same way', async () => {
    const { impl, calls } = fakeFetch(routes);
    await performBackupRestore('developer', 'b1', impl);
    expect(calls[0]).toBe('POST /api/agents/developer/pack-content-backups/b1/restore');
    expect(calls.slice(1)).toEqual([
      'GET /api/agents/developer',
      'GET /api/platform-packs/sync-status',
      'GET /api/agents/developer/pack-content-backups',
    ]);
  });

  it('surfaces the server error instead of swallowing it', async () => {
    const { impl } = fakeFetch({});
    await expect(performPlatformReset('developer', impl)).rejects.toThrow('not found');
  });
});

describe('Agent Studio markup [REQ-450-001/003/004/008/009]', () => {
  const html = loadPageHtml();

  it('hosts one Reset button, the badge, backups list, and two accessible dialogs', () => {
    for (const id of [
      'forgePlatformDefaultsSection',
      'forgePlatformUpdateBadge',
      'forgeResetPlatformDefaultsBtn',
      'forgePackBackupsList',
      'resetPlatformDefaultsModal',
      'confirmResetPlatformDefaultsBtn',
      'restorePackBackupModal',
      'confirmRestorePackBackupBtn',
    ]) {
      expect(html).toContain(`id="${id}"`);
    }
    expect(html).toMatch(/id="resetPlatformDefaultsModal"[^>]*role="dialog"[^>]*aria-labelledby="resetPlatformDefaultsTitle"/);
    expect(html).toMatch(/id="restorePackBackupModal"[^>]*role="dialog"[^>]*aria-labelledby="restorePackBackupTitle"/);
    expect(html).not.toContain('Accept platform version');
    expect((html.match(/Reset to platform defaults/g) || []).length).toBeGreaterThanOrEqual(1);
  });
});
