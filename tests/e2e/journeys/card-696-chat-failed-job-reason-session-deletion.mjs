/**
 * CARD-696 journey: Chat failed-job reason, session deletion, and tool-round token telemetry.
 * 1) Reopen a chat session with a failed multi-phase job and verify #jobPhaseStatusStrip
 *    displays the failure reason ("Job failed: <reason>") and the failed phase ("Phase 1/2 Build image")
 *    rather than bare "Job failed" or the last queued phase.
 * 2) Delete that session from the Chat sessions drawer (#sessionList) via its delete button
 *    and verify it is removed from #sessionList and GET /api/sessions.
 * 3) Run a tool-calling turn in Chat and verify via GET /api/chat/sessions/{id}/debug that
 *    every turn span (including the tool-call round) records completion_tokens > 0.
 */
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { waitFor } from './lib/runner.mjs';
import { getJson, openApp, send, waitReplyIdle } from './lib/app.mjs';

const AGENT_ID = 'autoreiv';

function seedFailedJobForSession(sessionId, failReason) {
  const pyBin = path.resolve(process.cwd(), '.venv', 'bin', 'python');
  const dataDir = process.env.AUTOREIV_DATA_DIR || path.resolve(process.cwd(), 'scratch', 'live_qa_data');
  const dbPath = path.join(dataDir, 'database', 'autoreiv.db');
  const script = [
    'import sys',
    'from src.infrastructure.memory.sqlite_store import SQLiteStateStore',
    'from src.domain.orchestration.models import PhaseSpec',
    'from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator',
    'sid, reason, db_path = sys.argv[1], sys.argv[2], sys.argv[3]',
    'store = SQLiteStateStore(db_path=db_path)',
    'orch = JobPhaseOrchestrator(store=store)',
    'job = orch.create_job_with_phases(',
    '    goal="Deploy container release",',
    '    agent_id="autoreiv",',
    '    session_id=sid,',
    '    phase_specs=[',
    '        PhaseSpec(name="Build image", assigned_agent_id="autoreiv", success_rule="Image built"),',
    '        PhaseSpec(name="Verify health", assigned_agent_id="autoreiv", success_rule="Health check green"),',
    '    ],',
    ')',
    'phases = store.list_phases_for_job(job.id)',
    'orch.start_phase(phases[0].id)',
    'orch.fail_phase(phases[0].id, reason)',
  ].join('\n');
  execFileSync(pyBin, ['-c', script, sessionId, failReason, dbPath], {
    cwd: process.cwd(),
    env: process.env,
    stdio: 'pipe',
  });
}

async function ensureChatOpen(page) {
  if (!(await page.locator('#promptInput').isVisible().catch(() => false))) {
    const dockChat = page.locator('#dock-chat');
    if (await dockChat.isVisible().catch(() => false)) {
      await dockChat.click();
    } else {
      const mobileMenu = page.locator('#mobileMenuBtn');
      if (await mobileMenu.isVisible().catch(() => false)) {
        await mobileMenu.click();
      }
      await page.locator('#tab-chat').click();
    }
  }
  await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 20000 });
  if ((await page.locator('#agentSelect').inputValue().catch(() => '')) !== AGENT_ID) {
    await page.selectOption('#agentSelect', AGENT_ID);
    await page.waitForTimeout(500);
  }
}

async function openSessionsDrawer(page) {
  const drawer = page.locator('#chatSessionsDrawer');
  if (await drawer.evaluate((el) => el.classList.contains('hidden')).catch(() => true)) {
    await page.locator('#toggleSidebarBtn').click();
  }
  await drawer.waitFor({ state: 'visible', timeout: 10000 });
}

