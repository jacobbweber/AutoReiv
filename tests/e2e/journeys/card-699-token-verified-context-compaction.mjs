/**
 * CARD-699 journey: Token-verified context compaction and non-destructive archive links.
 * 1) Creates an AutoReiv chat session and seeds 6 earlier turns where user messages place paths
 *    (/etc/orion-7/config.yaml), numbers/dates (8770, 2026-10-17), and snake_case identifiers
 *    (max_retry_budget) beyond character 150.
 * 2) Opens the session in Chat, clicks the Compact button in Chat Options, and verifies the toast,
 *    the structured summary sections (Decisions / Open tasks / Key facts) preserving all key tokens,
 *    and the non-destructive archive_links recorded in SQLite and exposed via /context and
 *    /messages?include_archived=true.
 * 3) Sends a live follow-up question in Chat and verifies AutoReiv recalls the preserved tokens
 *    from the compacted summary with no horizontal overflow on desktop or phone.
 */
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { waitFor } from './lib/runner.mjs';
import {
  getJson,
  isStreaming,
  openApp,
  openSessionByTitle,
  send,
  trackStreams,
  waitReplyIdle,
} from './lib/app.mjs';

const REPO_ROOT = process.cwd();
const PYTHON_BIN = path.join(REPO_ROOT, '.venv', 'bin', 'python');
const QA_DB_PATH = path.join(REPO_ROOT, 'scratch', 'live_qa_data', 'database', 'autoreiv.db');

const role = (m) => String((m && m.role) || '').toLowerCase();

function seedSessionMessages(sessionId) {
  const script = `
import sys
from src.domain.gateway.models import ChatMessage, Role
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

repo = SQLiteStateStore(db_path=sys.argv[1])
sid = sys.argv[2]
padding = "We reviewed the telemetry pipeline and discussed rollout readiness across regions with full audit logs. " * 3
turns = [
    (
        Role.USER,
        "Initialize the release planning session for the gateway service.",
    ),
    (
        Role.ASSISTANT,
        padding + "Initialized the release planning session and loaded initial service defaults.",
    ),
    (
        Role.USER,
        padding + "Decided to load /etc/orion-7/config.yaml on port 8770 by 2026-10-17 with max_retry_budget enabled.",
    ),
    (
        Role.ASSISTANT,
        padding + "Acknowledged. I will track the configuration path, port, target date, and retry budget across turns.",
    ),
    (
        Role.USER,
        padding + "Also keep src/application/kernel/context_compactor.py aligned with check_summary.",
    ),
    (
        Role.ASSISTANT,
        padding + "Noted. Context compaction will verify every key token before replacing active turns.",
    ),
    (
        Role.USER,
        "Proceed to the staging verification phase.",
    ),
    (
        Role.ASSISTANT,
        padding + "Staging verification phase started with all health probes active and nominal.",
    ),
    (
        Role.USER,
        "Let us verify the deployment checklist next.",
    ),
    (
        Role.ASSISTANT,
        "Ready to verify the deployment checklist.",
    ),
    (
        Role.USER,
        "Check the staging health status.",
    ),
    (
        Role.ASSISTANT,
        "Staging health checks are green.",
    ),
    (
        Role.USER,
        "Confirm the archive link count is tracked.",
    ),
    (
        Role.ASSISTANT,
        "Archive links are recorded in SQLite.",
    ),
    (
        Role.USER,
        "Prepare the final status note.",
    ),
    (
        Role.ASSISTANT,
        "Standing by for your final question.",
    ),
]
for r, content in turns:
    repo.save_message(sid, "autoreiv", ChatMessage(role=r, content=content))
`;
  execFileSync(PYTHON_BIN, ['-c', script, QA_DB_PATH, sessionId], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
  });
}

async function openCompactButton(page) {
  const drawer = page.locator('#chatOptionsDrawer');
  const isHidden = await drawer.evaluate((el) => el.classList.contains('hidden')).catch(() => true);
  if (isHidden) {
    await page.locator('#chatOptionsToggleBtn').click();
  }
  const btn = page.locator('#chatManualCompactBtn');
  await btn.waitFor({ state: 'visible', timeout: 10000 });
  return btn;
}

