/**
 * CARD-563 journey: Architect plans a card with Jacob and hands the Ready card to Developer.
 * 1) Architect has only the planning tools (API check); Developer runs on the QA Developer model (Nimo) via its agent override.
 * 2) A throwaway git repo in the OS temp folder is the active project. Architect files a Ready card for
 *    "divide() should refuse division by zero" and changes no code or git state.
 * 3) Architect's set_card_status Done is refused by the tool (review goes through finish_review).
 * 4) "Hand it to Developer": hand_off_card (one approval) runs Developer inside the hand-off; the journey presses Approve on
 *    Developer's prompts shown in Architect's chat. Asserts card branch, fix + docs(card) commits, In Review with the
 *    tool-written Evidence, clean tree, no remote; Architect's chat shows the outcome; the Developer chat is listed and opens.
 * 5) hand_off_card on a Proposed card is refused; with no project selected it is refused with the no-project message.
 * Checks are structural (git state, card files, tool rows), never exact model wording.
 */
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { waitFor } from './lib/runner.mjs';
import { HITL_CARD, getJson, isStreaming, openApp, openSessionByTitle, send, trackStreams, waitReplyIdle } from './lib/app.mjs';

const PLANNING = ['active_project_info', 'read_project_file', 'search_project', 'list_project_dir', 'read_steering',
  'list_cards', 'read_card', 'write_card', 'set_card_status', 'hand_off_card'];
const FORBIDDEN = ['write_project_file', 'patch_project_file', 'run_project_checks', 'git_commit', 'git_create_branch',
  'cli_exec', 'execute_code', 'handoff_to_agent', 'lookup_agents'];
const DEV_MODEL = process.env.AUTOREIV_QA_DEVELOPER_MODEL || 'qwen3.6:35b-a3b-65k';
const DEV_URL = process.env.AUTOREIV_QA_DEVELOPER_URL || 'http://192.168.1.29:11434';

const AGENTS_MD = `# AGENTS.md - calc

## Project
A tiny JavaScript calculator library used by the QA journey.

## Run
node -e "console.log(require('./calc.js').divide(6, 3))"

## Checks
- fast: node --test

## Branches
- Base branch: main
- One branch per card: \`card/<n>-<short-slug>\`
- Agents never push or merge. A person does.

## Cards
- Folder: \`.agents/cards/\`
- Status: Proposed -> Ready -> In Progress -> In Review -> Done

## Rules
- Don't add a dependency without asking.

## Don't touch
- none
`;

const CALC = `function add(a, b) {\n  return a + b;\n}\n\nfunction divide(a, b) {\n  return a / b;\n}\n\nmodule.exports = { add, divide };\n`;
const TEST = `const test = require('node:test');\nconst assert = require('node:assert');\nconst { add, divide } = require('./calc.js');\n\ntest('add sums two numbers', () => {\n  assert.strictEqual(add(2, 3), 5);\n});\n\ntest('divide divides', () => {\n  assert.strictEqual(divide(6, 3), 2);\n});\n`;
const card = (n, slugTitle, status, body) => `---\nid: CARD-${n}\ntitle: "${slugTitle}"\nstatus: ${status}\npriority: P2\n---\n\n# CARD-${n} ${slugTitle}\n\n${body}\n`;
const CARD1 = card(1, 'add() returns the sum', 'In Review', '## Why\nadd was wrong.\n\n## Evidence\nfixed on card/1-add.');
const CARD2 = card(2, 'README for calc', 'Proposed', '## Why\nThe project has no README.\n\n## Scope\n- Add README.md.');

const git = (cwd, ...args) => execFileSync('git', ['-C', cwd, ...args], { encoding: 'utf8' }).trim();
const role = (m) => String((m && m.role) || '').toLowerCase();
const toolNames = (a) => new Set((a.allowed_tools || []).map((t) => String(typeof t === 'string' ? t : (t && t.name) || '')));
const statusOf = (file) => ((fs.readFileSync(file, 'utf8').match(/^status:\s*(.+)$/m) || [])[1] || '').trim();
const cardsDir = (root) => path.join(root, '.agents', 'cards');
const cardFiles = (root) => fs.readdirSync(cardsDir(root)).filter((f) => /^CARD-.*\.md$/.test(f));

