/**
 * CARD-698 journey: Comparative architecture review of Crucible and Agent-OS against AutoReiv.
 * 1) Verifies docs/architecture-comparison-crucible-agent-os.md and docs/README.md exist and include
 *    the comparative review across AutoReiv, Crucible, and Agent-OS with Adopt / Adapt / Skip recommendations.
 * 2) Selects a throwaway git fixture project containing docs/architecture-comparison-crucible-agent-os.md
 *    and docs/README.md, asks AutoReiv in Chat to read the review via read_project_file and summarize
 *    the Tier 1 Adopt items, and verifies tool execution, assistant response structure, and responsive layout.
 */
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { waitFor } from './lib/runner.mjs';
import {
  HITL_CARD,
  getJson,
  isStreaming,
  openApp,
  openSessionByTitle,
  send,
  trackStreams,
  waitReplyIdle,
} from './lib/app.mjs';

const REPO_ROOT = process.cwd();
const DOC_REL = 'docs/architecture-comparison-crucible-agent-os.md';
const README_REL = 'docs/README.md';

const git = (cwd, ...args) => execFileSync('git', ['-C', cwd, ...args], { encoding: 'utf8' }).trim();
const role = (m) => String((m && m.role) || '').toLowerCase();

function makeDocProjectFixture(tag) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), `autoreiv-card698-${tag}-`));
  fs.mkdirSync(path.join(root, 'docs', 'adr'), { recursive: true });
  fs.mkdirSync(path.join(root, '.agents', 'cards'), { recursive: true });
  fs.mkdirSync(path.join(root, '.agents', 'templates'), { recursive: true });
  fs.writeFileSync(path.join(root, '.gitignore'), 'scratch/\n');
  fs.writeFileSync(path.join(root, 'AGENTS.md'), '# AGENTS.md - docs-review\n\n## Project\nArchitecture review docs.\n');
  fs.writeFileSync(path.join(root, 'README.md'), '# docs-review\n');
  fs.writeFileSync(path.join(root, 'CHANGELOG.md'), '# Changelog\n');
  fs.writeFileSync(path.join(root, 'VERSION'), '0.1.0\n');
  fs.writeFileSync(path.join(root, '.agents', 'cards', '.gitkeep'), '');
  fs.writeFileSync(path.join(root, '.agents', 'templates', 'card.template.md'), '# Card template\n');
  fs.writeFileSync(path.join(root, '.agents', 'templates', 'adr.template.md'), '# ADR template\n');
  fs.writeFileSync(path.join(root, 'docs', 'adr', '.gitkeep'), '');
  fs.copyFileSync(path.join(REPO_ROOT, DOC_REL), path.join(root, DOC_REL));
  fs.copyFileSync(path.join(REPO_ROOT, README_REL), path.join(root, README_REL));
  git(root, 'init', '-b', 'main');
  git(root, 'config', 'user.name', 'AutoReiv QA');
  git(root, 'config', 'user.email', 'qa@autoreiv.local');
  git(root, 'add', '.');
  git(root, 'commit', '-m', 'chore: add comparative architecture review doc');
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

async function askAndWait(page, streams, text, done, timeoutMs) {
  const n = streams.count;
  await send(page, text);
  await waitFor(() => streams.count > n, { timeoutMs: 20000 });
  let idlePolls = 0;
  await waitFor(
    async () => {
      const cards = page.locator(HITL_CARD);
      const count = await cards.count();
      for (let i = 0; i < count; i += 1) {
        const approve = cards.nth(i).locator('[data-hitl-decision="APPROVED"]').first();
        if (await approve.isVisible().catch(() => false)) {
          await approve.click();
          await page.waitForTimeout(1500);
          return false;
        }
      }
      const streaming = await isStreaming(page);
      if (!streaming && (await done())) return true;
      idlePolls = streaming ? 0 : idlePolls + 1;
      return idlePolls >= 8;
    },
    { timeoutMs, intervalMs: 2000 },
  ).catch(() => {});
  await waitReplyIdle(page, { timeoutMs: 60000 }).catch(() => {});
}

