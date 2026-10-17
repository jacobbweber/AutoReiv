/**
 * CARD-700 journey: Per-turn and per-job structured span waterfall and trace inspector.
 * 1) Creates an AutoReiv chat session and runs a live tool-calling turn (active_project_info).
 * 2) Verifies GET /api/traces?session_id=<sid> and GET /api/traces/<sid> return the hierarchical
 *    parent-child span waterfall (turn -> user_input, compaction, model_request -> model_response,
 *    tool_call -> tool_result, final_answer) with millisecond durations and JSONL persistence.
 * 3) Opens the Execution Journey drawer (#chatShowJourneyBtn -> #chatJourneyDrawer) in Chat,
 *    expands the tool_call span row in [data-trace-waterfall], and verifies the rendered waterfall
 *    and zero horizontal overflow on desktop and phone.
 */
import fs from 'node:fs';
import { clickExpect, waitFor } from './lib/runner.mjs';
import {
  getJson,
  isStreaming,
  openApp,
  openSessionByTitle,
  send,
  trackStreams,
  waitReplyIdle,
} from './lib/app.mjs';

const role = (m) => String((m && m.role) || '').toLowerCase();

export default {
  id: 'card-700-span-waterfall-trace-inspector',
  card: 'CARD-700',
  title: 'Per-turn hierarchical span waterfall trace is exposed via /api/traces and rendered in the Chat Journey drawer',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    let sid = '';
    let title = '';

    await j.step('Create AutoReiv session and run a tool-calling turn in Chat', async () => {
      title = `QA 700 trace ${viewport.name} ${Date.now() % 100000}`;
      const made = await request.post(`${base}/api/sessions`, {
        data: { agent_id: 'autoreiv', title },
      });
      if (!made.ok()) throw new Error(`create session -> ${made.status()}`);
      sid = (await made.json()).id;

      await openApp(page, base);
      try {
        await openSessionByTitle(page, title, { agentId: 'autoreiv' });
      } catch (err) {
        const active = await page.evaluate(() => localStorage.getItem('autoreiv_active_session_id'));
        if (active !== sid) throw err;
        await page.locator('#toggleSidebarBtn').click().catch(() => {});
      }

      const prevStreams = streams.count;
      await send(
        page,
        'Call get_session_info() in this turn and reply in one short sentence with the active agent_id.',
      );
      const started = await waitFor(() => streams.count > prevStreams, { timeoutMs: 20000 });
      if (!started) throw new Error('Stream did not start within 20s');
      const done = await waitFor(
        async () => {
          const streaming = await isStreaming(page);
          if (streaming) return false;
          const rows = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sid)}/messages`).catch(() => []);
          const hasTool = rows.some((m) => role(m) === 'tool' && m.name === 'get_session_info');
          const hasAssistant = rows.some((m) => role(m) === 'assistant' && String(m.content || '').trim().length > 0);
          return hasTool && hasAssistant;
        },
        { timeoutMs: 120000, intervalMs: 1500 },
      );
      if (!done) {
        const rows = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sid)}/messages`).catch(() => []);
        throw new Error(`Expected get_session_info tool call and assistant reply, got messages: ${JSON.stringify(rows.map((r) => ({ role: r.role, name: r.name, content: String(r.content || '').slice(0, 120) })))}`);
      }
      await waitReplyIdle(page, { timeoutMs: 60000 }).catch(() => {});
      j.note(`completed tool-calling turn in session ${sid}`);
    }, { timeoutMs: 180000 });

    await j.step('Verify /api/traces and /api/traces/{trace_id} return parent-child span waterfall and JSONL file', async () => {
      const listPayload = await getJson(request, `${base}/api/traces?session_id=${encodeURIComponent(sid)}`);
      if (!listPayload || !Array.isArray(listPayload.traces) || listPayload.traces.length === 0) {
        throw new Error(`Expected /api/traces?session_id=${sid} to return traces, got: ${JSON.stringify(listPayload)}`);
      }

      const trace = await getJson(request, `${base}/api/traces/${encodeURIComponent(sid)}`);
      if (!trace || !Array.isArray(trace.spans) || trace.spans.length === 0) {
        throw new Error(`Expected spans in /api/traces/${sid}, got: ${JSON.stringify(trace)}`);
      }

      const names = trace.spans.map((s) => s.name);
      for (const required of [
        'turn',
        'user_input',
        'compaction',
        'model_request',
        'model_response',
        'tool_call',
        'tool_result',
        'final_answer',
      ]) {
        if (!names.includes(required)) {
          throw new Error(`Expected span "${required}" in waterfall spans, got: ${names.join(', ')}`);
        }
      }

      const turnSpanIds = new Set(trace.spans.filter((s) => s.name === 'turn').map((s) => s.span_id));
      const modelReq = trace.spans.find((s) => s.name === 'model_request');
      const modelResp = trace.spans.find((s) => s.name === 'model_response' && s.parent_span_id === modelReq?.span_id);
      const toolCall = trace.spans.find((s) => s.name === 'tool_call');
      const toolRes = trace.spans.find((s) => s.name === 'tool_result' && s.parent_span_id === toolCall?.span_id);
      if (
        turnSpanIds.size === 0 ||
        !turnSpanIds.has(modelReq?.parent_span_id) ||
        !modelResp ||
        !turnSpanIds.has(toolCall?.parent_span_id) ||
        !toolRes
      ) {
        throw new Error('Parent-child span IDs did not match expected hierarchy');
      }

      if (!trace.jsonl_path || !fs.existsSync(trace.jsonl_path)) {
        throw new Error(`Expected JSONL trace file on disk at ${trace.jsonl_path}`);
      }
      j.note(`verified ${trace.span_count} spans (${trace.total_duration_ms}ms) and ${trace.jsonl_path}`);
    }, { timeoutMs: 30000 });

    await j.step('Open Execution Journey drawer in Chat and inspect expandable Span Waterfall on UI', async () => {
      const optionsDrawer = page.locator('#chatOptionsDrawer');
      const isOptionsHidden = await optionsDrawer.evaluate((el) => el.classList.contains('hidden')).catch(() => true);
      if (isOptionsHidden) {
        await page.locator('#chatOptionsToggleBtn').click();
      }
      const journeyBtn = page.locator('#chatShowJourneyBtn');
      await journeyBtn.waitFor({ state: 'visible', timeout: 10000 });

      await clickExpect(
        journeyBtn,
        async () => {
          const drawerVisible = await page.locator('#chatJourneyDrawer').isVisible().catch(() => false);
          const hasWaterfall = (await page.locator('#chatJourneyContent [data-trace-waterfall]').count()) > 0;
          return drawerVisible && hasWaterfall;
        },
        { what: 'Execution Journey drawer with [data-trace-waterfall]', label: '#chatShowJourneyBtn', timeoutMs: 15000 },
      );

      for (const stage of ['turn', 'user_input', 'compaction', 'model_request', 'model_response', 'tool_call', 'tool_result', 'final_answer']) {
        const count = await page.locator(`#chatJourneyContent [data-waterfall-span="${stage}"]`).count();
        if (count === 0) {
          throw new Error(`Expected [data-waterfall-span="${stage}"] in #chatJourneyContent`);
        }
      }

      const toolCallDetails = page.locator('#chatJourneyContent [data-waterfall-span="tool_call"]').first();
      await clickExpect(
        toolCallDetails.locator('summary'),
        async () => toolCallDetails.evaluate((el) => el.hasAttribute('open')),
        { what: 'tool_call span details to expand', label: 'tool_call summary', timeoutMs: 10000 },
      );

      const preText = await toolCallDetails.locator('pre').innerText();
      if (!preText.includes('get_session_info')) {
        throw new Error(`Expected expanded tool_call attributes to include get_session_info, got: ${preText}`);
      }

      const overflow = await page.evaluate(() => {
        const doc = document.documentElement;
        return doc.scrollWidth - doc.clientWidth;
      });
      if (overflow > 2) {
        throw new Error(`Expected no horizontal overflow on ${viewport.name}, got ${overflow}px`);
      }
      j.note(`expanded tool_call span in #chatJourneyDrawer on ${viewport.name} (overflow=${overflow}px)`);
    }, { timeoutMs: 45000 });
  },
};
