/**
 * CARD-744 journey: Add HITL-gated wiki_note_delete and wiki_note_move to wiki-curation
 * and prune empty topic folders.
 * 1) Seeds two notes in nested topic folders under 01_Notes/general/:
 *    - 01_Notes/general/temp_move_topic/splunk_move_note.md
 *    - 01_Notes/general/temp_delete_topic/splunk_stub_note.md
 * 2) In Chat, asks AutoReiv to open wiki-curation via skill_view, move splunk_move_note.md
 *    to 01_Notes/devops/splunk_ops/splunk_move_note.md with wiki_note_move, and delete
 *    splunk_stub_note.md with wiki_note_delete, approving the HITL confirmation cards.
 * 3) Verifies the moved note exists at 01_Notes/devops/splunk_ops/splunk_move_note.md with
 *    updated domain/topic frontmatter, the deleted stub note is gone, and both now-empty
 *    parent topic directories (temp_move_topic/ and temp_delete_topic/) are pruned from disk
 *    and the Wiki tree on desktop and phone.
 */
import fs from 'node:fs';
import path from 'node:path';
import { askAndApprove, getJson, openApp, openTab, trackStreams } from './lib/app.mjs';

const AGENT_ID = 'autoreiv';
const MOVE_SRC = '01_Notes/general/temp_move_topic/splunk_move_note.md';
const MOVE_DST = '01_Notes/devops/splunk_ops/splunk_move_note.md';
const DEL_REL = '01_Notes/general/temp_delete_topic/splunk_stub_note.md';

function resolveWikiRoot() {
  const dataDir = process.env.AUTOREIV_DATA_DIR || path.resolve(process.cwd(), 'scratch', 'live_qa_data');
  return path.join(dataDir, 'wiki');
}

async function ensureChatOpen(page) {
  if (!(await page.locator('#promptInput').isVisible().catch(() => false))) {
    const dockChat = page.locator('#dock-chat');
    if (await dockChat.isVisible().catch(() => false)) {
      await dockChat.click();
    } else {
      await page.locator('#tab-chat').click();
    }
  }
  await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 20000 });
  if ((await page.locator('#agentSelect').inputValue().catch(() => '')) !== AGENT_ID) {
    await page.selectOption('#agentSelect', AGENT_ID);
    await page.waitForTimeout(500);
  }
}

