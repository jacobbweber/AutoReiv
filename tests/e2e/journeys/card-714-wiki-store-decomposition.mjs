/**
 * CARD-714 journey: Decompose src/domain/wiki/store.py, fix double vault file parsing
 * in graph/mindmap, and remove upward domain imports.
 */
import { waitFor } from './lib/runner.mjs';
import { getJson, openApp } from './lib/app.mjs';

async function postJson(request, url, data) {
  const res = await request.post(url, { data });
  if (!res.ok()) throw new Error(`POST ${url} -> ${res.status()}`);
  return res.json();
}

export default {
  id: 'card-714-wiki-store-decomposition',
  card: 'CARD-714',
  title: 'WikiStore decomposition, single-pass graph/mindmap, and Wiki Studio verification',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const suffix = `${viewport.name.toLowerCase()}_${Date.now() % 10000}`;
    const targetTitle = `Card 714 Target ${suffix}`;
    const sourceTitle = `Card 714 Source ${suffix}`;
    let sourcePath = '';

    await j.step('Verify WikiStore note CRUD, templates catalog, single-pass graph, and mindmap APIs', async () => {
      const targetRes = await postJson(request, `${base}/api/wiki/note`, {
        title: targetTitle,
        content: 'Target architecture note for CARD-714 verification.',
        domain: 'systems_engineering',
        topic: 'architecture',
        category: 'notes',
        tags: ['card714', 'architecture'],
      });
      if (!targetRes || !targetRes.success) {
        throw new Error(`Failed to create target wiki note: ${JSON.stringify(targetRes)}`);
      }

      const sourceRes = await postJson(request, `${base}/api/wiki/note`, {
        title: sourceTitle,
        content: `Source note linking to [[${targetTitle}]] for single-pass graph indexing.`,
        domain: 'systems_engineering',
        topic: 'architecture',
        category: 'notes',
        tags: ['card714', 'graph'],
      });
      if (!sourceRes || !sourceRes.success) {
        throw new Error(`Failed to create source wiki note: ${JSON.stringify(sourceRes)}`);
      }
      sourcePath = sourceRes.path;

      const templates = await getJson(request, `${base}/api/wiki/templates`);
      const slugs = new Set((Array.isArray(templates) ? templates : []).map((t) => t.slug));
      if (!slugs.has('feynman-technique') || !slugs.has('education-priming')) {
        throw new Error(`Expected core & education templates in /api/wiki/templates, got: ${Array.from(slugs).join(', ')}`);
      }

      const graph = await getJson(request, `${base}/api/wiki/graph`);
      const hasEdge = (graph.edges || []).some(
        (e) => e.source === sourceRes.path && e.target === targetRes.path
      );
      if (!hasEdge) {
        throw new Error(`Expected wikilink edge ${sourceRes.path} -> ${targetRes.path} in /api/wiki/graph`);
      }

      const mindmap = await getJson(request, `${base}/api/wiki/mindmap?include_tags=true&include_taxonomy=true`);
      const nodeTypes = new Set((mindmap.nodes || []).map((n) => n.type));
      const edgeTypes = new Set((mindmap.edges || []).map((e) => e.type));
      for (const reqNodeType of ['note', 'tag', 'domain', 'topic']) {
        if (!nodeTypes.has(reqNodeType)) {
          throw new Error(`Missing node type '${reqNodeType}' in /api/wiki/mindmap`);
        }
      }
      for (const reqEdgeType of ['wikilink', 'has_tag', 'in_topic', 'in_domain']) {
        if (!edgeTypes.has(reqEdgeType)) {
          throw new Error(`Missing edge type '${reqEdgeType}' in /api/wiki/mindmap`);
        }
      }
      j.note(`Graph nodes=${(graph.nodes || []).length}, MindMap nodes=${(mindmap.nodes || []).length}, templates=${slugs.size}`);
    }, { timeoutMs: 30000 });

    await j.step('Open Wiki Studio (#view-wiki) and verify note rendering and tree', async () => {
      await openApp(page, base);
      await page.evaluate(() => {
        if (typeof window.switchView === 'function') {
          window.switchView('wiki');
        } else {
          const btn = document.getElementById('dock-wiki');
          if (btn) btn.click();
        }
      });
      await page.locator('#view-wiki').waitFor({ state: 'visible', timeout: 15000 });

      await page.evaluate(async (relPath) => {
        const mod = await import('/static/modules/studios/wiki/note.js');
        if (mod && typeof mod.loadWikiNote === 'function') {
          await mod.loadWikiNote(relPath);
        }
      }, sourcePath);

      await waitFor(async () => {
        const text = await page.locator('#view-wiki').innerText().catch(() => '');
        return text.includes(sourceTitle);
      }, { timeoutMs: 15000, intervalMs: 500 });
    }, { timeoutMs: 30000 });

    await j.step('Open Wiki Mind-Map modal and verify canvas and layout bounds', async () => {
      const mmBtn = page.locator('#wikiMindMapViewBtn');
      if (await mmBtn.isVisible().catch(() => false)) {
        await mmBtn.click();
      } else {
        await page.evaluate(async () => {
          const mod = await import('/static/modules/studios/wiki/mindmap.js');
          if (mod && typeof mod.openMindMap === 'function') {
            await mod.openMindMap();
          }
        });
      }

      await page.locator('#wikiMindMapModal').waitFor({ state: 'visible', timeout: 15000 });
      const canvasVisible = await page.locator('#wikiMindMapCanvas').isVisible();
      if (!canvasVisible) {
        throw new Error('#wikiMindMapCanvas is not visible inside #wikiMindMapModal');
      }
      await page.waitForTimeout(600);

      const closeBtn = page.locator('#wikiMindMapCloseBtn');
      if (await closeBtn.isVisible().catch(() => false)) {
        await closeBtn.click();
      }
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
      if (overflow) {
        throw new Error(`Horizontal overflow detected on ${viewport.name}`);
      }
    }, { timeoutMs: 30000 });
  },
};
