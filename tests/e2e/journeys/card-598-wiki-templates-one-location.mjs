/**
 * CARD-598 journey: Wiki templates: one storage folder, agents create/list/use templates there.
 *
 * 1) AutoReiv allowed tools include wiki_template_create, wiki_template_update, wiki_template_list, wiki_template_read.
 * 2) AutoReiv creates a new template via wiki_template_create:
 *    - Lands in 02_Resources/_Templates/<slug>.md.
 *    - Nothing created in 00_Inbox/ or 01_Notes/.
 *    - GET /api/wiki/templates lists the new template.
 * 3) AutoReiv creates a note from that template via wiki_note_create:
 *    - Lands in 00_Inbox/<note>.md.
 *    - Contains the template sections.
 */
import { waitFor } from './lib/runner.mjs';
import { getJson, isStreaming, openApp, send, trackStreams, waitReplyIdle } from './lib/app.mjs';

const role = (m) => String((m && m.role) || '').toLowerCase();

async function approveAllHitl(page) {
  const buttons = page.locator('button[data-hitl-decision="APPROVED"]');
  const count = await buttons.count();
  let clicked = 0;
  for (let i = 0; i < count; i += 1) {
    const btn = buttons.nth(i);
    if (await btn.isVisible().catch(() => false)) {
      await btn.click().catch(() => {});
      clicked += 1;
      await page.waitForTimeout(1000);
    }
  }
  return clicked;
}

async function waitReplyWithHitl(page, streams, prevCount, { timeoutMs = 400000 } = {}) {
  await waitFor(() => streams.count > prevCount, { timeoutMs: 20000 });
  let quiet = 0;
  await waitFor(async () => {
    const approved = await approveAllHitl(page);
    if (approved > 0) {
      quiet = 0;
      return false;
    }
    quiet = (await isStreaming(page)) ? 0 : quiet + 1;
    return quiet >= 4;
  }, { timeoutMs, intervalMs: 2000 });
  await waitReplyIdle(page, { timeoutMs: 60000 }).catch(() => {});
}

async function ensureChatOpen(page) {
  if (!(await page.locator('#promptInput').isVisible().catch(() => false))) {
    await page.locator('#dock-chat').click();
  }
  await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 15000 });
  if ((await page.locator('#agentSelect').inputValue()) !== 'autoreiv') {
    await page.selectOption('#agentSelect', 'autoreiv');
    await page.waitForTimeout(1000);
  }
}

async function startNewChat(page) {
  await ensureChatOpen(page);
  const sidebarBtn = page.locator('#toggleSidebarBtn');
  const newChatBtn = page.locator('#newChatBtn');
  if (!(await newChatBtn.isVisible().catch(() => false))) {
    if (await sidebarBtn.isVisible().catch(() => false)) {
      await sidebarBtn.click();
      await page.waitForTimeout(600);
    }
  }
  if (await newChatBtn.isVisible().catch(() => false)) {
    await newChatBtn.click();
    await page.waitForTimeout(1000);
  }
  const closeBtn = page.locator('#chatSessionsDrawerCloseBtn');
  if (await closeBtn.isVisible().catch(() => false)) {
    await closeBtn.click().catch(() => {});
    await page.waitForTimeout(500);
  }
}

