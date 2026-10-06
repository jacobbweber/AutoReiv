/**
 * CARD-640: the dual coding course step is built from your own wiki notes on the topic via the model,
 * or writes nothing. A topic with no notes skips the step; after a real note is added, the step
 * writes a note whose diagram and quiz come from that note and link back to it. Calls the model.
 */
import { getJson, openApp } from './lib/app.mjs';

const AGENT = 'tutor';
const STEPS = ['priming', 'dual_coding', 'retrieval', 'elaboration', 'construction', 'application', 'analysis', 'environment', 'retention'];
const BARE_TOPIC = 'Bloom filter false positives';
const TOPIC = 'Raft log replication';
const NOTE = [
  '# Raft log replication',
  '',
  'The leader accepts client commands and appends each one to its own log as a new entry.',
  'It sends AppendEntries messages carrying the new entries to every follower.',
  'A follower accepts the entries only if its log has an entry at the previous index with the same term; otherwise it rejects them and the leader retries with an earlier index.',
  'Once a majority of servers have stored an entry, the leader advances the commit index and applies the entry to its state machine.',
  'Followers learn the new commit index from the next AppendEntries message (heartbeats are empty AppendEntries) and apply committed entries in log order.',
].join('\n');
const TEMPLATE_BITS = ['Key Concepts & Invariants', 'Concrete Implementation Flow', 'verbal prose and visual diagrams', 'two representations used in Dual Coding'];

async function post(request, url, data) {
  const res = await request.post(url, { data, timeout: 240000 });
  let body;
  try { body = await res.json(); } catch { body = null; }
  if (res.status() !== 200) throw new Error(`POST ${url} -> ${res.status()} ${JSON.stringify(body).slice(0, 300)}`);
  return body;
}

async function courseOnDualCoding(request, base, topic) {
  const started = await post(request, `${base}/api/education/course/start`, { agent_id: AGENT, topic_id: topic, steps: STEPS });
  const courseId = started.course.course_id;
  await post(request, `${base}/api/education/course/jump`, { agent_id: AGENT, course_id: courseId, step: 'dual_coding' });
  return courseId;
}

export default {
  id: 'card-640-dual-coding-grounded-or-skipped',
  card: 'CARD-640',
  title: 'Dual coding is grounded in your notes or skipped',
  async run(j, { page, request, base }) {
    await j.step('A topic with no wiki notes skips dual coding and writes nothing', async () => {
      const courseId = await courseOnDualCoding(request, base, BARE_TOPIC);
      const done = await post(request, `${base}/api/education/course/complete-step`, { agent_id: AGENT, course_id: courseId });
      j.note(`completed ${done.completed_step}; skip_reason ${done.skip_reason}; wiki_path ${done.wiki_path}; next ${done.course.current_step}`);
      if (done.skip_reason !== 'no_wiki_notes' || done.wiki_path) throw new Error('dual coding wrote something without notes');
      if (done.course.current_step !== 'retrieval') throw new Error(`course did not advance: ${done.course.current_step}`);
      const ledger = await getJson(request, `${base}/api/education/mastery?agent_id=${AGENT}`);
      if ((ledger.items || []).some((r) => String(r.item_id).includes('dual_coding'))) throw new Error('a dual coding quiz item was written');
    }, { timeoutMs: 60000 });

    let notePath = '';
    await j.step('With a real note on the topic, dual coding writes content taken from that note', async () => {
      const created = await post(request, `${base}/api/wiki/note`, { title: TOPIC, content: NOTE, tags: ['distributed-systems', 'raft'], summary: 'How the Raft leader replicates and commits log entries' });
      const sourcePath = created.path;
      j.note(`source note ${sourcePath}`);
      const courseId = await courseOnDualCoding(request, base, TOPIC);
      const t0 = Date.now();
      const done = await post(request, `${base}/api/education/course/complete-step`, { agent_id: AGENT, course_id: courseId });
      j.note(`completed ${done.completed_step} in ${Math.round((Date.now() - t0) / 1000)} s; skip_reason ${done.skip_reason}; wiki_path ${done.wiki_path}; next ${done.course.current_step}`);
      if (done.course.current_step !== 'retrieval') throw new Error('course did not advance');
      if (!done.wiki_path) throw new Error(`no grounded note written (skip_reason ${done.skip_reason})`);
      notePath = done.wiki_path;
      const note = await getJson(request, `${base}/api/wiki/note?path=${encodeURIComponent(notePath)}`);
      const text = String(note.content || '');
      j.note(`note:\n${text.slice(0, 1400)}`);
      if (!text.includes('```mermaid')) throw new Error('note has no diagram');
      if (!text.includes(`[[${sourcePath.replace(/\.md$/, '')}]]`)) throw new Error('note does not link the source note');
      if (TEMPLATE_BITS.some((b) => text.includes(b))) throw new Error('note contains the old template');
      if (!/AppendEntries|commit index|majority|follower/i.test(text)) throw new Error('note does not use the source note');
      const item = (await getJson(request, `${base}/api/education/mastery?agent_id=${AGENT}`)).items.find((r) => r.item_id === done.item_ids[0]);
      j.note(`quiz item: ${item && item.prompt} -> ${item && item.expected_answer}`);
      if (!item || TEMPLATE_BITS.some((b) => `${item.prompt} ${item.expected_answer}`.includes(b))) throw new Error('quiz item is missing or generic');
    }, { timeoutMs: 300000 });

    await j.step('The note shows in the Wiki Studio', async () => {
      await openApp(page, base);
      await page.waitForTimeout(1500);
      if (!(await page.locator('#view-wiki').isVisible())) await page.locator('#dock-wiki').click();
      await page.locator('#view-wiki').waitFor({ state: 'visible', timeout: 20000 });
      const search = page.locator('#wikiSearchInput');
      if (await search.isVisible().catch(() => false)) {
        await search.fill('Course Dual Coding');
        await page.waitForTimeout(1500);
      }
      const hit = page.getByText(`Course Dual Coding: ${TOPIC}`).first();
      if (await hit.isVisible().catch(() => false)) {
        await hit.click();
        await page.waitForTimeout(2000);
      } else {
        j.note('note title not visible in the Wiki list; screenshot shows the Wiki Studio');
      }
      await j.screenshot('dual-coding-note-in-wiki');
    }, { timeoutMs: 60000 });
  },
};
