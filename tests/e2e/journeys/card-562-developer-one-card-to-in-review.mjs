/**
 * CARD-562 journey: Developer works one card to In Review on the active project, then files a Proposed card.
 * 1) Developer's tools are the SDLC set (git, cards, checks, search, patch, project info), not the checkout repo_file_* tools.
 * 2) A throwaway git repo in the OS temp folder (AGENTS.md contract, a failing node test, a Ready card) becomes the active project.
 * 3) Asked to work CARD-1, Developer (journey presses Approve) branches, fixes the code, runs the AGENTS.md checks green,
 *    commits, and moves the card to In Review. Nothing is pushed (no remote, no push tool).
 * 4) Asked for a quick audit, Developer files a new card with status Proposed and changes no code.
 * 5) With no active project, Developer's project tools refuse and it points to Projects Studio.
 * Checks are structural (git state, card files, tool rows), never exact model wording.
 */
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { waitFor } from './lib/runner.mjs';
import { HITL_CARD, getJson, isStreaming, openApp, openSessionByTitle, send, trackStreams, waitReplyIdle } from './lib/app.mjs';

const SDLC_TOOLS = ['git_status', 'git_diff', 'git_create_branch', 'git_commit', 'read_card', 'write_card', 'set_card_status',
  'run_project_checks', 'search_project', 'patch_project_file', 'active_project_info'];
const REPO_TOOLS = ['repo_file_read', 'repo_file_list', 'repo_file_write', 'repo_file_patch'];

const AGENTS_MD = `# AGENTS.md - calc

## Project
A tiny JavaScript calculator library used by the QA journey.

## Run
node -e "console.log(require('./calc.js').add(2, 3))"

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

const CALC = `function add(a, b) {\n  return a - b;\n}\n\nfunction divide(a, b) {\n  return a / b;\n}\n\nmodule.exports = { add, divide };\n`;
const TEST = `const test = require('node:test');\nconst assert = require('node:assert');\nconst { add } = require('./calc.js');\n\ntest('add sums two numbers', () => {\n  assert.strictEqual(add(2, 3), 5);\n});\n`;
const CARD = `---\nid: CARD-1\ntitle: "add() returns the sum"\nstatus: Ready\npriority: P2\n---\n\n# CARD-1 add() returns the sum\n\n## Why\nadd(2, 3) returns -1 instead of 5 (calc.js line 2), so calc.test.js fails.\n\n## Scope\n- Fix add() in calc.js.\n\nOut of scope: divide() and anything else.\n\n## Acceptance criteria\n- [ ] add(2, 3) returns 5.\n- [ ] The fast check (node --test) passes.\n\n## Proof\nfast check.\n\n## Plan\n\n## Evidence\n`;

const git = (cwd, ...args) => execFileSync('git', ['-C', cwd, ...args], { encoding: 'utf8' }).trim();
const role = (m) => String((m && m.role) || '').toLowerCase();
const toolNames = (a) => new Set((a.allowed_tools || []).map((t) => String(typeof t === 'string' ? t : (t && t.name) || '')));
const statusOf = (file) => ((fs.readFileSync(file, 'utf8').match(/^status:\s*(.+)$/m) || [])[1] || '').trim();
const cardFiles = (root) => fs.readdirSync(path.join(root, '.agents', 'cards')).filter((f) => /^CARD-.*\.md$/.test(f));

function makeFixture(tag) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), `autoreiv-card562-${tag}-`));
  fs.mkdirSync(path.join(root, '.agents', 'cards'), { recursive: true });
  fs.writeFileSync(path.join(root, 'AGENTS.md'), AGENTS_MD);
  fs.writeFileSync(path.join(root, 'calc.js'), CALC);
  fs.writeFileSync(path.join(root, 'calc.test.js'), TEST);
  fs.writeFileSync(path.join(root, '.agents', 'cards', 'CARD-1-add-returns-sum.md'), CARD);
  git(root, 'init', '-b', 'main');
  git(root, 'config', 'user.name', 'AutoReiv QA');
  git(root, 'config', 'user.email', 'qa@autoreiv.local');
  git(root, 'add', '.');
  git(root, 'commit', '-m', 'chore: fixture');
  return root;
}

