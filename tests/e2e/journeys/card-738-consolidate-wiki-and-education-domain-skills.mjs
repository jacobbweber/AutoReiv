/**
 * CARD-738 journey: Consolidate Wiki and Education domain skills with progressive references.
 * 1) Verifies GET /api/capabilities/tree retires the 6 duplicate/empty folders (education-priming,
 *    education-dual-coding, education-construction, diagnostics, wiki, wiki-templates), folds
 *    wiki_template_create and wiki_template_update into on-demand wiki-curation, and exposes
 *    progressive references/*.md across socratic-tutoring, wiki-curation, wiki_tasks, quiz-turn,
 *    flashcard-turn, due-review, and education-wiki-curation.
 * 2) Verifies GET /api/capabilities/skills/<id>/file serves the new reference markdown files.
 * 3) Opens Capabilities Studio (#view-capabilities) in the browser and verifies the Agora skill
 *    tree lists wiki-curation and quiz-turn with their progressive reference nodes and zero
 *    horizontal overflow on desktop and phone viewports.
 */
import { waitFor } from './lib/runner.mjs';
import { getJson, openApp, openTab } from './lib/app.mjs';

export default {
  id: 'card-738-consolidate-wiki-and-education-domain-skills',
  card: 'CARD-738',
  title: 'Consolidated Wiki and Education Agora skills with progressive references',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    await j.step('1. Verify /api/capabilities/tree retired skill folders, wiki-curation template bindings, and progressive references', async () => {
      const tree = await getJson(request, `${base}/api/capabilities/tree`);
      const skills = Array.isArray(tree.skills) ? tree.skills : [];
      const byId = Object.fromEntries(skills.map((s) => [s.id, s]));

      const retiredIds = [
        'education-priming',
        'education-dual-coding',
        'education-construction',
        'diagnostics',
        'wiki',
        'wiki-templates',
      ];
      for (const retiredId of retiredIds) {
        if (byId[retiredId]) {
          throw new Error(`Retired skill folder '${retiredId}' still present in /api/capabilities/tree`);
        }
      }

      const expectedRefs = {
        'socratic-tutoring': ['learning-modes.md', 'priming-and-construction.md'],
        'wiki-curation': ['templates-guide.md'],
        wiki_tasks: ['weekly-rollover.md'],
        'quiz-turn': ['grading-rubric.md'],
        'flashcard-turn': ['srs-loop.md'],
        'due-review': ['retention-schedule.md'],
        'education-wiki-curation': ['library-templates.md'],
      };

      for (const [skillId, refNames] of Object.entries(expectedRefs)) {
        const entry = byId[skillId];
        if (!entry) {
          throw new Error(`Expected skill '${skillId}' in /api/capabilities/tree`);
        }
        const gotRefs = (entry.references || []).map((r) => r.name);
        for (const reqRef of refNames) {
          if (!gotRefs.includes(reqRef)) {
            throw new Error(`Expected reference '${reqRef}' on skill '${skillId}', got: ${JSON.stringify(gotRefs)}`);
          }
        }
      }

      const curationTools = new Set((byId['wiki-curation'] || {}).declared_tools || []);
      for (const templateTool of ['wiki_template_list', 'wiki_template_read', 'wiki_template_create', 'wiki_template_update']) {
        if (!curationTools.has(templateTool)) {
          throw new Error(`Expected '${templateTool}' declared on consolidated wiki-curation skill`);
        }
      }

      const templatesRef = await getJson(
        request,
        `${base}/api/capabilities/skills/wiki-curation/file?path=${encodeURIComponent('references/templates-guide.md')}`,
      );
      if (!String(templatesRef.content || '').includes('wiki_template_create')) {
        throw new Error(`Unexpected templates-guide.md content: ${JSON.stringify(templatesRef)}`);
      }

      const quizRef = await getJson(
        request,
        `${base}/api/capabilities/skills/quiz-turn/file?path=${encodeURIComponent('references/grading-rubric.md')}`,
      );
      if (!String(quizRef.content || '').includes('education_quiz_grade')) {
        throw new Error(`Unexpected grading-rubric.md content: ${JSON.stringify(quizRef)}`);
      }

      j.note('verified /api/capabilities/tree consolidated Wiki and Education references');
    }, { timeoutMs: 25000 });

    await j.step('2. Open Capabilities Studio (#view-capabilities) and inspect Wiki and Education progressive reference nodes', async () => {
      await openApp(page, base);
      await openTab(page, 'capabilities');
      await page.locator('#view-capabilities').waitFor({ state: 'visible', timeout: 15000 });

      const treeReady = await waitFor(
        async () => {
          const txt = await page.locator('#capabilitiesTreeList').innerText().catch(() => '');
          return (
            txt.includes('wiki-curation') &&
            txt.includes('quiz-turn') &&
            !txt.includes('education-priming') &&
            !txt.includes('wiki-templates')
          );
        },
        { timeoutMs: 15000 },
      );
      if (!treeReady) {
        const txt = await page.locator('#capabilitiesTreeList').innerText().catch(() => '');
        throw new Error(`Expected #capabilitiesTreeList to show wiki-curation and quiz-turn without retired skills; got: ${txt}`);
      }

      const search = page.locator('#capabilitiesTreeSearch');
      await search.waitFor({ state: 'visible', timeout: 10000 });
      await search.fill('wiki-curation');
      await search.dispatchEvent('input');

      const refBtn = page.locator(
        '#capabilitiesTreeList [data-skill-id="wiki-curation"][data-skill-file="references/templates-guide.md"]',
      );
      await refBtn.waitFor({ state: 'visible', timeout: 10000 });
      await refBtn.scrollIntoViewIfNeeded();
      await refBtn.click();

      const refLoaded = await waitFor(
        async () =>
          (await page.locator('#capabilitiesFileEditor').inputValue().catch(() => '')).includes('wiki_template_create'),
        { timeoutMs: 10000 },
      );
      if (!refLoaded) {
        const val = await page.locator('#capabilitiesFileEditor').inputValue().catch(() => '');
        throw new Error(`Expected references/templates-guide.md to load into #capabilitiesFileEditor, got: ${val}`);
      }

      const overflow = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
      }));
      if (overflow.scrollWidth > overflow.innerWidth + 2) {
        throw new Error(
          `Horizontal overflow in #view-capabilities on ${viewport?.name || 'viewport'}: ${overflow.scrollWidth} > ${overflow.innerWidth}`,
        );
      }

      j.note(`verified Capabilities Studio Wiki/Education references on ${viewport?.name || 'viewport'}`);
    }, { timeoutMs: 35000 });
  },
};