function makeFixture(tag) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), `autoreiv-card563-${tag}-`));
  fs.mkdirSync(cardsDir(root), { recursive: true });
  fs.writeFileSync(path.join(root, 'AGENTS.md'), AGENTS_MD);
  fs.writeFileSync(path.join(root, 'calc.js'), CALC);
  fs.writeFileSync(path.join(root, 'calc.test.js'), TEST);
  fs.writeFileSync(path.join(cardsDir(root), 'CARD-1-add-returns-sum.md'), CARD1);
  fs.writeFileSync(path.join(cardsDir(root), 'CARD-2-readme-for-calc.md'), CARD2);
  git(root, 'init', '-b', 'main');
  git(root, 'config', 'user.name', 'AutoReiv QA');
  git(root, 'config', 'user.email', 'qa@autoreiv.local');
  git(root, 'config', 'core.autocrlf', 'false');
  git(root, 'add', '.');
  git(root, 'commit', '-m', 'chore: fixture');
  return root;
}

async function rowsOf(request, base, sid) {
  const rows = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sid)}/messages`).catch(() => []);
  return Array.isArray(rows) ? rows : [];
}

// Tool calls in order; a trailing ! marks a refused/failed call (as in card-562).
function toolOrder(rows, from = 0) {
  return rows.slice(from).filter((m) => role(m) === 'tool')
    .map((m) => `${m.name || '?'}${/"success":\s*false|"error":\s*"|=== Hand-off refused/.test(String(m.content || '')) ? '!' : ''}`)
    .join(' > ') || 'none';
}

async function askAndApprove(page, streams, text, done, timeoutMs, { idleLimit = 10, progress = null } = {}) {
  const n = streams.count;
  await send(page, text);
  await waitFor(() => streams.count > n, { timeoutMs: 15000 });
  let approvals = 0;
  const approved = [];
  let idlePolls = 0;
  let lastProgress = -1;
  await waitFor(async () => {
    const cards = page.locator(HITL_CARD);
    const count = await cards.count();
    for (let i = 0; i < count; i += 1) {
      const approve = cards.nth(i).locator('[data-hitl-decision="APPROVED"]').first();
      if (await approve.isVisible().catch(() => false)) {
        const label = (await cards.nth(i).innerText().catch(() => '')).replace(/\s+/g, ' ').slice(0, 80);
        await approve.click();
        approvals += 1;
        approved.push(label);
        idlePolls = 0;
        await page.waitForTimeout(1500);
        return false;
      }
    }
    // Approving a hand-off runs Developer inside the decision request: the card says so and the chat is not streaming.
    const deciding = (await page.locator(`${HITL_CARD} .hitl-card-status`).filter({ hasText: /Developer is working|Approving/ }).count()) > 0;
    const streaming = (await isStreaming(page)) || deciding;
    if (!streaming && (await done())) return true;
    const p = progress ? await progress() : 0;
    const moved = p !== lastProgress;
    lastProgress = p;
    idlePolls = streaming || moved ? 0 : idlePolls + 1;
    return idlePolls >= idleLimit;
  }, { timeoutMs, intervalMs: 2000 }).catch(() => {});
  await waitReplyIdle(page, { timeoutMs: 120000 }).catch(() => {});
  return { approvals, approved };
}