async function allRows(request, base, sid) {
  const listed = await getJson(request, `${base}/api/sessions`).catch(() => []);
  const ids = new Set([sid, ...(Array.isArray(listed) ? listed : []).map((x) => String(x.id)).filter((x) => x.startsWith(`${sid}::`))]);
  const out = [];
  for (const id of ids) {
    const rows = await getJson(request, `${base}/api/sessions/${encodeURIComponent(id)}/messages`).catch(() => []);
    if (Array.isArray(rows)) out.push(...rows);
  }
  return out;
}

async function askAndApprove(page, request, base, streams, text, done, timeoutMs) {
  const n = streams.count;
  await send(page, text);
  await waitFor(() => streams.count > n, { timeoutMs: 15000 });
  let approvals = 0;
  await waitFor(async () => {
    const cards = page.locator(HITL_CARD);
    const count = await cards.count();
    for (let i = 0; i < count; i += 1) {
      const approve = cards.nth(i).locator('[data-hitl-decision="APPROVED"]').first();
      if (await approve.isVisible().catch(() => false)) {
        await approve.click();
        approvals += 1;
        await page.waitForTimeout(1500);
        return false;
      }
    }
    return (await done()) && !(await isStreaming(page));
  }, { timeoutMs, intervalMs: 2000 }).catch(() => {});
  await waitReplyIdle(page, { timeoutMs: 60000 }).catch(() => {});
  return approvals;
}

