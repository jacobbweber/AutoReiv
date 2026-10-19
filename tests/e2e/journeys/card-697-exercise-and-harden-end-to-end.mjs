/**
 * CARD-697 journey: Exercise and harden end-to-end self-development on AutoReiv.
 * 1) AutoReiv's allowed_tools include create_project (repo-onboarding), the project-cards tools
 *    and software-development tools (patch_project_file, git_create_branch, git_commit, run_project_checks).
 * 2) A throwaway git project in the user-data projects folder (CARD-728) with a failing node --test check
 *    and Ready card CARD-1 is selected as the active project.
 * 3) In Chat, AutoReiv opens project-cards and software-development via skill_view,
 *    creates the card branch, fixes calc.js, commits, runs run_project_checks green, and transitions
 *    CARD-1 to In Review with tool-written ## Evidence.
 * 4) In Projects Studio (#view-projects), there is no drift banner (CARD-729) and opening CARD-1 shows In Review.
 */
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { waitFor } from './lib/runner.mjs';
import {
  askAndApprove,
  freshProjectDir,
  getJson,
  openApp,
  openSessionByTitle,
  trackStreams,
} from './lib/app.mjs';

const REQUIRED_TOOLS = [
  'create_project',
  'list_cards',
  'read_card',
  'write_card',
  'set_card_status',
  'review_card',
  'finish_review',
  'read_project_file',
  'patch_project_file',
  'git_create_branch',
  'git_commit',
  'run_project_checks',
];

const AGENTS_MD = `# AGENTS.md - calc

## Project
A tiny JavaScript calculator library used by the CARD-697 live QA journey.

## Run
node -e "console.log(require('./calc.js').add(2, 3))"

## Checks
- fast: node --test

## Branches
- Base branch: main
- One branch per card: \`feat/card-<n>-<short-slug>\`
- Agents never push or merge. A person does.

## Cards
- Folder: \`.agents/cards/\`
- Status: Proposed -> Ready -> In Progress -> In Review -> Done

## Rules
- Don't add a dependency without asking.

## Don't touch
- none
`;

const CALC = `function add(a, b) {\n  return a - b;\n}\n\nmodule.exports = { add };\n`;
const TEST = `const test = require('node:test');\nconst assert = require('node:assert');\nconst { add } = require('./calc.js');\n\ntest('add sums two numbers', () => {\n  assert.strictEqual(add(2, 3), 5);\n});\n`;
const CARD = `---\nid: CARD-1\ntitle: "add() returns the sum"\nstatus: Ready\npriority: P2\n---\n\n# CARD-1 add() returns the sum\n\n## Why\nadd(2, 3) returns -1 instead of 5 in calc.js.\n\n## Acceptance criteria\n- [ ] add(2, 3) returns 5.\n- [ ] fast check (node --test) passes.\n`;

const git = (cwd, ...args) => execFileSync('git', ['-C', cwd, ...args], { encoding: 'utf8' }).trim();
const role = (m) => String((m && m.role) || '').toLowerCase();
const statusOf = (file) => ((fs.readFileSync(file, 'utf8').match(/^status:\s*(.+)$/m) || [])[1] || '').trim();

