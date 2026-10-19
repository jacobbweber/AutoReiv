/**
 * CARD-730 journey: AutoReiv clones, pulls and pushes through its git tools, each after an approval.
 * Fixture: a bare origin repo inside the user-data projects folder (local clone sources must live there).
 * 1) git_clone puts the repo in the projects folder and makes it the active project (Projects Studio shows it).
 * 2) After a new commit in origin, git_pull fast-forwards the local main.
 * 3) git_push sends a work branch to origin.
 * 4) On main, git_push is refused and origin main is unchanged.
 */
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { clickExpect, waitFor } from './lib/runner.mjs';
import { askAndApprove, getJson, openApp, openSessionByTitle, trackStreams } from './lib/app.mjs';

const git = (cwd, ...args) =>
  execFileSync('git', ['-C', cwd, '-c', 'user.name=QA', '-c', 'user.email=qa@local', ...args], { encoding: 'utf8' }).trim();
const role = (m) => String((m && m.role) || '').toLowerCase();

function commitFile(repo, name, text, subject) {
  fs.writeFileSync(path.join(repo, name), text);
  git(repo, 'add', name);
  git(repo, 'commit', '-m', subject);
}

async function toolRows(request, base, sid, name) {
  const rows = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sid)}/messages`).catch(() => []);
  return (Array.isArray(rows) ? rows : []).filter((m) => role(m) === 'tool' && String(m.name || '') === name);
}

export default {
  id: 'card-730-git-remote-tools',
  card: 'CARD-730',
  title: 'AutoReiv clones, pulls and pushes with approval; push to main is refused',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    const tag = String(viewport.name).replace(/[^a-z0-9]/gi, '').toLowerCase();
    const slug = `card730-${tag}`;
    let projectsRoot = '';
    let origin = '';
    let seed = '';
    let target = '';
    let sid = '';

    try {
      await j.step('Bare origin repo in the projects folder and an AutoReiv chat', async () => {
        const listed = await getJson(request, `${base}/api/projects`);
        projectsRoot = String(listed.projects_root || '');
        if (!projectsRoot) throw new Error('GET /api/projects returned no projects_root');
        origin = path.join(projectsRoot, `${slug}-origin.git`);
        target = path.join(projectsRoot, slug);
        for (const dir of [origin, target]) fs.rmSync(dir, { recursive: true, force: true });
        fs.mkdirSync(origin, { recursive: true });
        git(origin, 'init', '--bare', '-b', 'main');
        seed = fs.mkdtempSync(path.join(os.tmpdir(), `autoreiv-card730-${tag}-`));
        git(seed, 'init', '-b', 'main');
        commitFile(seed, 'README.md', '# card730\n', 'chore: seed');
        git(seed, 'remote', 'add', 'origin', origin);
        git(seed, 'push', 'origin', 'main');
        const title = `QA 730 git ${viewport.name} ${Date.now() % 100000}`;
        const made = await request.post(`${base}/api/sessions`, { data: { agent_id: 'autoreiv', title } });
        if (!made.ok()) throw new Error(`create session -> ${made.status()}`);
        sid = (await made.json()).id;
        await openApp(page, base);
        await openSessionByTitle(page, title, { agentId: 'autoreiv' });
      }, { timeoutMs: 60000 });

      await j.step('git_clone after approval lands in the projects folder and becomes the active project', async () => {
        const prompt = [
          'Do exactly these tool calls in order:',
          '1) skill_view(skill_id="repo-onboarding")',
          `2) git_clone(url="${origin}", slug="${slug}")`,
          'Then say in one line whether it worked.',
        ].join('\n');
        const approvals = await askAndApprove(page, streams, prompt, async () => fs.existsSync(path.join(target, '.git')), 300000);
        const rows = await toolRows(request, base, sid, 'git_clone');
        j.note(`approvals=${approvals}; git_clone rows=${rows.length}`);
        if (!rows.length) throw new Error('git_clone was not called');
        if (approvals < 1) throw new Error('git_clone ran without an approval card');
        if (!fs.existsSync(path.join(target, 'README.md'))) throw new Error(`${target} was not cloned`);
        const sel = (await getJson(request, `${base}/api/projects/selected`)).selected || {};
        if (sel.slug !== slug) throw new Error(`active project is ${sel.slug}, expected ${slug}`);
        if (/extraheader|x-access-token/i.test(fs.readFileSync(path.join(target, '.git', 'config'), 'utf8'))) {
          throw new Error('auth header written to .git/config');
        }
        await clickExpect(page.locator('#dock-projects'), async () =>
          (await page.locator('#projectsActiveName').innerText().catch(() => '')).includes(slug), {
          label: 'Projects Studio shows the cloned project as active', timeoutMs: 20000,
        });
        await clickExpect(page.locator('#dock-chat'), () => page.locator('#promptInput').isVisible(), {
          label: 'Back to Chat', timeoutMs: 15000,
        });
      }, { timeoutMs: 360000 });

      await j.step('git_pull after approval fast-forwards main to the new origin commit', async () => {
        commitFile(seed, 'NEW.md', 'new\n', 'feat: new upstream file');
        git(seed, 'push', 'origin', 'main');
        const want = git(origin, 'rev-parse', 'main');
        const prompt = 'Do exactly these tool calls in order:\n1) skill_view(skill_id="software-development")\n2) git_pull()\nThen say in one line whether it worked.';
        const approvals = await askAndApprove(page, streams, prompt, async () => git(target, 'rev-parse', 'HEAD') === want, 300000);
        j.note(`approvals=${approvals}`);
        if (git(target, 'rev-parse', 'HEAD') !== want) throw new Error('local main did not reach origin main');
        if (git(target, 'rev-list', '--merges', 'HEAD')) throw new Error('git_pull made a merge commit');
      }, { timeoutMs: 360000 });

      await j.step('git_push after approval sends the work branch to origin', async () => {
        git(target, 'switch', '-c', 'feat/card730-change');
        commitFile(target, 'CHANGE.md', 'change\n', 'feat: local change');
        const head = git(target, 'rev-parse', 'HEAD');
        const onOrigin = () => { try { return git(origin, 'rev-parse', 'feat/card730-change'); } catch { return ''; } };
        const approvals = await askAndApprove(page, streams, 'Call git_push() once, then say in one line whether it worked.', async () => onOrigin() === head, 300000);
        j.note(`approvals=${approvals}`);
        if (onOrigin() !== head) throw new Error('origin does not have feat/card730-change at the local HEAD');
      }, { timeoutMs: 360000 });

      await j.step('git_push on main is refused and origin main is unchanged', async () => {
        git(target, 'switch', 'main');
        commitFile(target, 'MAIN.md', 'main\n', 'feat: local main change');
        const before = git(origin, 'rev-parse', 'main');
        const seen = (await toolRows(request, base, sid, 'git_push')).length;
        await askAndApprove(page, streams, 'Call git_push() once and report the result in one line. Do not call any other tool.',
          async () => (await toolRows(request, base, sid, 'git_push')).length > seen, 300000);
        const rows = await toolRows(request, base, sid, 'git_push');
        const last = String((rows[rows.length - 1] || {}).content || '');
        j.note(`git_push rows=${rows.length}; last=${last.slice(0, 160)}`);
        if (rows.length <= seen) throw new Error('git_push was not called on main');
        if (!/Refusing to push 'main'/.test(last)) throw new Error('git_push on main was not refused');
        if (git(origin, 'rev-parse', 'main') !== before) throw new Error('origin main changed');
        await waitFor(async () => !(await page.locator('#promptInput').isDisabled().catch(() => false)), { timeoutMs: 30000 });
      }, { timeoutMs: 360000 });
    } finally {
      await request.put(`${base}/api/projects/selected`, { data: {} }).catch(() => {});
      for (const dir of [target, origin, seed]) if (dir) fs.rmSync(dir, { recursive: true, force: true });
    }
  },
};
