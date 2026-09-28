/**
 * CARD-565 journey: a chat message that mentions "acceptance criteria" stays a normal turn (no Formulate/Execute job).
 * 1) A throwaway git repo is the active project with CARD-3 In Review (README line missing, so Returned is right).
 * 2) "Please review CARD-3 against its acceptance criteria and record your verdict." in an Architect chat:
 *    review_card and finish_review run in that same session, no row mentions a job phase ("phase 1/2", "Formulate"),
 *    and no child job session is created. One session, one normal turn.
 * Checks are structural (tool rows, card file), never exact model wording.
 */
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { waitFor } from './lib/runner.mjs';
import { HITL_CARD, getJson, isStreaming, openApp, openSessionByTitle, send, trackStreams, waitReplyIdle } from './lib/app.mjs';

const BRANCH = 'card/3-divide-refuses-zero';
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
const CALC_FIXED = `function add(a, b) {\n  return a + b;\n}\n\nfunction divide(a, b) {\n  if (b === 0) throw new Error('Division by zero');\n  return a / b;\n}\n\nmodule.exports = { add, divide };\n`;
const TEST = `const test = require('node:test');\nconst assert = require('node:assert');\nconst { add, divide } = require('./calc.js');\n\ntest('add sums two numbers', () => {\n  assert.strictEqual(add(2, 3), 5);\n});\n\ntest('divide divides', () => {\n  assert.strictEqual(divide(6, 3), 2);\n});\n`;
const TEST_FIXED = `${TEST}\ntest('divide throws on zero', () => {\n  assert.throws(() => divide(6, 0), Error);\n});\n`;
const README = '# calc\n\nA tiny calculator: `add(a, b)` and `divide(a, b)`.\n';
const CARD3 = (status, evidence) => `---
id: CARD-3
title: "divide() refuses division by zero"
status: ${status}
priority: P2
---

# CARD-3 divide() refuses division by zero

## Why
divide(6, 0) returns Infinity; callers need an error.

## Acceptance criteria
1. \`divide(a, 0)\` throws an \`Error\`, with a node test for it.
2. README.md documents that \`divide\` throws when dividing by zero (one sentence under the existing text).

## Out of scope
- Other functions.

## Evidence
${evidence}
`;

const git = (cwd, ...args) => execFileSync('git', ['-C', cwd, ...args], { encoding: 'utf8' }).trim();
const role = (m) => String((m && m.role) || '').toLowerCase();
const statusOf = (file) => ((fs.readFileSync(file, 'utf8').match(/^status:\s*(.+)$/m) || [])[1] || '').trim();
const cardsDir = (root) => path.join(root, '.agents', 'cards');

function makeFixture(tag) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), `autoreiv-card565-${tag}-`));
  fs.mkdirSync(cardsDir(root), { recursive: true });
  fs.writeFileSync(path.join(root, 'AGENTS.md'), AGENTS_MD);
  fs.writeFileSync(path.join(root, 'calc.js'), CALC);
  fs.writeFileSync(path.join(root, 'calc.test.js'), TEST);
  fs.writeFileSync(path.join(root, 'README.md'), README);
  fs.writeFileSync(path.join(cardsDir(root), CARD_FILE), CARD3('Ready', ''));
  git(root, 'init', '-b', 'main');
  git(root, 'config', 'user.name', 'AutoReiv QA');
  git(root, 'config', 'user.email', 'qa@autoreiv.local');
  git(root, 'config', 'core.autocrlf', 'false');
  git(root, 'add', '.');
  git(root, 'commit', '-m', 'chore: fixture');
  // Seeded round 1 (what Developer would hand in, minus the README line): card branch, fix commit, card In Review.
  git(root, 'switch', '-c', BRANCH);
  fs.writeFileSync(path.join(root, 'calc.js'), CALC_FIXED);
  fs.writeFileSync(path.join(root, 'calc.test.js'), TEST_FIXED);
  git(root, 'commit', '-am', 'feat: divide() throws on division by zero');
  const fix = git(root, 'log', '-1', '--format=%h %s');
  const head = git(root, 'rev-parse', 'HEAD');
  const evidence = `\nRecorded by set_card_status (In Review):\n- Branch: \`${BRANCH}\` (base \`main\`)\n- Commits since base: \`${fix}\`\n`
    + `- Files changed: \`calc.js\`, \`calc.test.js\`\n- Green run_project_checks for HEAD \`${head.slice(0, 12)}\` at seeded: fast (\`node --test\`) - passed\n`;
  fs.writeFileSync(path.join(cardsDir(root), CARD_FILE), CARD3('In Review', evidence));
  git(root, 'add', '.');
  git(root, 'commit', '-m', 'docs(card): CARD-3 In Review');
  return root;
}