function makeFixture(root) {
  fs.mkdirSync(path.join(root, '.agents', 'cards'), { recursive: true });
  fs.mkdirSync(path.join(root, '.agents', 'templates'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs', 'adr'), { recursive: true });
  fs.writeFileSync(path.join(root, '.gitignore'), 'node_modules/\nscratch/\n');
  fs.writeFileSync(path.join(root, 'AGENTS.md'), AGENTS_MD);
  fs.writeFileSync(path.join(root, 'README.md'), '# calc\n');
  fs.writeFileSync(path.join(root, 'VERSION'), '0.1.0\n');
  fs.writeFileSync(path.join(root, '.agents', 'cards', '.gitkeep'), '');
  fs.writeFileSync(path.join(root, '.agents', 'templates', 'card.template.md'), '# Card template\n');
  fs.writeFileSync(path.join(root, '.agents', 'templates', 'adr.template.md'), '# ADR template\n');
  fs.writeFileSync(path.join(root, 'docs', 'adr', '.gitkeep'), '');
  fs.writeFileSync(path.join(root, 'CHANGELOG.md'), '# Changelog\n');
  fs.writeFileSync(path.join(root, 'calc.js'), CALC);
  fs.writeFileSync(path.join(root, 'calc.test.js'), TEST);
  fs.writeFileSync(path.join(root, '.agents', 'cards', 'CARD-1-add-returns-sum.md'), CARD);
  git(root, 'init', '-b', 'main');
  git(root, 'config', 'user.name', 'AutoReiv QA');
  git(root, 'config', 'user.email', 'qa@autoreiv.local');
  git(root, 'add', '.');
  git(root, 'commit', '-m', 'chore: initial fixture');
  return root;
}

async function allRows(request, base, sid) {
  const listed = await getJson(request, `${base}/api/sessions`).catch(() => []);
  const ids = new Set([
    sid,
    ...(Array.isArray(listed) ? listed : [])
      .map((x) => String(x.id))
      .filter((x) => x.startsWith(`${sid}::`)),
  ]);
  const out = [];
  for (const id of ids) {
    const rows = await getJson(request, `${base}/api/sessions/${encodeURIComponent(id)}/messages`).catch(() => []);
    if (Array.isArray(rows)) out.push(...rows);
  }
  return out;
}


export default {
  id: 'card-697-exercise-and-harden-end-to-end',
  card: 'CARD-697',
  title: 'AutoReiv exercises project-cards and software-development end-to-end to In Review',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    let root = '';
    let sid = '';
    const cardFile = () => path.join(root, '.agents', 'cards', 'CARD-1-add-returns-sum.md');

    await j.step('AutoReiv exposes repo-onboarding, project-cards and software-development tools', async () => {
      const ar = await getJson(request, `${base}/api/agents/autoreiv`);
      const names = new Set(
        (ar.allowed_tools || []).map((t) => String(typeof t === 'string' ? t : (t && t.name) || '')),
      );
      const missing = REQUIRED_TOOLS.filter((t) => !names.has(t));
      j.note(`autoreiv skills: ${(ar.allowed_skill || []).join(', ')}; missing tools: ${missing.join(', ') || 'none'}`);
      if (missing.length) throw new Error(`AutoReiv missing tools: ${missing.join(', ')}`);
    }, { timeoutMs: 30000 });

    await j.step('Select throwaway git fixture project and open AutoReiv chat session', async () => {
      const slug = `card697-${viewport.name}`;
      root = makeFixture(await freshProjectDir(request, base, slug));
      const res = await request.put(`${base}/api/projects/selected`, { data: { slug, path: root } });
      if (!res.ok()) throw new Error(`select project -> ${res.status()}`);
      j.note(`fixture ${root}`);

      const title = `QA 697 autoreiv ${viewport.name} ${Date.now() % 100000}`;
      const made = await request.post(`${base}/api/sessions`, { data: { agent_id: 'autoreiv', title } });
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
    }, { timeoutMs: 60000 });

    await j.step('AutoReiv mounts project-cards + software-development, fixes calc.js, runs checks, and moves CARD-1 to In Review', async () => {
      const prompt = [
        'In the active project, do these steps in order using your tools:',
        '1) Call skill_view(skill_id="project-cards") and skill_view(skill_id="software-development") to mount your project and development tools.',
        '2) Call git_create_branch(name="feat/card-1-add-returns-sum").',
        '3) Call patch_project_file(path="calc.js", old_text="return a - b;", new_text="return a + b;").',
        '4) Call git_commit(subject="feat(calc): return sum in add", paths=["calc.js"]).',
        '5) Call run_project_checks() and verify passed=true.',
        '6) Call set_card_status(card_id="CARD-1", status="In Review") and summarize the result.',
      ].join('\n');

      const approvals = await askAndApprove(
        page,
        streams,
        prompt,
        async () => statusOf(cardFile()) === 'In Review',
        900000,
      );

      if (statusOf(cardFile()) !== 'In Review') {
        await askAndApprove(
          page,
          streams,
          'Finish the remaining steps now: ensure calc.js is committed on branch feat/card-1-add-returns-sum with git_commit, run run_project_checks(), and call set_card_status(card_id="CARD-1", status="In Review").',
          async () => statusOf(cardFile()) === 'In Review',
          600000,
        );
      }

      const branch = git(root, 'branch', '--show-current');
      const status = statusOf(cardFile());
      const cardText = fs.readFileSync(cardFile(), 'utf8');
      const calcText = fs.readFileSync(path.join(root, 'calc.js'), 'utf8');
      const rows = await allRows(request, base, sid);
      const tools = rows.filter((m) => role(m) === 'tool').map((m) => String(m.name || ''));
      j.note(
        `approvals=${approvals}; branch=${branch}; status=${status}; tools=${[...new Set(tools)].join(', ')}`,
      );
      if (!tools.includes('skill_view')) throw new Error('skill_view was not called');
      if (branch === 'main' || !branch) throw new Error(`Expected card branch, got ${branch}`);
      if (!/return a \+ b/.test(calcText)) throw new Error('calc.js was not patched to return a + b');
      if (status !== 'In Review') throw new Error(`Expected CARD-1 status In Review, got ${status}`);
      if (!cardText.includes('## Evidence')) throw new Error('CARD-1 is missing tool-written ## Evidence');
    }, { timeoutMs: 1560000 });

    await j.step('Projects Studio has no drift banner and shows In Review card content', async () => {
      if (!(await page.locator('#view-projects').isVisible().catch(() => false))) {
        await page.locator('#dock-projects').click();
      }
      await page.locator('#view-projects').waitFor({ state: 'visible', timeout: 20000 });
      const refreshBtn = page.locator('#projectsRefreshBtn');
      if (await refreshBtn.isVisible().catch(() => false)) {
        await refreshBtn.click();
      }
      if (await page.locator('#projectsDriftBanner').count()) throw new Error('drift banner still rendered (CARD-729)');
      const cardsCatBtn = page.locator('#projectsCategoryPills button[data-cat="cards"]');
      if (await cardsCatBtn.count()) {
        await cardsCatBtn.click();
      }
      const cardRow = page.locator('#projectsTreeList > div', { hasText: 'CARD-1' }).first();
      await waitFor(async () => (await cardRow.count()) > 0, { timeoutMs: 15000 });
      await cardRow.click();
      await waitFor(
        async () => {
          const body = await page.locator('#projectsMarkdownContent').innerText().catch(() => '');
          return body.includes('CARD-1') && body.includes('Evidence');
        },
        { timeoutMs: 15000 },
      );
      j.note('Projects Studio has no drift banner; CARD-1 viewer verified In Review + Evidence');
    }, { timeoutMs: 60000 });
  },
};