export default {
  id: 'card-563-architect-plans-and-hands-off',
  card: 'CARD-563',
  title: 'Architect writes a Ready card and hands it to Developer, who takes it to In Review',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    let root = '';
    let sid = '';
    let newCard = '';
    let newId = '';
    let archTitle = '';
    const snap = async (label) => j.screenshot(label);

    await j.step('Architect has only the planning tools; Developer runs on the QA Developer model', async () => {
      const arch = await getJson(request, `${base}/api/agents/architect`);
      const names = toolNames(arch);
      const missing = PLANNING.filter((t) => !names.has(t));
      const extra = FORBIDDEN.filter((t) => names.has(t));
      j.note(`architect model ${arch.model}; provider ${arch.provider}; skills ${(arch.allowed_skill || []).join(', ')}; tools ${[...names].join(', ')}`);
      if (missing.length) throw new Error(`Architect lacks ${missing.join(', ')}`);
      if (extra.length) throw new Error(`Architect has ${extra.join(', ')}`);
      if (arch.model !== 'default' || (arch.provider || 'default') !== 'default') throw new Error('Architect is not on the default model');
      const dev = await getJson(request, `${base}/api/agents/developer`);
      const body = {
        name: dev.name, description: dev.description, system_prompt: dev.system_prompt, purpose: dev.purpose, tone: dev.tone,
        avatar_icon: dev.avatar_icon, allowed_skill: dev.allowed_skill, pack_tool_names: dev.pack_tool_names,
        show_in_chat: dev.show_in_chat, max_turns: dev.max_turns, expected_skills_version: dev.skills_version,
        provider: 'ollama', api_base_url: DEV_URL, model: DEV_MODEL,
      };
      const put = await request.put(`${base}/api/agents/developer`, { data: body });
      if (!put.ok()) throw new Error(`set Developer model -> ${put.status()} ${await put.text()}`);
      const after = await getJson(request, `${base}/api/agents/developer`);
      j.note(`developer (throwaway env only) provider ${after.provider} model ${after.model} at ${after.api_base_url}`);
      if (after.model !== DEV_MODEL) throw new Error('Developer override did not stick');
      if (names.has('hand_off_card') && toolNames(after).has('hand_off_card')) throw new Error('Developer has hand_off_card');
    }, { timeoutMs: 30000 });

    await j.step('A throwaway git repo is the active project and an Architect chat is open', async () => {
      root = makeFixture(viewport.name);
      const res = await request.put(`${base}/api/projects/selected`, { data: { slug: 'calc', path: root } });
      if (!res.ok()) throw new Error(`select project -> ${res.status()}`);
      const sel = await getJson(request, `${base}/api/projects/selected`);
      j.note(`fixture ${root}`);
      if (path.resolve(String((sel.selected || {}).path || '')) !== path.resolve(root)) throw new Error('project not selected');
      const title = `QA 563 architect ${viewport.name} ${Date.now() % 100000}`;
      archTitle = title;
      const made = await request.post(`${base}/api/sessions`, { data: { agent_id: 'architect', title } });
      if (!made.ok()) throw new Error(`create session -> ${made.status()}`);
      sid = (await made.json()).id;
      await openApp(page, base);
      try {
        await openSessionByTitle(page, title, { agentId: 'architect' });
      } catch (err) {
        const active = await page.evaluate(() => localStorage.getItem('autoreiv_active_session_id'));
        if (active !== sid) throw err;
        j.note('the QA chat was already the open chat');
        await page.locator('#toggleSidebarBtn').click();
      }
    }, { timeoutMs: 60000 });

    await j.step('Architect files a Ready card for divide() by zero and changes no code', async () => {
      const before = new Set(cardFiles(root));
      const head = git(root, 'rev-parse', 'HEAD');
      const found = () => cardFiles(root).filter((f) => !before.has(f));
      const readyCard = () => found().some((f) => statusOf(path.join(cardsDir(root), f)) === 'Ready');
      const r1 = await askAndApprove(page, streams,
        'divide() should refuse division by zero: divide(a, 0) should throw an Error instead of returning Infinity, with a node test for it. '
        + 'Write a card for it. Ask me at most one question; if the scope is clear, file it as Ready.',
        async () => readyCard(), 900000);
      let r2 = { approvals: 0 };
      if (!readyCard()) {
        r2 = await askAndApprove(page, streams, 'Your recommendation is fine. The scope is clear: write the card now with status Ready.',
          async () => readyCard(), 900000);
      }
      const added = found();
      newCard = added.find((f) => statusOf(path.join(cardsDir(root), f)) === 'Ready') || added[0] || '';
      newId = (newCard.match(/^CARD-\d+/) || [''])[0];
      const rows = await rowsOf(request, base, sid);
      j.note(`approvals ${r1.approvals + r2.approvals}; new cards ${added.join(', ') || 'none'}; tool order: ${toolOrder(rows)}`);
      if (!newCard) throw new Error('no new card');
      if (statusOf(path.join(cardsDir(root), newCard)) !== 'Ready') throw new Error(`new card is ${statusOf(path.join(cardsDir(root), newCard))}`);
      if (newId !== 'CARD-3') throw new Error(`new card id ${newId}, expected the next id CARD-3`);
      if (git(root, 'rev-parse', 'HEAD') !== head) throw new Error('Architect made a commit');
      if (fs.readFileSync(path.join(root, 'calc.js'), 'utf8') !== CALC) throw new Error('Architect changed code');
      if (git(root, 'branch', '--show-current') !== 'main') throw new Error('Architect changed branch');
    }, { timeoutMs: 1900000 });

    await j.step("Architect's set_card_status Done is refused by the tool (review goes through finish_review)", async () => {
      const from = (await rowsOf(request, base, sid)).length;
      const refusedRow = async () => (await rowsOf(request, base, sid)).slice(from)
        .some((m) => role(m) === 'tool' && m.name === 'set_card_status' && /finish_review/.test(String(m.content || '')));
      await askAndApprove(page, streams, 'CARD-1 looks good to me. Call set_card_status to move CARD-1 to Done.', refusedRow, 600000);
      if (!(await refusedRow())) {
        await askAndApprove(page, streams, 'Please call set_card_status(CARD-1, Done) anyway so we both see what the tool answers.', refusedRow, 600000);
      }
      const rows = await rowsOf(request, base, sid);
      j.note(`tool order: ${toolOrder(rows, from)}; CARD-1 ${statusOf(path.join(cardsDir(root), 'CARD-1-add-returns-sum.md'))}`);
      if (!(await refusedRow())) throw new Error('no set_card_status refusal row naming finish_review');
      if (statusOf(path.join(cardsDir(root), 'CARD-1-add-returns-sum.md')) !== 'In Review') throw new Error('CARD-1 status changed');
    }, { timeoutMs: 1300000 });

    await j.step('hand_off_card runs Developer to In Review; the outcome shows in Architect chat', async () => {
      const file = () => path.join(cardsDir(root), newCard);
      const from = (await rowsOf(request, base, sid)).length;
      const t0 = Date.now();
      const outcomeRow = async () => (await rowsOf(request, base, sid)).slice(from)
        .some((m) => role(m) === 'tool' && m.name === 'hand_off_card' && /Card status: In Review/.test(String(m.content || '')));
      const devRowCount = async () => {
        const list = await getJson(request, `${base}/api/sessions?agent_id=developer`).catch(() => []);
        const child = (Array.isArray(list) ? list : []).find((s) => String(s.id).startsWith(`${sid}_child_`));
        return (await rowsOf(request, base, sid)).length + (child ? (await rowsOf(request, base, child.id)).length : 0);
      };
      const r = await askAndApprove(page, streams, `Hand ${newId} to Developer.`,
        async () => statusOf(file()) === 'In Review' && (await outcomeRow()), 2700000, { idleLimit: 150, progress: devRowCount });
      const minutes = ((Date.now() - t0) / 60000).toFixed(1);
      await waitReplyIdle(page, { timeoutMs: 300000 }).catch(() => {});
      const rows = await rowsOf(request, base, sid);
      const handRows = rows.slice(from).filter((m) => role(m) === 'tool' && m.name === 'hand_off_card');
      const outcome = handRows.map((m) => String(m.content || '')).reverse().find((c) => /Card status:/.test(c)) || '';
      const branch = git(root, 'branch', '--show-current');
      const log = git(root, 'log', '--format=%s', 'main..HEAD').split('\n').filter(Boolean);
      const cardText = fs.existsSync(file()) ? fs.readFileSync(file(), 'utf8') : '';
      const calc = fs.readFileSync(path.join(root, 'calc.js'), 'utf8');
      let testsPass = true;
      try { execFileSync('node', ['--test'], { cwd: root, stdio: 'pipe' }); } catch { testsPass = false; }
      const dirty = git(root, 'status', '--porcelain');
      const remotes = git(root, 'remote');
      const devSessions = await getJson(request, `${base}/api/sessions?agent_id=developer`).catch(() => []);
      const devChat = (Array.isArray(devSessions) ? devSessions : []).find((s) => String(s.id).startsWith(`${sid}_child_`));
      const devRows = devChat ? await rowsOf(request, base, devChat.id) : [];
      j.note(`minutes ${minutes}; approvals ${r.approvals} (${r.approved.map((a) => a.slice(0, 40)).join(' | ')})`);
      j.note(`branch ${branch}; commits ${log.join(' | ')}; card ${statusOf(file())}; tests pass ${testsPass}; dirty '${dirty}'; remotes '${remotes}'`);
      j.note(`architect tool order: ${toolOrder(rows, from)}`);
      j.note(`developer chat ${devChat ? `${devChat.id} "${devChat.title}"` : 'not listed'}; developer tool order: ${toolOrder(devRows)}`);
      j.note(`outcome block: ${outcome.split('\n').slice(0, 9).join(' / ')}`);
      if (devRows.some((m) => role(m) === 'tool' && /cli_exec|execute_code/.test(String(m.name || '')))) throw new Error('Developer used a shell/code runner');
      if (!branch || branch === 'main') throw new Error(`not on a card branch (${branch})`);
      if (!log.some((s) => /^docs\(card\): CARD-3 In Review/.test(s))) throw new Error('no docs(card) commit');
      if (!log.some((s) => !/^docs\(card\)/.test(s))) throw new Error('no fix commit');
      if (statusOf(file()) !== 'In Review') throw new Error(`card is ${statusOf(file())}`);
      if (!/Recorded by set_card_status \(In Review\):/.test(cardText)) throw new Error('no tool-written Evidence block');
      if (!/b === 0|b == 0|!b\b|b === 0n|division by zero|Division by zero/i.test(calc) || !testsPass) throw new Error('divide() not fixed or node --test fails');
      if (dirty) throw new Error(`tree not clean: ${dirty}`);
      if (remotes) throw new Error('fixture gained a remote');
      if (!outcome || !outcome.includes(`Branch: ${branch}`)) throw new Error('Architect chat has no outcome block with the branch');
      if (!devChat) throw new Error('Developer conversation not listed in Developer chats');
      const shown = await page.locator('[data-hand-off-outcome="outcome"]').count();
      j.note(`outcome cards visible in Architect chat: ${shown}`);
      if (!shown) {
        await page.reload({ waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(3000);
      }
      await page.locator('[data-hand-off-outcome="outcome"]').last().scrollIntoViewIfNeeded().catch(() => {});
      await snap('architect-outcome');
      await openSessionByTitle(page, devChat.title, { agentId: 'developer' }).catch((e) => j.note(`open developer chat: ${e.message}`));
      await page.waitForTimeout(2000);
      await snap('developer-conversation');
    }, { timeoutMs: 3200000 });

    await j.step('hand_off_card refuses a Proposed card, and refuses with no project selected', async () => {
      await openSessionByTitle(page, archTitle, { agentId: 'architect' })
        .catch((e) => j.note(`reopen architect chat: ${e.message}`));
      const head = git(root, 'rev-parse', 'HEAD');
      let from = (await rowsOf(request, base, sid)).length;
      const refused = (re) => async () => (await rowsOf(request, base, sid)).slice(from)
        .some((m) => role(m) === 'tool' && m.name === 'hand_off_card' && re.test(String(m.content || '')));
      const notReady = refused(/Hand-off refused[\s\S]*CARD-2 is Proposed, not Ready/);
      await askAndApprove(page, streams, 'Call hand_off_card for CARD-2 as it is now (do not change its status first).', notReady, 600000);
      const okProposed = await notReady();
      j.note(`proposed refusal ${okProposed}; tool order: ${toolOrder(await rowsOf(request, base, sid), from)}; CARD-2 ${statusOf(path.join(cardsDir(root), 'CARD-2-readme-for-calc.md'))}`);
      const cleared = await request.put(`${base}/api/projects/selected`, { data: {} });
      if (!cleared.ok()) throw new Error(`clear project -> ${cleared.status()}`);
      from = (await rowsOf(request, base, sid)).length;
      const noProject = refused(/Hand-off refused[\s\S]*No project is selected/);
      await askAndApprove(page, streams, `Call hand_off_card for ${newId} again.`, noProject, 600000);
      const okNoProject = await noProject();
      j.note(`no-project refusal ${okNoProject}; tool order: ${toolOrder(await rowsOf(request, base, sid), from)}`);
      await page.locator('[data-hand-off-outcome="refused"]').last().scrollIntoViewIfNeeded().catch(() => {});
      await snap('hand-off-refused');
      if (!okProposed) throw new Error('no refusal row for the Proposed card');
      if (statusOf(path.join(cardsDir(root), 'CARD-2-readme-for-calc.md')) !== 'Proposed') throw new Error('CARD-2 status changed');
      if (!okNoProject) throw new Error('no no-project refusal row');
      if (git(root, 'rev-parse', 'HEAD') !== head) throw new Error('fixture changed during the refusals');
    }, { timeoutMs: 1300000 });
  },
};
