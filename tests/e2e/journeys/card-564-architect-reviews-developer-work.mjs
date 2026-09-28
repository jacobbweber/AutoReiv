/**
 * CARD-564 journey: Architect reviews Developer's work: one Return with notes, Developer rework on the same branch, then Done.
 * 1) Architect has review_card and finish_review and still no code-writing, commit or shell tool (API check);
 *    Developer runs on the QA Developer model (Nimo) via its agent override in this throwaway environment only.
 * 2) A throwaway git repo in the OS temp folder is the active project. Round 1 of the work is seeded by the harness
 *    (so the Return is deterministic): CARD-3 needs divide() to throw on zero AND a README line; the card branch has
 *    the code fix and test but no README line, and the card is In Review with the tool-written Evidence.
 * 3) "Review CARD-3": review_card runs (diff, commits, fresh checks) and finish_review records Returned with notes
 *    naming the README; the card has ## Review round 1, review_rounds 1, and a card-only commit. No approval click.
 * 4) "Hand CARD-3 back to Developer": hand_off_card (one approval) runs Developer, who adds the README line on the
 *    existing card branch and brings the card back to In Review (Developer's prompts are approved by the journey).
 * 5) "Review CARD-3 again": Done with a written review (round 2); main is unchanged (no merge), no remote, clean tree.
 * Checks are structural (git state, card files, tool rows), never exact model wording.
 */
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { waitFor } from './lib/runner.mjs';
import { HITL_CARD, getJson, isStreaming, openApp, openSessionByTitle, send, trackStreams, waitReplyIdle } from './lib/app.mjs';

const REVIEW_TOOLS = ['review_card', 'finish_review', 'hand_off_card', 'read_card', 'list_cards'];
const FORBIDDEN = ['write_project_file', 'patch_project_file', 'run_project_checks', 'git_commit', 'git_create_branch',
  'cli_exec', 'execute_code', 'handoff_to_agent', 'lookup_agents'];
const DEV_MODEL = process.env.AUTOREIV_QA_DEVELOPER_MODEL || 'qwen3.6:35b-a3b-65k';
const DEV_URL = process.env.AUTOREIV_QA_DEVELOPER_URL || 'http://192.168.1.29:11434';
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
const toolNames = (a) => new Set((a.allowed_tools || []).map((t) => String(typeof t === 'string' ? t : (t && t.name) || '')));
const statusOf = (file) => ((fs.readFileSync(file, 'utf8').match(/^status:\s*(.+)$/m) || [])[1] || '').trim();
const cardsDir = (root) => path.join(root, '.agents', 'cards');
const readmeDocumentsZero = (root) => /zero/i.test(fs.readFileSync(path.join(root, 'README.md'), 'utf8'));