async function rowsOf(request, base, sid) {
  const rows = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sid)}/messages`).catch(() => []);
  return Array.isArray(rows) ? rows : [];
}

function toolOrder(rows, from = 0) {
  return rows.slice(from).filter((m) => role(m) === 'tool')
    .map((m) => `${m.name || '?'}${/"success":\s*false|"error":\s*"|=== (Hand-off|Review|Verdict) refused/.test(String(m.content || '')) ? '!' : ''}`)
    .join(' > ') || 'none';
}

async function ask(page, streams, text, done, timeoutMs, { approve = true, idleLimit = 10, progress = null } = {}) {
  const n = streams.count;
  await send(page, text);
  await waitFor(() => streams.count > n, { timeoutMs: 15000 });
  let approvals = 0;
  const approved = [];
  let idlePolls = 0;
  let lastProgress = -1;
  await waitFor(async () => {
    if (approve) {
      const cards = page.locator(HITL_CARD);
      const count = await cards.count();
      for (let i = 0; i < count; i += 1) {
        const btn = cards.nth(i).locator('[data-hitl-decision="APPROVED"]').first();
        if (await btn.isVisible().catch(() => false)) {
          approved.push((await cards.nth(i).innerText().catch(() => '')).replace(/\s+/g, ' ').slice(0, 80));
          await btn.click();
          approvals += 1;
          idlePolls = 0;
          await page.waitForTimeout(1500);
          return false;
        }
      }
    }
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
  id: 'card-565-acceptance-criteria-routes-to-job',
  card: 'CARD-565',
  title: 'A review request that mentions acceptance criteria completes as a normal Architect turn (no job phases)',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    let root = '';
    let sid = '';
    const file = () => path.join(cardsDir(root), CARD_FILE);
    const toolRow = (name, re, from) => async () => (await rowsOf(request, base, sid)).slice(from)
      .some((m) => role(m) === 'tool' && m.name === name && re.test(String(m.content || '')));

    await j.step('A throwaway repo with CARD-3 In Review is the active project; an Architect chat is open', async () => {
      root = makeFixture(viewport.name);
      const res = await request.put(`${base}/api/projects/selected`, { data: { slug: 'calc', path: root } });
      if (!res.ok()) throw new Error(`select project -> ${res.status()}`);
      const title = `QA 565 architect ${viewport.name} ${Date.now() % 100000}`;
      const made = await request.post(`${base}/api/sessions`, { data: { agent_id: 'architect', title } });
      if (!made.ok()) throw new Error(`create session -> ${made.status()}`);
      sid = (await made.json()).id;
      j.note(`fixture ${root}; card ${statusOf(file())}; session ${sid}`);
      await openApp(page, base);
      try {
        await openSessionByTitle(page, title, { agentId: 'architect' });
      } catch (err) {
        const active = await page.evaluate(() => localStorage.getItem('autoreiv_active_session_id'));
        if (active !== sid) throw err;
        await page.locator('#toggleSidebarBtn').click();
      }
    }, { timeoutMs: 60000 });

    await j.step('"Review CARD-3 against its acceptance criteria" runs review_card and finish_review in this session, no job phases', async () => {
      const from = (await rowsOf(request, base, sid)).length;
      const t0 = Date.now();
      const verdict = toolRow('finish_review', /^=== Review (Returned|Done)/, from);
      const r = await ask(page, streams,
        'Please review CARD-3 against its acceptance criteria and record your verdict.',
        async () => (await verdict()), 1500000, { approve: false });
      const rows = (await rowsOf(request, base, sid)).slice(from);
      const phaseRows = rows.filter((m) => /phase \d\/\d|Formulat/i.test(String(m.content || '')) && role(m) !== 'user');
      const list = await getJson(request, `${base}/api/sessions`).catch(() => []);
      const kids = (Array.isArray(list) ? list : []).filter((s) => String(s.id).startsWith(`${sid}_`));
      const phaseUi = await page.getByText(/phase \d\/\d|Formulat/i).count().catch(() => 0);
      j.note(`minutes ${((Date.now() - t0) / 60000).toFixed(1)}; approvals ${r.approvals}; tool order: ${toolOrder(rows)}; card ${statusOf(file())}`);
      j.note(`phase rows ${phaseRows.length}; phase text on screen ${phaseUi}; child sessions ${kids.map((k) => k.id).join(',') || 'none'}`);
      if (!(await toolRow('review_card', /^=== Review packet: CARD-3/, from)())) throw new Error('review_card did not run in the Architect session');
      if (!(await verdict())) throw new Error('no verdict recorded in the Architect session');
      if (phaseRows.length || phaseUi) throw new Error('the turn went through the Formulate/Execute job');
      if (kids.length) throw new Error(`child sessions created: ${kids.map((k) => k.id).join(',')}`);
      if (!['Returned', 'Done'].includes(statusOf(file()))) throw new Error(`card is ${statusOf(file())}`);
      await page.locator('[data-card-review]').last().scrollIntoViewIfNeeded().catch(() => {});
      await j.screenshot('normal-turn-review');
    }, { timeoutMs: 1600000 });
  },
};
