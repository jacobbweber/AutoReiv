/**
 * CARD-566 journey: with Auto-run ticked, Architect hands a Ready card to Developer with zero approval prompts.
 * 1) Developer runs on the QA Developer model (Nimo) via its agent override in this throwaway environment only.
 * 2) A throwaway git repo in the OS temp folder is the active project with CARD-3 Ready (divide() refuses zero).
 * 3) Auto-run is ticked in the Architect chat; "Hand CARD-3 to Developer." runs hand_off_card and Developer to In Review
 *    on a card branch. No approval card ever appears (the journey never clicks Approve) and no tool row is parked.
 * Checks are structural (git state, card file, tool rows, DOM), never exact model wording.
 */
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { waitFor } from './lib/runner.mjs';
import { HITL_CARD, getJson, isStreaming, openApp, openSessionByTitle, send, trackStreams, waitReplyIdle } from './lib/app.mjs';

const DEV_MODEL = process.env.AUTOREIV_QA_DEVELOPER_MODEL || 'qwen3.6:35b-a3b-65k';
const DEV_URL = process.env.AUTOREIV_QA_DEVELOPER_URL || 'http://192.168.1.29:11434';
const CARD_FILE = 'CARD-3-divide-refuses-zero.md';

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
const README = '# calc\n\nA tiny calculator: `add(a, b)` and `divide(a, b)`.\n';
const CARD3 = `---
id: CARD-3
title: "divide() refuses division by zero"
status: Ready
priority: P2
---

# CARD-3 divide() refuses division by zero

## Why
divide(6, 0) returns Infinity; callers need an error.

## Acceptance criteria
1. \`divide(a, 0)\` throws an \`Error\`, with a node test for it.

## Out of scope
- Other functions.
`;

const git = (cwd, ...args) => execFileSync('git', ['-C', cwd, ...args], { encoding: 'utf8' }).trim();
const role = (m) => String((m && m.role) || '').toLowerCase();
const statusOf = (file) => ((fs.readFileSync(file, 'utf8').match(/^status:\s*(.+)$/m) || [])[1] || '').trim();
const cardsDir = (root) => path.join(root, '.agents', 'cards');

function makeFixture(tag) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), `autoreiv-card566-${tag}-`));
  fs.mkdirSync(cardsDir(root), { recursive: true });
  fs.writeFileSync(path.join(root, 'AGENTS.md'), AGENTS_MD);
  fs.writeFileSync(path.join(root, 'calc.js'), CALC);
  fs.writeFileSync(path.join(root, 'calc.test.js'), TEST);
  fs.writeFileSync(path.join(root, 'README.md'), README);
  fs.writeFileSync(path.join(cardsDir(root), CARD_FILE), CARD3);
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

function toolOrder(rows, from = 0) {
  return rows.slice(from).filter((m) => role(m) === 'tool')
    .map((m) => `${m.name || '?'}${/"success":\s*false|"error":\s*"|=== Hand-off refused/.test(String(m.content || '')) ? '!' : ''}`)
    .join(' > ') || 'none';
}

const parked = (rows) => rows.filter((m) => role(m) === 'tool' && /approval_required|"status":\s*"parked"/.test(String(m.content || '')));

