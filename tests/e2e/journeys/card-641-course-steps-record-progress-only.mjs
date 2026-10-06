/**
 * CARD-641 (with CARD-640): run a whole course through on a throwaway server with the real model.
 * Steps without their own writer (retrieval, retention) record progress only: no "Course Retrieval"
 * or "Course Retention" note and no "What Learning OS step did you just complete" quiz item.
 * Dual coding is built from the learner's note or skipped, never the old template.
 */
import { getJson, openApp } from './lib/app.mjs';

const AGENT = 'tutor';
const STEPS = ['priming', 'dual_coding', 'retrieval', 'elaboration', 'construction', 'application', 'analysis', 'environment', 'retention'];
const TOPIC = 'Raft log replication';
const NOTE = [
  '# Raft log replication',
  '',
  'The leader accepts client commands and appends each one to its own log as a new entry.',
  'It sends AppendEntries messages carrying the new entries to every follower.',
  'A follower accepts the entries only if its log has an entry at the previous index with the same term; otherwise it rejects them and the leader retries with an earlier index.',
  'Once a majority of servers have stored an entry, the leader advances the commit index and applies the entry to its state machine.',
].join('\n');
const EXTRA = {
  elaboration: { learner_explanation: 'The leader only commits an entry after a majority of followers have stored it, so a committed entry survives a leader crash.' },
  construction: { lab_submission: 'Defines the log entry schema and state model for Raft log replication, with deterministic state transitions for AppendEntries and boundary checks for edge cases such as a term mismatch at the previous index.' },
  application: { lab_submission: 'Executes an end-to-end Raft log replication workflow under injected follower failures and verifies the invariant guarantees: committed entries are never lost and logs match; emits a verification receipt.' },
};
const TEMPLATE_BITS = ['Key Concepts & Invariants', 'verbal prose and visual diagrams', 'What Learning OS step did you just complete'];

async function post(request, url, data) {
  const res = await request.post(url, { data, timeout: 240000 });
  let body;
  try { body = await res.json(); } catch { body = null; }
  if (res.status() !== 200) throw new Error(`POST ${url} -> ${res.status()} ${JSON.stringify(body).slice(0, 300)}`);
  return body;
}

export default {
  id: 'card-641-course-steps-record-progress-only',
  card: 'CARD-641',
  title: 'Course steps without a writer record progress only',
  async run(j, { page, request, base }) {
    const written = {};
    await j.step('Run a whole course; retrieval and retention write nothing, dual coding is grounded or skipped', async () => {
      await post(request, `${base}/api/wiki/note`, { title: TOPIC, content: NOTE, tags: ['distributed-systems', 'raft'], summary: 'How the Raft leader replicates and commits log entries' });
      const started = await post(request, `${base}/api/education/course/start`, { agent_id: AGENT, topic_id: TOPIC, steps: STEPS });
      const courseId = started.course.course_id;
      for (const step of STEPS) {
        const done = await post(request, `${base}/api/education/course/complete-step`, { agent_id: AGENT, course_id: courseId, ...(EXTRA[step] || {}) });
        written[step] = done;
        j.note(`${step}: wrote ${done.wiki_path || 'nothing'}; quiz items ${(done.item_ids || []).length}; skip_reason ${done.skip_reason}; passed ${done.passed}; next ${done.course.current_step} (${done.course.status})`);
        if (done.completed_step !== step) throw new Error(`expected to complete ${step}, completed ${done.completed_step}`);
        if (done.passed === false) throw new Error(`${step} lab was not passed; course halted`);
      }
      for (const step of ['retrieval', 'retention']) {
        const d = written[step];
        if (d.wiki_path || (d.item_ids || []).length || d.skip_reason !== 'no_writer') throw new Error(`${step} wrote something`);
      }
      const dual = written.dual_coding;
      if (!dual.wiki_path && !['no_wiki_notes', 'model_unavailable', 'model_output_invalid'].includes(dual.skip_reason)) throw new Error('dual coding neither wrote nor gave a skip reason');
      if (written.retention.course.status !== 'completed') throw new Error('course did not finish');
    }, { timeoutMs: 420000 });

    await j.step('No generic course notes or quiz items exist', async () => {
      const tree = await getJson(request, `${base}/api/wiki/notes`);
      const notes = (Array.isArray(tree) ? tree : tree.notes || tree.items || []).map((n) => `${n.title || ''}|${n.path || ''}`);
      const courseNotes = notes.filter((n) => /course/i.test(n));
      j.note(`course notes: ${courseNotes.join('; ')}`);
      if (notes.some((n) => /Course (Retrieval|Retention|Custom)/i.test(n))) throw new Error('a generic Course Retrieval/Retention note exists');
      const items = (await getJson(request, `${base}/api/education/mastery?agent_id=${AGENT}`)).items || [];
      j.note(`quiz items (${items.length}): ${items.map((r) => `${r.item_id}: ${r.prompt}`).join(' | ')}`);
      const generic = items.filter((r) => TEMPLATE_BITS.some((b) => `${r.prompt} ${r.expected_answer}`.includes(b)));
      if (generic.length) throw new Error(`generic quiz items: ${generic.map((r) => r.item_id).join(', ')}`);
      if (written.dual_coding.wiki_path) {
        const note = await getJson(request, `${base}/api/wiki/note?path=${encodeURIComponent(written.dual_coding.wiki_path)}`);
        if (TEMPLATE_BITS.some((b) => String(note.content).includes(b))) throw new Error('dual coding note is the template');
        if (!/AppendEntries|commit index|majority|follower/i.test(String(note.content))) throw new Error('dual coding note does not use the source note');
      }
    }, { timeoutMs: 60000 });

    await j.step('The Wiki inbox lists only the course notes from steps with real writers', async () => {
      await openApp(page, base);
      await page.waitForTimeout(1500);
      if (!(await page.locator('#view-wiki').isVisible())) await page.locator('#dock-wiki').click();
      await page.locator('#view-wiki').waitFor({ state: 'visible', timeout: 20000 });
      const search = page.locator('#wikiSearchInput');
      if (await search.isVisible().catch(() => false)) {
        await search.fill('Course');
        await page.waitForTimeout(1500);
      }
      const listText = await page.locator('#view-wiki').innerText();
      if (/Course (Retrieval|Retention)/.test(listText)) throw new Error('the Wiki lists a generic course note');
      await j.screenshot('wiki-course-notes');
    }, { timeoutMs: 60000 });
  },
};
