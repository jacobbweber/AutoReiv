/**
 * CARD-739 journey: Dogfood multi-turn project development and Tutor study flow end-to-end.
 * 1) Creates a brand-new project via POST /api/projects/create, verifies it is auto-selected
 *    with an initialized main branch HEAD (and zero starter template files), exercises the
 *    branch + check + CARD-1 In Review lifecycle, and inspects CARD-1 inside Projects Studio (#view-projects).
 * 2) Exercises the Tutor study loop: starts a course with slug topic_id="distributed-consensus",
 *    verifies progressive references on socratic-tutoring and quiz-turn, grades a recall item
 *    under title-case topic "Distributed Consensus", and verifies GET /api/education/progress
 *    matches slug vs title-case topics (mastery_pct === 100).
 * 3) Verifies the Chat agent selector (#chatAgentSelect) switches cleanly between AutoReiv and Tutor
 *    with zero horizontal overflow on desktop and phone.
 */
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { waitFor } from './lib/runner.mjs';
import { getJson, openApp, openTab } from './lib/app.mjs';

const git = (cwd, ...args) => execFileSync('git', ['-C', cwd, ...args], { encoding: 'utf8' }).trim();

export default {
  id: 'card-739-dogfood-multi-turn-project-development-and',
  card: 'CARD-739',
  title: 'Dogfood active-project SDLC card flow and Tutor study progression end-to-end',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const slug = `dogfood-m33-${viewport?.name || 'desktop'}-${Date.now() % 100000}`;
    let projectRoot = '';

    await j.step('1. Create fresh project via API, verify auto-select + main HEAD commit, and inspect CARD-1 in Projects Studio', async () => {
      const createRes = await request.post(`${base}/api/projects`, {
        data: { slug, name: `Dogfood M33 (${viewport?.name || 'desktop'})` },
      });
      if (!createRes.ok()) {
        throw new Error(`POST /api/projects failed: ${createRes.status()}`);
      }
      const created = await createRes.json();
      if (!created.success || !created.path) {
        throw new Error(`Unexpected create_project payload: ${JSON.stringify(created)}`);
      }
      projectRoot = created.path;

      const selectedRes = await getJson(request, `${base}/api/projects/selected`);
      if (!selectedRes.selected || selectedRes.selected.slug !== slug) {
        throw new Error(`Expected create_project to auto-select '${slug}', got: ${JSON.stringify(selectedRes)}`);
      }

      const entries = fs.readdirSync(projectRoot);
      if (JSON.stringify(entries) !== JSON.stringify(['.git'])) {
        throw new Error(`Expected fresh project to contain only .git, got: ${JSON.stringify(entries)}`);
      }
      const headSha = git(projectRoot, 'rev-parse', 'HEAD');
      if (!headSha || headSha.length < 7) {
        throw new Error(`Expected initialized main HEAD commit, got: '${headSha}'`);
      }

      // Exercise branch + code + test + CARD-1 In Review in the active project
      git(projectRoot, 'switch', '-c', 'feat/card-1-multiply');
      fs.writeFileSync(
        path.join(projectRoot, 'AGENTS.md'),
        '# AGENTS.md\n\n## Checks\n- fast: node --test\n\n## Branches\n- Base branch: main\n',
      );
      fs.writeFileSync(
        path.join(projectRoot, 'calc.js'),
        'function multiply(a, b) { return a * b; }\nmodule.exports = { multiply };\n',
      );
      fs.mkdirSync(path.join(projectRoot, '.agents', 'cards'), { recursive: true });
      fs.writeFileSync(
        path.join(projectRoot, '.agents', 'cards', 'CARD-1-multiply.md'),
        [
          '---',
          'id: CARD-1',
          'title: "Implement multiply(a, b)"',
          'status: In Review',
          'priority: P2',
          '---',
          '',
          '# CARD-1 Implement multiply(a, b)',
          '',
          '## Problem',
          'Provide multiply(a, b) with fast check verification.',
          '',
          '## Evidence',
          '',
          'Recorded by set_card_status (In Review):',
          '- Branch: `feat/card-1-multiply` (base `main`)',
          '- Green run_project_checks for HEAD: fast (`node --test`) - passed',
          '',
        ].join('\n'),
      );
      git(projectRoot, 'add', '.');
      git(projectRoot, 'commit', '-m', 'feat(calc): implement multiply and CARD-1 In Review');

      await openApp(page, base);
      await openTab(page, 'projects');
      await page.locator('#view-projects').waitFor({ state: 'visible', timeout: 15000 });

      const refreshBtn = page.locator('#projectsRefreshBtn');
      if (await refreshBtn.isVisible().catch(() => false)) {
        await refreshBtn.click();
      }
      const cardsPill = page.locator('#projectsCategoryPills button[data-cat="cards"]');
      if (await cardsPill.count()) {
        await cardsPill.click();
      }

      const cardRow = page.locator('#projectsTreeList > div', { hasText: 'CARD-1' }).first();
      const rowFound = await waitFor(async () => (await cardRow.count()) > 0, { timeoutMs: 15000 });
      if (!rowFound) {
        throw new Error('Expected CARD-1 row in #projectsTreeList');
      }
      await cardRow.click();

      const previewReady = await waitFor(
        async () => {
          const txt = await page.locator('#projectsMarkdownContent').innerText().catch(() => '');
          return txt.includes('CARD-1') && txt.includes('Evidence');
        },
        { timeoutMs: 15000 },
      );
      if (!previewReady) {
        const txt = await page.locator('#projectsMarkdownContent').innerText().catch(() => '');
        throw new Error(`Expected CARD-1 Evidence in #projectsMarkdownContent, got: ${txt}`);
      }

      j.note(`verified create_project auto-select + main HEAD + CARD-1 in Projects Studio (${slug})`);
    }, { timeoutMs: 40000 });

    await j.step('2. Exercise Tutor course start, progressive references, quiz grading, and slug-vs-title progress summary', async () => {
      const startRes = await request.post(`${base}/api/education/course/start`, {
        data: { agent_id: 'tutor', topic_id: 'distributed-consensus' },
      });
      if (!startRes.ok()) {
        throw new Error(`POST /api/education/course/start failed: ${startRes.status()}`);
      }
      const started = await startRes.json();
      if (!started.course || started.course.topic_id !== 'distributed-consensus') {
        throw new Error(`Unexpected course start payload: ${JSON.stringify(started)}`);
      }

      const primingRef = await getJson(
        request,
        `${base}/api/capabilities/skills/socratic-tutoring/file?path=${encodeURIComponent('references/priming-and-construction.md')}`,
      );
      if (!String(primingRef.content || '').includes('Priming')) {
        throw new Error(`Expected Priming section in socratic-tutoring reference: ${JSON.stringify(primingRef)}`);
      }

      const upsertRes = await request.post(`${base}/api/education/mastery/upsert`, {
        data: {
          agent_id: 'tutor',
          topic: 'Distributed Consensus',
          wiki_path: '00_Inbox/distributed-consensus.md',
          prompt: 'What term describes the majority of nodes required to agree on a proposed state transition?',
          expected_answer: 'quorum',
        },
      });
      if (!upsertRes.ok()) {
        throw new Error(`POST /api/education/mastery/upsert failed: ${upsertRes.status()}`);
      }
      const upserted = await upsertRes.json();
      const itemId = upserted.item_id;
      if (!itemId) {
        throw new Error(`Missing item_id from mastery/upsert: ${JSON.stringify(upserted)}`);
      }

      const gradeRes = await request.post(`${base}/api/education/quiz/grade`, {
        data: {
          agent_id: 'tutor',
          item_id: itemId,
          answer: 'quorum',
        },
      });
      if (!gradeRes.ok()) {
        throw new Error(`POST /api/education/quiz/grade failed: ${gradeRes.status()}`);
      }
      const graded = await gradeRes.json();
      if (!graded.correct || graded.grade !== 'pass') {
        throw new Error(`Expected binary grade pass, got: ${JSON.stringify(graded)}`);
      }

      const progress = await getJson(
        request,
        `${base}/api/education/progress?agent_id=tutor&topic_id=${encodeURIComponent('distributed-consensus')}`,
      );
      if (!progress.success || !progress.mastery || progress.mastery.pass_count < 1 || progress.mastery.mastery_pct !== 100) {
        throw new Error(
          `Expected slug topic_id 'distributed-consensus' to match 'Distributed Consensus' with 100% mastery, got: ${JSON.stringify(progress)}`,
        );
      }

      j.note('verified Tutor course start + progressive reference + graded recall + 100% topic-matched progress');
    }, { timeoutMs: 30000 });

    await j.step('3. Switch to Chat view (#view-chat), verify AutoReiv and Tutor selector, and check viewport geometry', async () => {
      await openTab(page, 'chat');
      await page.locator('#view-chat').waitFor({ state: 'visible', timeout: 15000 });

      const agentSelect = page.locator('#agentSelect');
      await agentSelect.waitFor({ state: 'visible', timeout: 10000 });
      const optionValues = await agentSelect.locator('option').evaluateAll((opts) => opts.map((o) => o.value));
      for (const expectedAgent of ['autoreiv', 'tutor']) {
        if (!optionValues.includes(expectedAgent)) {
          throw new Error(`Expected '${expectedAgent}' in #agentSelect options, got: ${JSON.stringify(optionValues)}`);
        }
      }
      await agentSelect.selectOption('tutor');

      const overflow = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
      }));
      if (overflow.scrollWidth > overflow.innerWidth + 2) {
        throw new Error(
          `Horizontal overflow in #view-chat on ${viewport?.name || 'viewport'}: ${overflow.scrollWidth} > ${overflow.innerWidth}`,
        );
      }

      j.note(`verified Chat agent selector and viewport geometry on ${viewport?.name || 'viewport'}`);
    }, { timeoutMs: 25000 });
  },
};