export default {
  id: 'card-562-developer-one-card-to-in-review',
  card: 'CARD-562',
  title: 'Developer takes a card to In Review on the active project and files a Proposed card',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    let root = '';
    let sid = '';
    const cardFile = () => path.join(root, '.agents', 'cards', 'CARD-1-add-returns-sum.md');

    await j.step("Developer's tools are the SDLC set, not the checkout repo_file_* tools", async () => {
      const dev = await getJson(request, `${base}/api/agents/developer`);
      const names = toolNames(dev);
      const missing = SDLC_TOOLS.filter((t) => !names.has(t));
      j.note(`developer model ${dev.model || 'default'}; skills: ${(dev.allowed_skill || []).join(', ')}; missing: ${missing.join(', ') || 'none'}`);
      if (missing.length) throw new Error(`Developer lacks ${missing.join(', ')}`);
      if (REPO_TOOLS.some((t) => names.has(t))) throw new Error('Developer still has checkout repo_file_* tools');
      if ([...names].some((t) => /push|merge/.test(t))) throw new Error('Developer has a push/merge tool');
    }, { timeoutMs: 30000 });

    await j.step('A throwaway git repo in the OS temp folder becomes the active project', async () => {
      root = makeFixture(viewport.name);
      const res = await request.put(`${base}/api/projects/selected`, { data: { slug: 'calc', path: root } });
      if (!res.ok()) throw new Error(`select project -> ${res.status()}`);
      const sel = await getJson(request, `${base}/api/projects/selected`);
      j.note(`fixture ${root}; selected ${JSON.stringify(sel.selected)}`);
      if (path.resolve(String((sel.selected || {}).path || '')) !== path.resolve(root)) throw new Error('project not selected');
      const title = `QA 562 developer ${viewport.name} ${Date.now() % 100000}`;
      const made = await request.post(`${base}/api/sessions`, { data: { agent_id: 'developer', title } });
      if (!made.ok()) throw new Error(`create session -> ${made.status()}`);
      sid = (await made.json()).id;
      await openApp(page, base);
      try {
        await openSessionByTitle(page, title, { agentId: 'developer' });
      } catch (err) {
        // The newest chat opens as the active one, and the drawer lists only the *other* chats.
        const active = await page.evaluate(() => localStorage.getItem('autoreiv_active_session_id'));
        if (active !== sid) throw err;
        j.note('the QA chat was already the open chat (the drawer lists only the other chats)');
        await page.locator('#toggleSidebarBtn').click();
      }
    }, { timeoutMs: 60000 });

    await j.step('Developer works CARD-1: branch, fix, checks green, one commit, card In Review', async () => {
      const approvals = await askAndApprove(page, request, base, streams,
        'Work card CARD-1 in the active project, following your skills, and stop when it is In Review.',
        async () => statusOf(cardFile()) === 'In Review', 1500000);
      const branch = git(root, 'branch', '--show-current');
      const commits = Number(git(root, 'rev-list', '--count', 'main..HEAD') || '0');
      const status = statusOf(cardFile());
      const card = fs.readFileSync(cardFile(), 'utf8');
      const calc = fs.readFileSync(path.join(root, 'calc.js'), 'utf8');
      let testsPass = true;
      try { execFileSync('node', ['--test'], { cwd: root, stdio: 'pipe' }); } catch { testsPass = false; }
      const rows = await allRows(request, base, sid);
      const tools = rows.filter((m) => role(m) === 'tool').map((m) => String(m.name || ''));
      const checksGreen = rows.filter((m) => role(m) === 'tool' && m.name === 'run_project_checks' && /"passed":\s*true/.test(String(m.content || ''))).length;
      const remotes = git(root, 'remote');
      const dirty = git(root, 'status', '--porcelain', '--untracked-files=no');
      j.note(`approvals ${approvals}; branch ${branch}; commits on branch ${commits}; card ${status}; tests pass ${testsPass}; green check runs ${checksGreen}; remotes '${remotes}'; dirty '${dirty}'; tools used: ${[...new Set(tools)].join(', ')}`);
      j.note(`commit log: ${git(root, 'log', '--oneline', 'main..HEAD').replace(/\n/g, ' | ')}`);
      if (branch === 'main' || !branch) throw new Error(`work is not on a card branch (${branch})`);
      if (!/return a \+ b/.test(calc) || !testsPass) throw new Error('add() is not fixed / node --test fails');
      if (!checksGreen) throw new Error('no green run_project_checks row');
      if (commits < 1) throw new Error('no commit on the card branch');
      if (status !== 'In Review') throw new Error(`card is ${status}, not In Review`);
      if (!/node --test|run_project_checks|fast/i.test(card.split('## Evidence')[1] || card)) throw new Error('card has no evidence of the checks');
      if (remotes) throw new Error('fixture gained a remote');
    }, { timeoutMs: 1600000 });

    await j.step('Asked for a quick audit, Developer files a Proposed card and changes no code', async () => {
      const before = new Set(cardFiles(root));
      const head = git(root, 'rev-parse', 'HEAD');
      const calcBefore = fs.readFileSync(path.join(root, 'calc.js'), 'utf8');
      const approvals = await askAndApprove(page, request, base, streams,
        'Now do a quick audit of the active project (skill codebase-audit): file one card for the most important problem you find outside CARD-1. Do not change code.',
        async () => cardFiles(root).some((f) => !before.has(f)), 900000);
      const added = cardFiles(root).filter((f) => !before.has(f));
      const statuses = added.map((f) => statusOf(path.join(root, '.agents', 'cards', f)));
      j.note(`approvals ${approvals}; new cards ${added.join(', ') || 'none'}; statuses ${statuses.join(', ')}`);
      if (!added.length) throw new Error('no new card filed');
      if (statuses.some((s) => s !== 'Proposed')) throw new Error(`new card status ${statuses.join(', ')}, not Proposed`);
      if (git(root, 'rev-parse', 'HEAD') !== head) throw new Error('audit made a commit');
      if (fs.readFileSync(path.join(root, 'calc.js'), 'utf8') !== calcBefore) throw new Error('audit changed code');
    }, { timeoutMs: 960000 });

    await j.step('With no active project, Developer refuses project work and points to Projects Studio', async () => {
      const cleared = await request.put(`${base}/api/projects/selected`, { data: {} });
      if (!cleared.ok()) throw new Error(`clear project -> ${cleared.status()}`);
      const sel = await getJson(request, `${base}/api/projects/selected`);
      if (sel.selected && sel.selected.path) throw new Error('project still selected');
      const head = git(root, 'rev-parse', 'HEAD');
      const refused = async () => {
        const rows = await allRows(request, base, sid);
        const tail = rows.slice(-12);
        return tail.some((m) => /No project is selected|Projects Studio/i.test(String(m.content || '')));
      };
      await askAndApprove(page, request, base, streams,
        'List the cards in the active project.', refused, 300000);
      const rows = await allRows(request, base, sid);
      const toolRefusal = rows.slice(-12).some((m) => role(m) === 'tool' && /No project is selected/.test(String(m.content || '')));
      j.note(`tool refusal row ${toolRefusal}`);
      if (!(await refused())) throw new Error('no refusal naming Projects Studio');
      if (git(root, 'rev-parse', 'HEAD') !== head) throw new Error('fixture changed with no project selected');
    }, { timeoutMs: 360000 });
  },
};