export default {
  id: 'card-698-comparative-architecture-review-of-crucible-and',
  card: 'CARD-698',
  title: 'Comparative architecture review of Crucible and Agent-OS against AutoReiv is indexed and inspectable in Chat',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    let root = '';
    let sid = '';

    try {
      await j.step('Verify comparative architecture review document and docs index on disk', async () => {
        const docPath = path.join(REPO_ROOT, DOC_REL);
        const readmePath = path.join(REPO_ROOT, README_REL);
        if (!fs.existsSync(docPath)) throw new Error(`Missing ${DOC_REL}`);
        if (!fs.existsSync(readmePath)) throw new Error(`Missing ${README_REL}`);

        const docText = fs.readFileSync(docPath, 'utf8');
        const readmeText = fs.readFileSync(readmePath, 'utf8');
        if (!readmeText.includes('(architecture-comparison-crucible-agent-os.md)')) {
          throw new Error('docs/README.md must link to architecture-comparison-crucible-agent-os.md');
        }
        for (const required of ['AutoReiv', 'Crucible', 'Agent-OS', 'compaction.py', 'trace.py', 'ADR-0015', 'Adopt', 'Adapt', 'Skip']) {
          if (!docText.includes(required)) throw new Error(`Review doc missing "${required}"`);
        }
        j.note(`verified ${DOC_REL} (${docText.split('\n').length} lines) and link in ${README_REL}`);
      }, { timeoutMs: 15000 });

      await j.step('Select fixture project containing comparative review doc and open AutoReiv chat session', async () => {
        root = makeDocProjectFixture(viewport.name);
        const res = await request.put(`${base}/api/projects/selected`, { data: { slug: 'docs-review', path: root } });
        if (!res.ok()) throw new Error(`select project -> ${res.status()}`);

        const title = `QA 698 review ${viewport.name} ${Date.now() % 100000}`;
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
        j.note(`selected project ${root}; session ${sid}`);
      }, { timeoutMs: 60000 });

      await j.step('AutoReiv mounts software-development, reads docs/architecture-comparison-crucible-agent-os.md, and summarizes Tier 1 Adopt items', async () => {
        const prompt = [
          'In the active project, do these steps directly in this turn (do not delegate):',
          '1) Call skill_view(skill_id="software-development") to mount read_project_file.',
          '2) Call read_project_file(path="docs/architecture-comparison-crucible-agent-os.md").',
          '3) Reply with a concise summary naming the 3 Tier 1 (Adopt) recommendations from Crucible and Agent-OS.',
        ].join('\n');

        await askAndWait(
          page,
          streams,
          prompt,
          async () => {
            const rows = await allRows(request, base, sid);
            const tools = rows.filter((m) => role(m) === 'tool').map((m) => String(m.name || ''));
            const assistantText = rows
              .filter((m) => role(m) === 'assistant')
              .map((m) => String(m.content || ''))
              .join('\n');
            return (
              tools.includes('read_project_file') &&
              /Crucible|Agent-OS/i.test(assistantText) &&
              /compaction|trace|ApprovalMode/i.test(assistantText)
            );
          },
          240000,
        );

        const rows = await allRows(request, base, sid);
        const tools = rows.filter((m) => role(m) === 'tool').map((m) => String(m.name || ''));
        const assistantText = rows
          .filter((m) => role(m) === 'assistant')
          .map((m) => String(m.content || ''))
          .join('\n');

        j.note(`tools called: ${[...new Set(tools)].join(', ')}`);
        if (!tools.includes('read_project_file')) {
          throw new Error(`Expected read_project_file to be called; got tools: ${tools.join(', ')}`);
        }
        if (!/Crucible|Agent-OS/i.test(assistantText)) {
          throw new Error(`Expected Crucible or Agent-OS in assistant summary, got: ${assistantText.slice(0, 240)}`);
        }
        if (!/compaction|trace|ApprovalMode/i.test(assistantText)) {
          throw new Error(`Expected Tier 1 recommendation keywords in summary, got: ${assistantText.slice(0, 240)}`);
        }

        const overflow = await page.evaluate(() => {
          const doc = document.documentElement;
          return doc.scrollWidth - doc.clientWidth;
        });
        if (overflow > 2) {
          throw new Error(`Expected no horizontal overflow on ${viewport.name}, got ${overflow}px`);
        }
      }, { timeoutMs: 260000 });
    } finally {
      if (root) {
        try {
          fs.rmSync(root, { recursive: true, force: true });
        } catch {
          // ignore cleanup errors
        }
      }
    }
  },
};