export default {
  id: 'card-566-hand-off-follows-autorun',
  card: 'CARD-566',
  title: 'With Auto-run ticked, Architect hands a Ready card to Developer with zero approval prompts',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    let root = '';
    let sid = '';
    const file = () => path.join(cardsDir(root), CARD_FILE);

    await j.step('Developer runs on the QA Developer model (throwaway environment only)', async () => {
      const dev = await getJson(request, `${base}/api/agents/developer`);
      const body = {
        name: dev.name, description: dev.description, system_prompt: dev.system_prompt, purpose: dev.purpose, tone: dev.tone,
        avatar_icon: dev.avatar_icon, allowed_skill: dev.allowed_skill,
        show_in_chat: dev.show_in_chat, max_turns: dev.max_turns, expected_skills_version: dev.skills_version,
        provider: 'ollama', api_base_url: DEV_URL, model: DEV_MODEL,
      };
      const put = await request.put(`${base}/api/agents/developer`, { data: body });
      if (!put.ok()) throw new Error(`set Developer model -> ${put.status()} ${await put.text()}`);
      const after = await getJson(request, `${base}/api/agents/developer`);
      j.note(`developer (throwaway env only) provider ${after.provider} model ${after.model} at ${after.api_base_url}`);
      if (after.model !== DEV_MODEL) throw new Error('Developer override did not stick');
    }, { timeoutMs: 30000 });

    await j.step('A throwaway repo with CARD-3 Ready is the active project; Auto-run is ticked in an Architect chat', async () => {
      root = makeFixture(viewport.name);
      const res = await request.put(`${base}/api/projects/selected`, { data: { slug: 'calc', path: root } });
      if (!res.ok()) throw new Error(`select project -> ${res.status()}`);
      const title = `QA 566 architect ${viewport.name} ${Date.now() % 100000}`;
      const made = await request.post(`${base}/api/sessions`, { data: { agent_id: 'architect', title } });
      if (!made.ok()) throw new Error(`create session -> ${made.status()}`);
      sid = (await made.json()).id;
      await openApp(page, base);
      try {
        await openSessionByTitle(page, title, { agentId: 'architect' });
      } catch (err) {
        const active = await page.evaluate(() => localStorage.getItem('autoreiv_active_session_id'));
        if (active !== sid) throw err;
        await page.locator('#toggleSidebarBtn').click();
      }
      await page.locator('#chatOptionsToggleBtn').click();
      await page.locator('#approvalToggle').check();
      const checked = await page.locator('#approvalToggle').isChecked();
      await page.locator('#chatOptionsToggleBtn').click().catch(() => {});
      j.note(`fixture ${root}; card ${statusOf(file())}; Auto-run ticked ${checked}`);
      if (!checked) throw new Error('Auto-run did not tick');
    }, { timeoutMs: 60000 });

    await j.step('"Hand CARD-3 to Developer." runs Developer to In Review with zero approval prompts', async () => {
      const from = (await rowsOf(request, base, sid)).length;
      const t0 = Date.now();
      const outcome = async () => (await rowsOf(request, base, sid)).slice(from)
        .some((m) => role(m) === 'tool' && m.name === 'hand_off_card' && /Card status: In Review/.test(String(m.content || '')));
      const devChat = async () => {
        const list = await getJson(request, `${base}/api/sessions?agent_id=developer`).catch(() => []);
        return (Array.isArray(list) ? list : []).find((s) => String(s.id).startsWith(`${sid}_child_`));
      };
      const progress = async () => {
        const kid = await devChat();
        return (await rowsOf(request, base, sid)).length + (kid ? (await rowsOf(request, base, kid.id)).length : 0);
      };
      const n = streams.count;
      await send(page, 'Hand CARD-3 to Developer.');
      await waitFor(() => streams.count > n, { timeoutMs: 15000 });
      let prompts = 0;
      let idle = 0;
      let last = -1;
      await waitFor(async () => {
        const visible = await page.locator(`${HITL_CARD} [data-hitl-decision="APPROVED"]`).count();
        if (visible) { prompts = visible; return true; }
        const deciding = (await page.locator(`${HITL_CARD} .hitl-card-status`).filter({ hasText: /Developer is working/ }).count()) > 0;
        const streaming = (await isStreaming(page)) || deciding;
        if (!streaming && statusOf(file()) === 'In Review' && (await outcome())) return true;
        const p = await progress();
        idle = streaming || p !== last ? 0 : idle + 1;
        last = p;
        return idle >= 150;
      }, { timeoutMs: 2700000, intervalMs: 2000 }).catch(() => {});
      await waitReplyIdle(page, { timeoutMs: 300000 }).catch(() => {});
      const rows = await rowsOf(request, base, sid);
      const kid = await devChat();
      const devRows = kid ? await rowsOf(request, base, kid.id) : [];
      const branch = git(root, 'branch', '--show-current');
      const log = git(root, 'log', '--format=%s', 'main..HEAD').split('\n').filter(Boolean);
      let testsPass = true;
      try { execFileSync('node', ['--test'], { cwd: root, stdio: 'pipe' }); } catch { testsPass = false; }
      const parkedRows = parked(rows.slice(from)).length + parked(devRows).length;
      j.note(`minutes ${((Date.now() - t0) / 60000).toFixed(1)}; approval prompts seen ${prompts}; parked tool rows ${parkedRows}`);
      j.note(`branch ${branch}; commits ${log.join(' | ')}; card ${statusOf(file())}; tests ${testsPass}; dirty '${git(root, 'status', '--porcelain')}'`);
      j.note(`architect tool order: ${toolOrder(rows, from)}`);
      j.note(`developer chat ${kid ? kid.id : 'not listed'}; developer tool order: ${toolOrder(devRows)}`);
      if (prompts) throw new Error(`an approval prompt appeared with Auto-run ticked (${prompts})`);
      if (parkedRows) throw new Error(`${parkedRows} tool rows were parked for approval`);
      if (!(await outcome())) throw new Error('no hand_off_card outcome with Card status: In Review');
      if (!branch || branch === 'main') throw new Error(`not on a card branch (${branch})`);
      if (statusOf(file()) !== 'In Review') throw new Error(`card is ${statusOf(file())}`);
      if (!log.some((s) => /^docs\(card\): CARD-3 In Review/.test(s))) throw new Error('no docs(card) In Review commit');
      if (!testsPass) throw new Error('node --test fails');
      if (git(root, 'status', '--porcelain')) throw new Error('tree not clean');
      if (git(root, 'remote')) throw new Error('fixture gained a remote');
      await page.locator('[data-hand-off-outcome="outcome"]').last().scrollIntoViewIfNeeded().catch(() => {});
      await j.screenshot('autorun-hand-off-outcome');
    }, { timeoutMs: 3200000 });
  },
};