export default {
  id: 'card-699-token-verified-context-compaction',
  card: 'CARD-699',
  title: 'Token-verified context compaction preserves key facts past 150 chars and records archive_links',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    let sid = '';
    let title = '';

    await j.step('Create session, seed 8 turns with key tokens past char 150, and open in Chat', async () => {
      title = `QA 699 compact ${viewport.name} ${Date.now() % 100000}`;
      const made = await request.post(`${base}/api/sessions`, {
        data: { agent_id: 'autoreiv', title },
      });
      if (!made.ok()) throw new Error(`create session -> ${made.status()}`);
      sid = (await made.json()).id;

      seedSessionMessages(sid);

      const initialMsgs = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sid)}/messages`);
      if (!Array.isArray(initialMsgs) || initialMsgs.length !== 16) {
        throw new Error(`Expected 16 seeded messages, got ${initialMsgs && initialMsgs.length}`);
      }

      await openApp(page, base);
      try {
        await openSessionByTitle(page, title, { agentId: 'autoreiv' });
      } catch (err) {
        const active = await page.evaluate(() => localStorage.getItem('autoreiv_active_session_id'));
        if (active !== sid) throw err;
        await page.locator('#toggleSidebarBtn').click().catch(() => {});
      }
      j.note(`seeded session ${sid} with 16 messages`);
    }, { timeoutMs: 60000 });

    await j.step('Compact session via Chat Options button and verify structured summary + archive_links', async () => {
      const compactBtn = await openCompactButton(page);
      await compactBtn.click();

      const toast = await waitFor(async () => {
        const count = await page.locator('#toastContainer > div').count();
        if (count === 0) return null;
        const text = (await page.locator('#toastContainer > div').last().innerText()).replace(/\s+/g, ' ').trim();
        return /Compacted \d+ turns?/i.test(text) ? text : null;
      }, { timeoutMs: 15000 });
      if (!toast) {
        throw new Error('Expected "Compacted N turns" toast after clicking Compact');
      }

      // Close options drawer if still open so composer is unobstructed
      const drawer = page.locator('#chatOptionsDrawer');
      const isHidden = await drawer.evaluate((el) => el.classList.contains('hidden')).catch(() => true);
      if (!isHidden) {
        await page.locator('#chatOptionsToggleBtn').click().catch(() => {});
      }

      const activeMsgs = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sid)}/messages`);
      const summaryMsgs = activeMsgs.filter((m) => String(m.content || '').includes('[Summary of earlier conversation:'));
      if (summaryMsgs.length === 0) {
        throw new Error(`Expected compacted summary message in active messages, got ${activeMsgs.length} rows`);
      }

      const summaryMsg = summaryMsgs[0];
      const summaryText = summaryMsgs.map((m) => String(m.content || '')).join('\n');
      for (const heading of ['Decisions', 'Open tasks', 'Key facts']) {
        if (!summaryText.includes(heading)) {
          throw new Error(`Compacted summary missing section "${heading}": ${summaryText}`);
        }
      }
      for (const token of ['/etc/orion-7/config.yaml', '8770', '2026-10-17', 'max_retry_budget']) {
        if (!summaryText.includes(token)) {
          throw new Error(`Compacted summary dropped token "${token}": ${summaryText}`);
        }
      }

      const ctx = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sid)}/context`);
      if (!ctx || !(Number(ctx.archive_links_count) > 0) || !Array.isArray(ctx.archive_links) || ctx.archive_links.length === 0) {
        throw new Error(`Expected archive_links_count > 0 in /context, got: ${JSON.stringify(ctx)}`);
      }

      const allMsgs = await getJson(
        request,
        `${base}/api/sessions/${encodeURIComponent(sid)}/messages?include_archived=true`,
      );
      const archivedRows = allMsgs.filter((m) => m.archived === true);
      if (allMsgs.length < 13 || archivedRows.length !== ctx.archive_links_count) {
        throw new Error(
          `Expected include_archived=true to return all original messages + summary; got total=${allMsgs.length}, archived=${archivedRows.length}, links=${ctx.archive_links_count}`,
        );
      }
      const summaryIds = new Set(summaryMsgs.map((m) => m.id));
      if (!archivedRows.every((m) => summaryIds.has(m.archived_by_summary_id))) {
        throw new Error('Expected every archived message to link to a summary message via archived_by_summary_id');
      }

      j.note(`toast="${toast}"; active=${activeMsgs.length}; archived=${archivedRows.length}; summary=${summaryMsg.id}`);
    }, { timeoutMs: 45000 });

    await j.step('Ask AutoReiv in Chat to recall the preserved tokens from the compacted summary', async () => {
      const prevStreams = streams.count;
      await send(
        page,
        'Without calling any tools, state the exact config file path, port number, target date, and retry budget setting from our earlier compacted conversation.',
      );
      await waitFor(() => streams.count > prevStreams, { timeoutMs: 20000 });
      await waitFor(
        async () => {
          const streaming = await isStreaming(page);
          if (streaming) return false;
          const rows = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sid)}/messages`).catch(() => []);
          const lastAssistant = [...rows].reverse().find((m) => role(m) === 'assistant');
          const text = String((lastAssistant && lastAssistant.content) || '');
          return text.includes('config.yaml') && text.includes('8770');
        },
        { timeoutMs: 120000, intervalMs: 1500 },
      );
      await waitReplyIdle(page, { timeoutMs: 60000 }).catch(() => {});

      const rows = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sid)}/messages`);
      const lastAssistant = [...rows].reverse().find((m) => role(m) === 'assistant');
      const reply = String((lastAssistant && lastAssistant.content) || '');
      for (const expected of ['/etc/orion-7/config.yaml', '8770', '2026-10-17', 'max_retry_budget']) {
        if (!reply.includes(expected)) {
          throw new Error(`Expected assistant reply to recall "${expected}", got: ${reply.slice(0, 300)}`);
        }
      }

      const overflow = await page.evaluate(() => {
        const doc = document.documentElement;
        return doc.scrollWidth - doc.clientWidth;
      });
      if (overflow > 2) {
        throw new Error(`Expected no horizontal overflow on ${viewport.name}, got ${overflow}px`);
      }
      j.note(`assistant recalled tokens on ${viewport.name}: ${reply.slice(0, 140)}`);
    }, { timeoutMs: 180000 });
  },
};