async function findSession(request, base, text) {
  const list = await getJson(request, `${base}/api/sessions?agent_id=autoreiv`);
  const rows = (Array.isArray(list) ? list : []).sort((x, y) => String(y.updated_at).localeCompare(String(x.updated_at)));
  for (const sess of rows.slice(0, 8)) {
    const msgs = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sess.id)}/messages`);
    if ((Array.isArray(msgs) ? msgs : []).some((m) => role(m) === 'user' && String(m.content || '').includes(text.slice(0, 30)))) {
      return sess.id;
    }
  }
  return rows[0] ? rows[0].id : null;
}

export default {
  id: 'card-598-wiki-templates-one-location',
  card: 'CARD-598',
  title: 'AutoReiv creates wiki templates in 02_Resources/_Templates/ and authors notes from them',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    const slug = `qa-meeting-${viewport.name.toLowerCase()}-${Date.now() % 10000}`;

    await j.step('AutoReiv profile ticks wiki-templates and allows wiki_template_create', async () => {
      const resp = await getJson(request, `${base}/api/agents/autoreiv`);
      const agent = resp.agent || resp;
      const tools = new Set(Array.isArray(agent.allowed_tools) ? agent.allowed_tools : []);
      j.note(`AutoReiv allowed tools: ${Array.from(tools).join(', ')}`);
      for (const reqTool of ['wiki_template_create', 'wiki_template_update', 'wiki_template_list', 'wiki_template_read']) {
        if (!tools.has(reqTool)) {
          throw new Error(`AutoReiv lacks required template tool: ${reqTool}`);
        }
      }
    }, { timeoutMs: 30000 });

    await j.step('AutoReiv creates a new wiki template via wiki_template_create in 02_Resources/_Templates/', async () => {
      await openApp(page, base);
      await startNewChat(page);

      const prompt = `Use the wiki_template_create tool to create a new template with slug "${slug}", title "Meeting Summary", description "Template for recording team meetings", and content "# \${TITLE}\\n\\n## Attendees\\n\\n## Discussion\\n\\n## Action Items".`;
      const prev = streams.count;
      await send(page, prompt);
      await waitReplyWithHitl(page, streams, prev, { timeoutMs: 400000 });

      // Verify session messages
      const sid = await findSession(request, base, prompt);
      if (!sid) throw new Error('Could not find chat session for template creation');
      const msgs = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sid)}/messages`);
      const toolRows = (Array.isArray(msgs) ? msgs : []).filter((m) => role(m) === 'tool');
      const createRow = toolRows.find((m) => String(m.name || '') === 'wiki_template_create');
      if (!createRow) {
        throw new Error(`AutoReiv did not call wiki_template_create (called: ${toolRows.map((t) => t.name).join(', ') || 'none'})`);
      }
      const noteRows = toolRows.filter((m) => String(m.name || '') === 'wiki_note_create');
      if (noteRows.length > 0) {
        throw new Error('AutoReiv wrongly called wiki_note_create when asked to create a template');
      }

      let parsed;
      try { parsed = JSON.parse(String(createRow.content || '')); } catch { parsed = { raw: createRow.content }; }
      if (!parsed.success) {
        throw new Error(`wiki_template_create failed: ${JSON.stringify(parsed)}`);
      }
      j.note(`wiki_template_create result: ${JSON.stringify(parsed)}`);

      // Verify template listing API
      const tmpls = await getJson(request, `${base}/api/wiki/templates`);
      const tmplList = Array.isArray(tmpls) ? tmpls : [];
      const found = tmplList.find((t) => t.slug === slug);
      if (!found) {
        throw new Error(`New template "${slug}" not found in /api/wiki/templates: ${tmplList.map((t) => t.slug).join(', ')}`);
      }

      // Verify specific template API
      const single = await getJson(request, `${base}/api/wiki/template?slug=${encodeURIComponent(slug)}`);
      const tmplPath = String(single.path || '').replace(/\\/g, '/');
      if (!tmplPath.includes('02_Resources/_Templates')) {
        throw new Error(`Template path "${tmplPath}" is not under 02_Resources/_Templates`);
      }
      if (!String(single.content || '').includes('Action Items')) {
        throw new Error(`Template content missing expected sections: ${single.content}`);
      }

      // Ensure no notes created in inbox or notes folder for this template
      const inbox = await getJson(request, `${base}/api/wiki/notes?category=inbox`);
      const inboxNotes = Array.isArray(inbox) ? inbox : (inbox.notes || []);
      const misplacedInbox = inboxNotes.find((n) => String(n.title || '').includes(slug) || String(n.path || '').includes(slug));
      if (misplacedInbox) {
        throw new Error(`Template was erroneously filed in 00_Inbox/: ${misplacedInbox.path}`);
      }
    }, { timeoutMs: 430000 });

    await j.step('AutoReiv creates a note from the template into 00_Inbox/ via wiki_note_create', async () => {
      const noteTitle = `Sprint Planning ${viewport.name} ${Date.now() % 10000}`;
      const prompt = `Use the wiki_note_create tool to create a note titled "${noteTitle}" using the template "${slug}".`;
      const prev = streams.count;
      await send(page, prompt);
      await waitReplyWithHitl(page, streams, prev, { timeoutMs: 400000 });

      // Verify session messages
      const sid = await findSession(request, base, prompt);
      if (!sid) throw new Error('Could not find chat session for note creation');
      const msgs = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sid)}/messages`);
      const toolRows = (Array.isArray(msgs) ? msgs : []).filter((m) => role(m) === 'tool');
      const noteRows = toolRows.filter((m) => String(m.name || '') === 'wiki_note_create');
      if (noteRows.length === 0) {
        throw new Error(`AutoReiv did not call wiki_note_create (called: ${toolRows.map((t) => t.name).join(', ') || 'none'})`);
      }

      const parsedRows = noteRows.map((r) => {
        try { return JSON.parse(String(r.content || '')); } catch { return { raw: r.content }; }
      });
      const successRow = parsedRows.find((p) => p && p.success === true);
      if (!successRow) {
        throw new Error(`wiki_note_create had no successful execution: ${JSON.stringify(parsedRows)}`);
      }
      const notePath = String(successRow.path || successRow.relative_path || '').replace(/\\/g, '/');
      j.note(`wiki_note_create result path: ${notePath}`);
      if (!notePath.startsWith('00_Inbox/')) {
        throw new Error(`Created note was not staged in 00_Inbox/: ${notePath}`);
      }

      // Verify note content contains template structure
      const noteData = await getJson(request, `${base}/api/wiki/note?path=${encodeURIComponent(notePath)}`);
      const content = String(noteData.content || noteData.body || '');
      if (!content.includes('Action Items') && !content.includes('Attendees')) {
        throw new Error(`Created note content does not contain template sections: ${content}`);
      }
    }, { timeoutMs: 430000 });
  },
};