function makeFixture(tag) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), `autoreiv-card564-${tag}-`));
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
  id: 'card-564-architect-reviews-developer-work',
  card: 'CARD-564',
  title: 'Architect returns a card with notes, Developer reworks it on the same branch, Architect marks it Done (no merge)',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    let root = '';
    let sid = '';
    let archTitle = '';
    let mainHead = '';
    const file = () => path.join(cardsDir(root), CARD_FILE);
    const cardText = () => fs.readFileSync(file(), 'utf8');
    const snap = async (label) => j.screenshot(label);
    const toolRow = (name, re, from) => async () => (await rowsOf(request, base, sid)).slice(from)
      .some((m) => role(m) === 'tool' && m.name === name && re.test(String(m.content || '')));
    const onlyCardChanged = () => git(root, 'show', '--name-only', '--format=', 'HEAD') === `.agents/cards/${CARD_FILE}`;

    await j.step('Architect has the review tools and no code-writing tool; Developer runs on the QA Developer model', async () => {
      const arch = await getJson(request, `${base}/api/agents/architect`);
      const names = toolNames(arch);
      const missing = REVIEW_TOOLS.filter((t) => !names.has(t));
      const extra = FORBIDDEN.filter((t) => names.has(t));
      j.note(`architect model ${arch.model}; skills ${(arch.allowed_skill || []).join(', ')}; tools ${[...names].join(', ')}`);
      if (missing.length) throw new Error(`Architect lacks ${missing.join(', ')}`);
      if (extra.length) throw new Error(`Architect has ${extra.join(', ')}`);
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
      if (toolNames(after).has('finish_review') || toolNames(after).has('review_card')) throw new Error('Developer has the review tools');
    }, { timeoutMs: 30000 });

    await j.step('A throwaway repo with CARD-3 In Review (round 1 seeded without the README line) is the active project', async () => {
      root = makeFixture(viewport.name);
      mainHead = git(root, 'rev-parse', 'main');
      const res = await request.put(`${base}/api/projects/selected`, { data: { slug: 'calc', path: root } });
      if (!res.ok()) throw new Error(`select project -> ${res.status()}`);
      j.note(`fixture ${root}; branch ${git(root, 'branch', '--show-current')}; card ${statusOf(file())}`);
      archTitle = `QA 564 architect ${viewport.name} ${Date.now() % 100000}`;
      const made = await request.post(`${base}/api/sessions`, { data: { agent_id: 'architect', title: archTitle } });
      if (!made.ok()) throw new Error(`create session -> ${made.status()}`);
      sid = (await made.json()).id;
      await openApp(page, base);
      try {
        await openSessionByTitle(page, archTitle, { agentId: 'architect' });
      } catch (err) {
        const active = await page.evaluate(() => localStorage.getItem('autoreiv_active_session_id'));
        if (active !== sid) throw err;
        await page.locator('#toggleSidebarBtn').click();
      }
    }, { timeoutMs: 60000 });

    await j.step('Review CARD-3: Architect returns it with notes naming the README (no approval click)', async () => {
      const from = (await rowsOf(request, base, sid)).length;
      const returned = toolRow('finish_review', /^=== Review Returned: CARD-3/, from);
      const anyVerdict = toolRow('finish_review', /^=== Review (Returned|Done)/, from);
      const r = await ask(page, streams,
        'Review CARD-3 against its acceptance criteria and record your verdict. Do not hand it back to Developer yet.',
        async () => (await anyVerdict()), 1500000, { approve: false });
      const rows = await rowsOf(request, base, sid);
      const text = cardText();
      const review = (text.split(/^## Review\s*$/m)[1] || '').split(/^## /m)[0];
      j.note(`approval cards clicked ${r.approvals}; tool order: ${toolOrder(rows, from)}; card ${statusOf(file())}`);
      j.note(`last commit: ${git(root, 'log', '-1', '--format=%s')}; round 1 review: ${review.replace(/\s+/g, ' ').slice(0, 300)}`);
      if (!(await toolRow('review_card', /^=== Review packet: CARD-3/, from)())) throw new Error('review_card did not run');
      if (!(await returned())) throw new Error('no Returned verdict (the README line is missing, so Done is wrong)');
      if (statusOf(file()) !== 'Returned') throw new Error(`card is ${statusOf(file())}`);
      if (!/^review_rounds:\s*1$/m.test(text) || !/### Round 1 - Returned/.test(text)) throw new Error('no round 1 review on the card');
      if (!/README/i.test(review)) throw new Error('review notes do not name the README');
      if (git(root, 'log', '-1', '--format=%s') !== 'docs(card): CARD-3 Returned (round 1)' || !onlyCardChanged()) throw new Error('Returned commit is not card-only');
      if (git(root, 'rev-parse', 'main') !== mainHead) throw new Error('main moved');
      await page.locator('[data-card-review="returned"]').last().scrollIntoViewIfNeeded().catch(() => {});
      await snap('returned-review');
    }, { timeoutMs: 1600000 });

    await j.step('Hand CARD-3 back: Developer adds the README line on the same branch and brings it to In Review', async () => {
      const from = (await rowsOf(request, base, sid)).length;
      const t0 = Date.now();
      const branchesBefore = git(root, 'branch', '--format=%(refname:short)').split('\n').sort().join(',');
      const outcome = toolRow('hand_off_card', /Card status: In Review/, from);
      const devCount = async () => {
        const list = await getJson(request, `${base}/api/sessions?agent_id=developer`).catch(() => []);
        const kids = (Array.isArray(list) ? list : []).filter((s) => String(s.id).startsWith(`${sid}_child_`));
        let n = (await rowsOf(request, base, sid)).length;
        for (const k of kids) n += (await rowsOf(request, base, k.id)).length;
        return n;
      };
      const r = await ask(page, streams, 'Hand CARD-3 back to Developer to address your review notes.',
        async () => statusOf(file()) === 'In Review' && (await outcome()), 2700000, { idleLimit: 150, progress: devCount });
      await waitReplyIdle(page, { timeoutMs: 300000 }).catch(() => {});
      const rows = await rowsOf(request, base, sid);
      const list = await getJson(request, `${base}/api/sessions?agent_id=developer`).catch(() => []);
      const devChat = (Array.isArray(list) ? list : []).find((s) => String(s.id).startsWith(`${sid}_child_`));
      const devRows = devChat ? await rowsOf(request, base, devChat.id) : [];
      const log = git(root, 'log', '--format=%s', 'main..HEAD').split('\n').filter(Boolean);
      let testsPass = true;
      try { execFileSync('node', ['--test'], { cwd: root, stdio: 'pipe' }); } catch { testsPass = false; }
      const branchesAfter = git(root, 'branch', '--format=%(refname:short)').split('\n').sort().join(',');
      j.note(`minutes ${((Date.now() - t0) / 60000).toFixed(1)}; approvals ${r.approvals} (${r.approved.map((a) => a.slice(0, 40)).join(' | ')})`);
      j.note(`branch ${git(root, 'branch', '--show-current')}; branches ${branchesAfter}; commits ${log.join(' | ')}; card ${statusOf(file())}; README zero ${readmeDocumentsZero(root)}; tests ${testsPass}`);
      j.note(`architect tool order: ${toolOrder(rows, from)}`);
      j.note(`developer chat ${devChat ? `${devChat.id} "${devChat.title}"` : 'not listed'}; developer tool order: ${toolOrder(devRows)}`);
      if (git(root, 'branch', '--show-current') !== BRANCH) throw new Error('Developer is not on the existing card branch');
      if (branchesAfter !== branchesBefore) throw new Error(`branches changed: ${branchesBefore} -> ${branchesAfter}`);
      if (statusOf(file()) !== 'In Review') throw new Error(`card is ${statusOf(file())}`);
      if (!readmeDocumentsZero(root)) throw new Error('README does not document the zero rule');
      if (!testsPass) throw new Error('node --test fails');
      if (log[0] !== 'docs(card): CARD-3 In Review' || !log.includes('docs(card): CARD-3 Returned (round 1)')) throw new Error('no new In Review commit after the Return');
      if (git(root, 'status', '--porcelain')) throw new Error('tree not clean');
      if (!/### Round 1 - Returned/.test(cardText())) throw new Error('round 1 review lost');
      if (git(root, 'rev-parse', 'main') !== mainHead) throw new Error('main moved');
      if (!devChat) throw new Error('Developer rework conversation not listed');
      await page.locator('[data-hand-off-outcome="outcome"]').last().scrollIntoViewIfNeeded().catch(() => {});
      await snap('rework-outcome');
      await openSessionByTitle(page, devChat.title, { agentId: 'developer' }).catch((e) => j.note(`open developer chat: ${e.message}`));
      await page.waitForTimeout(2000);
      await snap('developer-rework');
    }, { timeoutMs: 3200000 });

    await j.step('Review CARD-3 again: Architect marks it Done with a written review; nothing merged', async () => {
      await openSessionByTitle(page, archTitle, { agentId: 'architect' }).catch((e) => j.note(`reopen architect chat: ${e.message}`));
      const from = (await rowsOf(request, base, sid)).length;
      const verdict = toolRow('finish_review', /^=== Review (Returned|Done)/, from);
      const r = await ask(page, streams, 'Developer addressed your notes. Review CARD-3 again and record your verdict.',
        async () => (await verdict()), 1500000, { approve: false });
      const rows = await rowsOf(request, base, sid);
      const text = cardText();
      j.note(`approval cards clicked ${r.approvals}; tool order: ${toolOrder(rows, from)}; card ${statusOf(file())}; last commit ${git(root, 'log', '-1', '--format=%s')}`);
      if (!(await toolRow('review_card', /^=== Review packet: CARD-3 \(round 2/, from)())) throw new Error('review_card round 2 did not run');
      if (!(await toolRow('finish_review', /^=== Review Done: CARD-3/, from)())) throw new Error('no Done verdict');
      if (statusOf(file()) !== 'Done' || !/### Round 2 - Done/.test(text) || !/^completed:/m.test(text)) throw new Error('card not Done with round 2 review');
      if (git(root, 'log', '-1', '--format=%s') !== 'docs(card): CARD-3 Done' || !onlyCardChanged()) throw new Error('Done commit is not card-only');
      if (git(root, 'rev-parse', 'main') !== mainHead) throw new Error('main moved: something merged');
      if (git(root, 'remote')) throw new Error('fixture gained a remote');
      if (git(root, 'status', '--porcelain')) throw new Error('tree not clean');
      await page.locator('[data-card-review="done"]').last().scrollIntoViewIfNeeded().catch(() => {});
      await snap('done-review');
    }, { timeoutMs: 1600000 });
  },
};
