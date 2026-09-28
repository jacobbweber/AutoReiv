/**
 * CARD-454 journey: Tutor still works after its two widest skills were trimmed to the 8-tool budget.
 * 1) Due review in a Tutor chat calls the due ledger tools (education_due_review_list / education_mastery_due).
 * 2) Curriculum curation in a Tutor chat calls the curation tools (education_wiki_curate_from_curriculum / wiki_note_create).
 * Neither turn may hit tool_policy_blocked or an unknown tool. Checked structurally (tool rows), never by exact text.
 */
import { waitFor } from './lib/runner.mjs';
import { getJson, openApp, send, trackStreams, waitReplyIdle } from './lib/app.mjs';

const DUE_ASK = 'Start my flashcard due review for today: show me the first card that is due, or tell me if nothing is due.';
const CURATE_ASK = 'Curate this curriculum outline into my education library as notes:\n- Photosynthesis basics\n- The Calvin cycle';
const BLOCKED_RE = /tool_policy_blocked|unknown tool|not an allowed tool|is not available/i;

const role = (m) => String((m && m.role) || '').toLowerCase();

async function toolRows(request, base, sid) {
  const rows = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sid)}/messages`);
  return (Array.isArray(rows) ? rows : []).filter((m) => role(m) === 'tool');
}

async function findSession(request, base, text) {
  const list = await getJson(request, `${base}/api/sessions?agent_id=tutor`);
  const rows = (Array.isArray(list) ? list : []).sort((x, y) => String(y.updated_at).localeCompare(String(x.updated_at)));
  for (const sess of rows.slice(0, 5)) {
    const msgs = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sess.id)}/messages`);
    if ((Array.isArray(msgs) ? msgs : []).some((m) => role(m) === 'user' && String(m.content || '').includes(text.slice(0, 40)))) return sess.id;
  }
  throw new Error('could not find the Tutor chat that received the message');
}

/** A fresh Tutor chat through the real UI: pick Tutor, New Conversation, send. */
async function askTutor(j, { page, request, base, streams }, label, text, wanted) {
  await openApp(page, base);
  if (!(await page.locator('#promptInput').isVisible().catch(() => false))) await page.locator('#dock-chat').click();
  await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 15000 });
  await page.selectOption('#agentSelect', 'tutor');
  await page.waitForTimeout(1500);
  if (!(await page.locator('#newChatBtn').isVisible().catch(() => false))) await page.locator('#toggleSidebarBtn').click();
  await page.locator('#newChatBtn').click({ timeout: 15000 });
  await page.waitForTimeout(1500);
  const n = streams.count;
  await send(page, text);
  await waitFor(() => streams.count > n, { timeoutMs: 15000 });
  await waitReplyIdle(page, { timeoutMs: 400000 });
  const sid = await findSession(request, base, text);
  const tools = await toolRows(request, base, sid);
  const names = tools.map((m) => String(m.name || '?'));
  j.note(`${label}: tool rows ${names.join(', ') || 'none'}`);
  const blocked = tools.filter((m) => BLOCKED_RE.test(String(m.content || '')));
  if (blocked.length) throw new Error(`a Tutor tool was blocked: ${String(blocked[0].name)} ${String(blocked[0].content).slice(0, 160)}`);
  if (!names.some((nm) => wanted.includes(nm))) throw new Error(`Tutor called none of ${wanted.join(' / ')} (called: ${names.join(', ') || 'none'})`);
}

export default {
  id: 'card-454-tutor-trimmed-skills',
  card: 'CARD-454',
  title: 'Tutor due review and curriculum curation still call their tools after the 8-tool trim',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    const stamp = `${viewport.name} ${Date.now() % 100000}`;
    const ctx = { page, request, base, streams };

    await j.step('Tutor due review calls the due ledger tools', async () => {
      await askTutor(j, ctx, `due review ${stamp}`, DUE_ASK, ['education_due_review_list', 'education_mastery_due']);
    }, { timeoutMs: 430000 });

    await j.step('Tutor curriculum curation calls the curation tools', async () => {
      await askTutor(j, ctx, `curation ${stamp}`, CURATE_ASK, ['education_wiki_curate_from_curriculum', 'wiki_note_create']);
    }, { timeoutMs: 430000 });
  },
};
