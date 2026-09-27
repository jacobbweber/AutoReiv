/**
 * CARD-556 journey (D1, Jacob 2026-09-27): with no project selected, write_project_file writes to the AutoReiv
 * scratch folder under the user data folder (<data root>/scratch), never into the checkout, and says where.
 * 1) No project is selected, and the write_project_file description names the scratch folder.
 * 2) Asked in a Developer chat to save a file with write_project_file, after Approve the tool row is a success with
 *    location "scratch", its full path is under <data root>/scratch (not the serve's checkout), and the reply gives
 *    the scratch path. The live QA runner's real-checkout guard (CARD-555) must stay PASS.
 * Checks are structural (tool rows, data dir), never exact model wording.
 */
import { waitFor } from './lib/runner.mjs';
import { HITL_CARD, getJson, isStreaming, openApp, send, trackStreams, waitReplyIdle } from './lib/app.mjs';

const askFor = (file) => `Use the write_project_file tool to save a file named ${file} containing the text "hello 556". Then tell me the full path where it was saved.`;
const REFUSAL_RE = /outside (of )?my (authorized )?domain|not authorized to|\brefuse/i;
const role = (m) => String((m && m.role) || '').toLowerCase();
const norm = (p) => String(p || '').replace(/\\/g, '/').replace(/\/+$/, '').toLowerCase();
const under = (child, parent) => { const c = norm(child); const p = norm(parent); return !!p && (c === p || c.startsWith(`${p}/`)); };

export default {
  id: 'card-556-write-project-file-scratch',
  card: 'CARD-556',
  title: 'write_project_file with no project selected writes to the data-folder scratch, never the checkout',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    let dataRoot = '';

    await j.step('No project is selected and write_project_file names the scratch folder', async () => {
      const dd = await getJson(request, `${base}/api/data-dir`);
      dataRoot = String(dd.root || '');
      const sel = await getJson(request, `${base}/api/projects/selected`).catch(() => ({}));
      const selected = (sel && (sel.selected || sel)) || {};
      const dev = await getJson(request, `${base}/api/agents/developer`);
      const tool = (dev.allowed_tools || []).find((t) => (typeof t === 'string' ? t : t && t.name) === 'write_project_file');
      j.note(`data root ${dataRoot}; selected project ${JSON.stringify(selected).slice(0, 120)}; Developer has write_project_file ${!!tool}`);
      if (!dataRoot) throw new Error('no data root from /api/data-dir');
      if (selected && selected.path) throw new Error(`a project is selected (${selected.path}); this journey needs none`);
      if (!tool) throw new Error('Developer lacks write_project_file');
    }, { timeoutMs: 30000 });

    await j.step('Developer saves a file with write_project_file: it lands in <data root>/scratch and the reply says where', async () => {
      // A session created through the API does not show in the Developer drawer list, so use the chat the Developer
      // picker opens and find it afterwards by the unique file name.
      const file = `card556-note-${viewport.name}-${Date.now() % 100000}.txt`;
      await openApp(page, base);
      if (!(await page.locator('#promptInput').isVisible().catch(() => false))) await page.locator('#dock-chat').click();
      await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 15000 });
      await page.selectOption('#agentSelect', 'developer');
      await page.waitForTimeout(1500);
      const n = streams.count;
      await send(page, askFor(file));
      await waitFor(() => streams.count > n, { timeoutMs: 15000 });
      let approvals = 0;
      let quiet = 0;
      await waitFor(async () => {
        const cards = page.locator(HITL_CARD);
        const count = await cards.count();
        for (let i = 0; i < count; i += 1) {
          const approve = cards.nth(i).locator('[data-hitl-decision="APPROVED"]').first();
          if (await approve.isVisible().catch(() => false)) {
            await approve.click();
            approvals += 1;
            quiet = 0;
            await page.waitForTimeout(1500);
            return false;
          }
        }
        quiet = (await isStreaming(page)) ? 0 : quiet + 1;
        return quiet >= 4;
      }, { timeoutMs: 400000, intervalMs: 2000 });
      await waitReplyIdle(page, { timeoutMs: 60000 }).catch(() => {});

      const listed = await getJson(request, `${base}/api/sessions`).catch(() => []);
      let sid = '';
      for (const x of (Array.isArray(listed) ? listed : []).filter((y) => y.agent_id === 'developer' && !String(y.id).includes('::'))) {
        const r = await getJson(request, `${base}/api/sessions/${encodeURIComponent(x.id)}/messages`).catch(() => []);
        if (Array.isArray(r) && r.some((m) => role(m) === 'user' && String(m.content || '').includes(file))) { sid = String(x.id); break; }
      }
      if (!sid) throw new Error(`no Developer session holds the request for ${file}`);
      const related = [sid, ...(Array.isArray(listed) ? listed : []).map((x) => String(x.id)).filter((id) => id.startsWith(`${sid}::`) || id.startsWith(`${sid}_child_`))];
      const rows = [];
      for (const s2 of new Set(related)) {
        const r = await getJson(request, `${base}/api/sessions/${encodeURIComponent(s2)}/messages`).catch(() => []);
        if (Array.isArray(r)) rows.push(...r);
      }
      const writes = rows.filter((m) => role(m) === 'tool' && String(m.name || '') === 'write_project_file');
      const parsed = writes.map((m) => { try { return JSON.parse(String(m.content || '')); } catch { return { raw: String(m.content || '') }; } });
      const ok = parsed.filter((p) => p && p.success === true);
      const scratch = `${norm(dataRoot)}/scratch`;
      const last = rows.filter((m) => role(m) === 'assistant').map((m) => String(m.content || '')).filter(Boolean).pop() || '';
      j.note(`approvals pressed ${approvals}; write_project_file rows ${writes.length}; ok ${ok.length}${ok.length ? ` (location ${ok[0].location}, full_path ${ok[0].full_path})` : ''}; other rows: ${parsed.filter((p) => !(p && p.success === true)).map((p) => String(p.error || p.raw || '').slice(0, 80)).join(' | ') || 'none'}; reply: ${last.slice(0, 200).replace(/\s+/g, ' ')}`);
      if (REFUSAL_RE.test(last)) throw new Error(`reply contains refusal wording: ${last.slice(0, 160)}`);
      if (!ok.length) throw new Error('no successful write_project_file row');
      const w = ok[ok.length - 1];
      if (w.location !== 'scratch') throw new Error(`write went to location ${w.location}, not scratch`);
      if (!under(w.full_path, scratch)) throw new Error(`full_path ${w.full_path} is not under ${scratch}`);
      if (!/scratch/i.test(String(w.note || ''))) throw new Error('the tool result does not tell the model where the file went');
      // Live QA keeps its throwaway data root in the real checkout's gitignored scratch/ folder, so only the serve's
      // own checkout (the sandbox worktree) is checked here; the runner's real-checkout guard covers the rest.
      if (/autoreiv-qa-checkout/i.test(String(w.full_path))) throw new Error(`full_path ${w.full_path} is inside the serve's checkout`);
      if (!norm(w.full_path).endsWith(`/${file}`)) throw new Error(`full_path ${w.full_path} is not the requested file ${file}`);
      if (!/scratch/i.test(last)) throw new Error('the reply does not say the file went to the scratch folder');
    }, { timeoutMs: 430000 });
  },
};
