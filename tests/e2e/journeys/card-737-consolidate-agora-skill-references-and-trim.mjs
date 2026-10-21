/**
 * CARD-737 journey: Consolidate Agora skill references and trim per-turn pinned tool schemas.
 * 1) Verifies GET /api/capabilities/tree exposes progressive references/*.md for wiki-knowledge,
 *    socratic-tutoring, and proposals, retires education-application from standalone skill folders,
 *    and moves standalone native-tool registration tools (register_native_tool, view_native_tool,
 *    plan_native_folder) from capability-authoring to proposals.
 * 2) Verifies GET /api/capabilities/skills/<id>/file serves the new reference markdown files.
 * 3) Opens Capabilities Studio (#view-capabilities) in the browser and verifies the Agora skill
 *    tree lists wiki-knowledge, socratic-tutoring, and proposals with their progressive reference
 *    nodes and zero horizontal overflow on desktop and phone viewports.
 */
import { waitFor } from './lib/runner.mjs';
import { getJson, openApp, openTab } from './lib/app.mjs';

export default {
  id: 'card-737-consolidate-agora-skill-references-and-trim',
  card: 'CARD-737',
  title: 'Agora progressive references for Wiki/Tutoring/Proposals and trimmed capability-authoring schemas',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    await j.step('1. Verify /api/capabilities/tree progressive references, retired education-application, and trimmed tool schemas', async () => {
      const tree = await getJson(request, `${base}/api/capabilities/tree`);
      const skills = Array.isArray(tree.skills) ? tree.skills : [];
      const byId = Object.fromEntries(skills.map((s) => [s.id, s]));

      if (byId['education-application']) {
        throw new Error('Retired micro-skill education-application still present in /api/capabilities/tree');
      }

      const expectedRefs = {
        'wiki-knowledge': ['vault-taxonomy.md', 'curation-and-templates.md'],
        'socratic-tutoring': ['learning-modes.md'],
        proposals: ['native-tool-lane.md'],
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

      const capTools = new Set((byId['capability-authoring'] || {}).declared_tools || []);
      const propTools = new Set((byId.proposals || {}).declared_tools || []);
      for (const standaloneTool of ['register_native_tool', 'view_native_tool', 'plan_native_folder']) {
        if (capTools.has(standaloneTool)) {
          throw new Error(`Expected '${standaloneTool}' trimmed from pinned capability-authoring declared_tools`);
        }
        if (!propTools.has(standaloneTool)) {
          throw new Error(`Expected '${standaloneTool}' declared on proposals skill`);
        }
      }

      const wikiRef = await getJson(
        request,
        `${base}/api/capabilities/skills/wiki-knowledge/file?path=${encodeURIComponent('references/vault-taxonomy.md')}`,
      );
      if (!String(wikiRef.content || '').includes('00_Inbox')) {
        throw new Error(`Unexpected vault-taxonomy.md content: ${JSON.stringify(wikiRef)}`);
      }

      const tutorRef = await getJson(
        request,
        `${base}/api/capabilities/skills/socratic-tutoring/file?path=${encodeURIComponent('references/learning-modes.md')}`,
      );
      if (!String(tutorRef.content || '').includes('Application')) {
        throw new Error(`Unexpected learning-modes.md content: ${JSON.stringify(tutorRef)}`);
      }

      j.note('verified /api/capabilities/tree references and trimmed tool bindings');
    }, { timeoutMs: 25000 });

    await j.step('2. Open Capabilities Studio (#view-capabilities) and inspect progressive reference nodes in the Agora tree', async () => {
      await openApp(page, base);
      await openTab(page, 'capabilities');
      await page.locator('#view-capabilities').waitFor({ state: 'visible', timeout: 15000 });

      const treeReady = await waitFor(
        async () => {
          const txt = await page.locator('#capabilitiesTreeList').innerText().catch(() => '');
          return (
            txt.includes('wiki-knowledge') &&
            txt.includes('socratic-tutoring') &&
            txt.includes('proposals') &&
            !txt.includes('education-application')
          );
        },
        { timeoutMs: 15000 },
      );
      if (!treeReady) {
        const txt = await page.locator('#capabilitiesTreeList').innerText().catch(() => '');
        throw new Error(`Expected #capabilitiesTreeList to show wiki-knowledge, socratic-tutoring, proposals without education-application; got: ${txt}`);
      }

      const search = page.locator('#capabilitiesTreeSearch');
      await search.waitFor({ state: 'visible', timeout: 10000 });
      await search.fill('wiki-knowledge');
      await search.dispatchEvent('input');

      const refBtn = page.locator(
        '#capabilitiesTreeList [data-skill-id="wiki-knowledge"][data-skill-file="references/vault-taxonomy.md"]',
      );
      await refBtn.waitFor({ state: 'visible', timeout: 10000 });
      await refBtn.scrollIntoViewIfNeeded();
      await refBtn.click();

      const refLoaded = await waitFor(
        async () =>
          (await page.locator('#capabilitiesFileEditor').inputValue().catch(() => '')).includes('00_Inbox'),
        { timeoutMs: 10000 },
      );
      if (!refLoaded) {
        const val = await page.locator('#capabilitiesFileEditor').inputValue().catch(() => '');
        throw new Error(`Expected references/vault-taxonomy.md to load into #capabilitiesFileEditor, got: ${val}`);
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

      j.note(`verified Capabilities Studio Agora tree and references on ${viewport?.name || 'viewport'}`);
    }, { timeoutMs: 35000 });
  },
};