export default {
  id: 'card-744-add-wiki-note-delete-and-move',
  card: 'CARD-744',
  title: 'Add HITL-gated wiki_note_delete and wiki_note_move to wiki-curation and prune empty topic folders',
  allow: [],
  async run(j, { page, request, base }) {
    const wikiRoot = resolveWikiRoot();

    await j.step('Seed nested topic notes for move and delete under 01_Notes/general/', async () => {
      const putMove = await request.put(`${base}/api/wiki/note`, {
        data: {
          path: MOVE_SRC,
          content: '# Splunk Forwarder Architecture\n\nUniversal forwarder vs heavy forwarder routing.',
          update_frontmatter: {
            title: 'Splunk Forwarder Architecture',
            domain: 'general',
            topic: 'temp_move_topic',
            tags: ['splunk', 'devops'],
          },
        },
      });
      if (!putMove.ok()) throw new Error(`PUT ${MOVE_SRC} -> ${putMove.status()}`);

      const putDel = await request.put(`${base}/api/wiki/note`, {
        data: {
          path: DEL_REL,
          content: 'Temporary duplicate stub note to delete.',
          update_frontmatter: {
            title: 'Splunk Stub Note',
            domain: 'general',
            topic: 'temp_delete_topic',
          },
        },
      });
      if (!putDel.ok()) throw new Error(`PUT ${DEL_REL} -> ${putDel.status()}`);

      if (!fs.existsSync(path.join(wikiRoot, MOVE_SRC))) {
        throw new Error(`Expected ${MOVE_SRC} on disk`);
      }
      if (!fs.existsSync(path.join(wikiRoot, DEL_REL))) {
        throw new Error(`Expected ${DEL_REL} on disk`);
      }

      const tree = await getJson(request, `${base}/api/wiki/tree`);
      const generalTopics = (tree['01_Notes'] && tree['01_Notes'].general) || {};
      if (!generalTopics.temp_move_topic || !generalTopics.temp_delete_topic) {
        throw new Error(`Expected temp_move_topic and temp_delete_topic in tree, got: ${JSON.stringify(Object.keys(generalTopics))}`);
      }
      j.note('Seeded both nested topic notes under 01_Notes/general/');
    });

    await j.step('In Chat, AutoReiv mounts wiki-curation and runs wiki_note_move and wiki_note_delete with HITL approval', async () => {
      await openApp(page, base);
      await ensureChatOpen(page);
      const streams = trackStreams(page);

      const approvals = await askAndApprove(
        page,
        streams,
        `Step 1: call skill_view with skill_id="wiki-curation". ` +
          `Step 2: call wiki_note_move with source_path="${MOVE_SRC}" and destination_path="${MOVE_DST}". ` +
          `Step 3: call wiki_note_delete with relative_path="${DEL_REL}" and reason="cleanup duplicate stub". ` +
          `Confirm when both operations have completed.`,
        async () => {
          const movedExists = fs.existsSync(path.join(wikiRoot, MOVE_DST));
          const deletedGone = !fs.existsSync(path.join(wikiRoot, DEL_REL));
          return movedExists && deletedGone;
        },
        240000,
        { onApprove: (lbl) => j.note(`Approved HITL card: ${lbl}`) },
      );

      if (approvals < 1) {
        throw new Error(`Expected at least 1 HITL approval for wiki_note_move / wiki_note_delete, got ${approvals}`);
      }
      if (!fs.existsSync(path.join(wikiRoot, MOVE_DST))) {
        throw new Error(`Expected moved note at ${MOVE_DST}`);
      }
      if (fs.existsSync(path.join(wikiRoot, MOVE_SRC))) {
        throw new Error(`Expected source note ${MOVE_SRC} to be removed after move`);
      }
      if (fs.existsSync(path.join(wikiRoot, DEL_REL))) {
        throw new Error(`Expected ${DEL_REL} to be deleted`);
      }
      if (fs.existsSync(path.join(wikiRoot, '01_Notes', 'general', 'temp_move_topic'))) {
        throw new Error('Expected empty folder 01_Notes/general/temp_move_topic to be pruned');
      }
      if (fs.existsSync(path.join(wikiRoot, '01_Notes', 'general', 'temp_delete_topic'))) {
        throw new Error('Expected empty folder 01_Notes/general/temp_delete_topic to be pruned');
      }

      const movedNote = await getJson(request, `${base}/api/wiki/note?path=${encodeURIComponent(MOVE_DST)}`);
      const meta = movedNote.meta || movedNote.frontmatter || {};
      if (meta.domain !== 'devops' || meta.topic !== 'splunk_ops') {
        throw new Error(`Expected moved note domain=devops, topic=splunk_ops, got: ${JSON.stringify(meta)}`);
      }
      j.note(`Moved note to ${MOVE_DST} and deleted ${DEL_REL} with empty topic folders pruned (${approvals} HITL approvals)`);
    }, { timeoutMs: 260000 });

    await j.step('Verify Wiki Studio reflects the updated vault tree and clean up test note', async () => {
      await openTab(page, 'wiki');
      const tree = await getJson(request, `${base}/api/wiki/tree`);
      const generalTopics = (tree['01_Notes'] && tree['01_Notes'].general) || {};
      if (generalTopics.temp_move_topic || generalTopics.temp_delete_topic) {
        throw new Error(`Expected pruned topic folders to be absent from Wiki tree, got: ${JSON.stringify(Object.keys(generalTopics))}`);
      }
      const devopsTopics = (tree['01_Notes'] && tree['01_Notes'].devops) || {};
      if (!devopsTopics.splunk_ops || devopsTopics.splunk_ops.length === 0) {
        throw new Error(`Expected moved note under 01_Notes.devops.splunk_ops, got: ${JSON.stringify(devopsTopics)}`);
      }

      const delRes = await request.delete(`${base}/api/wiki/note?path=${encodeURIComponent(MOVE_DST)}`);
      if (!delRes.ok()) throw new Error(`DELETE ${MOVE_DST} -> ${delRes.status()}`);
      if (fs.existsSync(path.join(wikiRoot, '01_Notes', 'devops', 'splunk_ops'))) {
        throw new Error('Expected DELETE /api/wiki/note to prune empty 01_Notes/devops/splunk_ops folder');
      }
    });
  },
};