export default {
  id: 'card-696-chat-failed-job-reason-session-deletion',
  card: 'CARD-696',
  title: 'Chat failed-job reason, session deletion, and tool-round token telemetry',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const tag = `${viewport.name}-${Date.now() % 100000}`;
    const sessionTitle = `CARD-696 Failed Job ${tag}`;
    const failReason = 'phase_llm_error: Container registry connection refused';
    let failedSessionId = null;

    await j.step('Reopen a chat session with a failed job and verify #jobPhaseStatusStrip shows the failure reason and failed phase', async () => {
      const res = await request.post(`${base}/api/sessions`, {
        data: { agent_id: AGENT_ID, title: sessionTitle },
      });
      if (!res.ok()) {
        throw new Error(`POST /api/sessions failed: ${res.status()}`);
      }
      const created = await res.json();
      failedSessionId = created.id;
      seedFailedJobForSession(failedSessionId, failReason);

      await openApp(page, base);
      await ensureChatOpen(page);
      await openSessionsDrawer(page);

      const rowReady = await waitFor(
        async () => (await page.locator('#sessionList > div', { hasText: sessionTitle }).count()) >= 1,
        { timeoutMs: 15000 }
      );
      if (!rowReady) {
        throw new Error(`Expected session row "${sessionTitle}" in #sessionList`);
      }

      const row = page.locator('#sessionList > div', { hasText: sessionTitle }).first();
      await row.scrollIntoViewIfNeeded();
      await row.click();

      const stripReady = await waitFor(
        async () => {
          const visible = await page.locator('#jobPhaseStatusStrip').isVisible().catch(() => false);
          if (!visible) return false;
          const txt = await page.locator('#jobPhaseStatusStrip').innerText().catch(() => '');
          return txt.includes('Job failed:') && txt.includes('Container registry connection refused');
        },
        { timeoutMs: 15000 }
      );
      const stripText = await page.locator('#jobPhaseStatusStrip').innerText().catch(() => '');
      if (!stripReady) {
        throw new Error(`Expected #jobPhaseStatusStrip to show failed job reason, got: ${JSON.stringify(stripText)}`);
      }
      if (!stripText.includes('Phase 1/2') || !stripText.includes('Build image')) {
        throw new Error(`Expected #jobPhaseStatusStrip to identify failed Phase 1/2 Build image, got: ${JSON.stringify(stripText)}`);
      }
      if (stripText.includes('Phase 2/2')) {
        throw new Error(`Expected #jobPhaseStatusStrip not to fall through to queued Phase 2/2, got: ${JSON.stringify(stripText)}`);
      }
      j.note(`Verified #jobPhaseStatusStrip shows failed phase and reason: ${stripText.replace(/\s+/g, ' ').trim()}`);
    });

    await j.step('Delete the session from the Chat sessions drawer and verify it is removed from #sessionList and /api/sessions', async () => {
      await openSessionsDrawer(page);
      const delBtn = page.locator(`[data-testid="delete-session-${failedSessionId}"]`);
      await delBtn.scrollIntoViewIfNeeded();
      await delBtn.waitFor({ state: 'visible', timeout: 10000 });

      page.once('dialog', (dialog) => dialog.accept());
      await delBtn.click();

      const removed = await waitFor(
        async () => {
          const domCount = await page.locator(`[data-testid="delete-session-${failedSessionId}"]`).count();
          if (domCount > 0) return false;
          const sessionsResp = await getJson(request, `${base}/api/sessions?agent_id=${AGENT_ID}`);
          const list = Array.isArray(sessionsResp) ? sessionsResp : (sessionsResp.sessions || []);
          return !list.some((s) => s.id === failedSessionId);
        },
        { timeoutMs: 15000 }
      );
      if (!removed) {
        throw new Error(`Expected session ${failedSessionId} to be deleted from DOM and /api/sessions`);
      }
      j.note(`Deleted session ${failedSessionId} via #sessionList delete button`);
    });

    await j.step('Run a tool-calling turn in Chat and verify all turn spans record completion_tokens > 0', async () => {
      const drawer = page.locator('#chatSessionsDrawer');
      if (!(await drawer.evaluate((el) => el.classList.contains('hidden')).catch(() => true))) {
        await page.locator('#toggleSidebarBtn').click();
      }

      await send(
        page,
        'Call the system_info tool right now and tell me the OS name in one short sentence.'
      );
      await waitReplyIdle(page, { timeoutMs: 180000 });

      const sessionsResp = await getJson(request, `${base}/api/sessions?agent_id=${AGENT_ID}`);
      const list = Array.isArray(sessionsResp) ? sessionsResp : (sessionsResp.sessions || []);
      const latest = list[0];
      if (!latest || !latest.id) {
        throw new Error('Expected active AutoReiv session after tool-calling turn');
      }

      const debug = await getJson(request, `${base}/api/chat/sessions/${encodeURIComponent(latest.id)}/debug`);
      const toolPayloads = debug.tool_payloads || [];
      const turnSpans = debug.turn_spans || [];
      if (toolPayloads.length < 1) {
        throw new Error(`Expected at least 1 tool span in session ${latest.id}, got: ${JSON.stringify(toolPayloads)}`);
      }
      if (turnSpans.length < 2) {
        throw new Error(`Expected at least 2 turn spans (tool call + answer) in session ${latest.id}, got: ${JSON.stringify(turnSpans)}`);
      }
      const zeroCompletionSpans = turnSpans.filter((s) => !s.completion_tokens || s.completion_tokens <= 0);
      if (zeroCompletionSpans.length > 0) {
        throw new Error(`Expected every turn span to have completion_tokens > 0, found zero-token spans: ${JSON.stringify(turnSpans)}`);
      }
      j.note(`Verified ${turnSpans.length} turn spans all recorded completion_tokens > 0 (${turnSpans.map((s) => s.completion_tokens).join(', ')})`);
    }, { timeoutMs: 200000 });
  },
};
