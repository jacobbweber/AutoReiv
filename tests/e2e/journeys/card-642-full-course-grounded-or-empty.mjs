/**
 * CARD-642..647 shared live check: run a whole course twice on a throwaway server with the real model,
 * once on a topic with a learner note and once on a topic with no notes. No template quiz item and no
 * generic note may exist anywhere in either course: every written step is grounded in the learner's
 * note or in what the learner wrote, and steps that cannot be grounded write nothing.
 */
import { getJson, openApp } from './lib/app.mjs';

const AGENT = 'tutor';
const STEPS = ['priming', 'dual_coding', 'retrieval', 'elaboration', 'construction', 'application', 'analysis', 'environment', 'retention'];
const NOTED = 'Raft log replication';
const BARE = 'Bloom filter false positives';
const NOTE = [
  '# Raft log replication',
  '',
  'The leader accepts client commands and appends each one to its own log as a new entry with the current term.',
  'It sends AppendEntries messages carrying the new entries, plus the previous log index and term, to every follower.',
  'A follower accepts the entries only if its log has an entry at the previous index with the same term; otherwise it rejects them and the leader retries with an earlier index.',
  'Once a majority of servers have stored an entry, the leader advances the commit index and applies the entry to its state machine.',
  'Followers learn the commit index from the next AppendEntries heartbeat and apply committed entries in log order.',
].join('\n');
const SUBMISSION = (topic) =>
  `My ${topic} lab: the leader appends each client command to its log with the current term and sends AppendEntries with the previous log index and term to every follower. ` +
  'A follower rejects entries when its log has no entry at the previous index with the same term, and the leader retries with an earlier index. ' +
  'When a majority of servers stored the entry, the leader advances the commit index and applies it to its state machine; followers learn the commit index from the next heartbeat and apply entries in log order.';
const EXTRA = (topic) => ({
  elaboration: { learner_explanation: topic === NOTED
    ? 'The leader only commits an entry after a majority of followers have stored it, and a follower rejects AppendEntries when the previous index and term do not match its log.'
    : 'A Bloom filter can say an item is present when it is not, because other items may have set all of its bit positions; it never misses an item that was added.' },
  construction: { lab_submission: SUBMISSION(topic) },
  application: { lab_submission: SUBMISSION(topic) },
});
const TEMPLATE_BITS = [
  'What Learning OS step did you just complete', 'In one sentence, what is', 'durable concept learned via Priming',
  'Where should Priming write durable knowledge', 'What is the Priming schema outline', 'memory.db ledger anchors',
  'What is the analysis pass rate', 'Perform construction lab', 'Perform application lab', 'with verified invariants',
  'How would you explain the core mechanism', 'Learner self-explanation to be added', 'guarantees correct state progression',
  'What delivery profile and runtime constraints', 'single-brain memory.db', 'Single-brain persistence',
  'Structural consistency', 'Deterministic state progression', 'pytest tests/unit/education/test_',
  'Key Concepts & Invariants', 'verbal prose and visual diagrams', 'Intuitive mental model illustrating',
];
const BODY_META = /^(tags|kind|step|topic|created):|^>\s*\*\*(Topic|Pedagogy Phase|Generated|Created):\*\*/m;
const NOTE_TERMS = /AppendEntries|commit index|majority|follower|previous (log )?index/i;

async function post(request, url, data) {
  const res = await request.post(url, { data, timeout: 240000 });
  let body;
  try { body = await res.json(); } catch { body = null; }
  if (res.status() !== 200) throw new Error(`POST ${url} -> ${res.status()} ${JSON.stringify(body).slice(0, 300)}`);
  return body;
}

function stripFrontMatter(text) {
  const t = String(text || '');
  if (!t.startsWith('---')) return t;
  const end = t.indexOf('\n---', 3);
  return end === -1 ? t : t.slice(end + 4);
}

async function runCourse(j, request, base, topic) {
  const started = await post(request, `${base}/api/education/course/start`, { agent_id: AGENT, topic_id: topic, steps: STEPS });
  const courseId = started.course.course_id;
  const written = {};
  for (const step of STEPS) {
    const done = await post(request, `${base}/api/education/course/complete-step`, { agent_id: AGENT, course_id: courseId, ...(EXTRA(topic)[step] || {}) });
    written[step] = done;
    j.note(`[${topic}] ${step}: wrote ${done.wiki_path || 'nothing'}; quiz ${(done.item_ids || []).length}; skip ${done.skip_reason || done.grounding_skip_reason || '-'}; graded ${done.graded ?? '-'}; passed ${done.passed}; next ${done.course.current_step} (${done.course.status})`);
    if (done.completed_step !== step) throw new Error(`expected to complete ${step}, completed ${done.completed_step}`);
    if (done.passed === false) throw new Error(`[${topic}] ${step} lab failed: ${JSON.stringify(done.grade_result).slice(0, 300)}`);
  }
  if (written.retention.course.status !== 'completed') throw new Error(`[${topic}] course did not finish`);
  return written;
}

async function checkNote(j, request, base, topic, step, path) {
  const note = await getJson(request, `${base}/api/wiki/note?path=${encodeURIComponent(path)}`);
  const raw = String(note.content || '');
  const body = stripFrontMatter(raw);
  const hit = TEMPLATE_BITS.find((b) => raw.includes(b));
  if (hit) throw new Error(`[${topic}] ${step} note has template text: ${hit}`);
  if (BODY_META.test(body)) throw new Error(`[${topic}] ${step} note has metadata lines in its body`);
  const docType = (note.meta || note.frontmatter || {}).document_type || (raw.match(/document_type:\s*"?([\w-]+)/) || [])[1];
  if (step !== 'priming' && docType === 'priming_schema') throw new Error(`[${topic}] ${step} note is typed priming_schema`);
  return { body, docType };
}

export default {
  id: 'card-642-full-course-grounded-or-empty',
  card: 'CARD-642',
  title: 'A full course with and without topic notes writes no template quiz items or generic notes',
  async run(j, { page, request, base }) {
    let noted;
    let bare;
    await j.step('Course on a topic with a learner note: every written step is grounded in the note', async () => {
      await post(request, `${base}/api/wiki/note`, { title: NOTED, content: NOTE, tags: ['distributed-systems', 'raft'], summary: 'How the Raft leader replicates and commits log entries' });
      noted = await runCourse(j, request, base, NOTED);
      for (const step of ['retrieval', 'retention']) {
        if (noted[step].wiki_path || (noted[step].item_ids || []).length) throw new Error(`${step} wrote something`);
      }
      for (const step of ['priming', 'dual_coding', 'elaboration', 'construction', 'application', 'environment']) {
        const d = noted[step];
        if (!d.wiki_path) {
          if (!['model_unavailable', 'model_output_invalid'].includes(d.skip_reason)) throw new Error(`${step} wrote nothing without a model reason (${d.skip_reason})`);
          continue;
        }
        const { body, docType } = await checkNote(j, request, base, NOTED, step, d.wiki_path);
        if (!NOTE_TERMS.test(body)) throw new Error(`${step} note does not use the learner note`);
        j.note(`[${NOTED}] ${step} note ${d.wiki_path} (${docType}) grounded; sources ${((d.artifact || {}).sources || []).map((s) => s.path).join(', ') || '-'}`);
      }
      const grounded = ['priming', 'dual_coding', 'construction', 'application', 'environment'].filter((s) => noted[s].wiki_path);
      if (grounded.length < 3) throw new Error(`only ${grounded.length} grounded steps wrote with a note and a model`);
    }, { timeoutMs: 600000 });

    await j.step('Course on a topic with no notes: only the learner\'s own words and the scorecard are saved', async () => {
      bare = await runCourse(j, request, base, BARE);
      for (const step of ['priming', 'dual_coding', 'environment']) {
        if (bare[step].wiki_path || (bare[step].item_ids || []).length) throw new Error(`${step} wrote something with no notes`);
        if (bare[step].skip_reason !== 'no_wiki_notes') throw new Error(`${step} skip reason ${bare[step].skip_reason}`);
      }
      for (const step of ['elaboration', 'construction', 'application']) {
        const d = bare[step];
        if (!d.wiki_path) throw new Error(`${step} did not keep the learner's text`);
        const { body } = await checkNote(j, request, base, BARE, step, d.wiki_path);
        const own = step === 'elaboration' ? EXTRA(BARE).elaboration.learner_explanation : SUBMISSION(BARE);
        if (!body.includes(own.slice(0, 60))) throw new Error(`${step} note does not hold the learner's own text`);
        // Elaboration may add probes and a quiz item grounded in the learner's own explanation (CARD-644); labs may not invent anything.
        const invented = step === 'elaboration' ? /^## (Objective|Tasks)/m : /^## (Quiz|Objective|Tasks|Questions to push further)/m;
        if (invented.test(body)) throw new Error(`${step} note has invented sections`);
      }
      if (bare.analysis.wiki_path) await checkNote(j, request, base, BARE, 'analysis', bare.analysis.wiki_path);
      const items = ((await getJson(request, `${base}/api/education/mastery?agent_id=${AGENT}`)).items || []).filter((r) => r.topic === BARE);
      const words = (t) => new Set(String(t).toLowerCase().match(/[a-z]{4,}/g) || []);
      const own = words(EXTRA(BARE).elaboration.learner_explanation);
      const foreign = items.filter((r) => !String(r.item_id).includes('elaboration') || ![...words(r.expected_answer)].some((w) => own.has(w)));
      j.note(`[${BARE}] quiz items: ${items.map((r) => `${r.item_id}: ${r.prompt} -> ${r.expected_answer}`).join(' | ') || 'none'}`);
      if (foreign.length) throw new Error(`quiz items not grounded in the learner's own words for a topic with no notes: ${foreign.map((r) => r.prompt).join(' | ')}`);
    }, { timeoutMs: 600000 });

    await j.step('No template quiz items or generic course notes exist anywhere', async () => {
      const items = (await getJson(request, `${base}/api/education/mastery?agent_id=${AGENT}`)).items || [];
      j.note(`quiz items (${items.length}): ${items.map((r) => `${r.topic} / ${r.item_id}: ${r.prompt} -> ${r.expected_answer}`).join(' | ')}`);
      const generic = items.filter((r) => TEMPLATE_BITS.some((b) => `${r.prompt} ${r.expected_answer}`.includes(b)));
      if (generic.length) throw new Error(`template quiz items: ${generic.map((r) => r.prompt).join(' | ')}`);
      const tree = await getJson(request, `${base}/api/wiki/notes`);
      const notes = (Array.isArray(tree) ? tree : tree.notes || tree.items || []);
      const courseNotes = notes.filter((n) => /^(Course |Priming:)/.test(n.title || ''));
      j.note(`course notes (${courseNotes.length}): ${courseNotes.map((n) => n.title).join('; ')}`);
      for (const n of courseNotes) await checkNote(j, request, base, n.title, /^Priming/.test(n.title) ? 'priming' : 'course', n.path);
      if (courseNotes.some((n) => /Course (Retrieval|Retention|Custom)/.test(n.title))) throw new Error('a generic course note exists');
    }, { timeoutMs: 120000 });

    await j.step('The Wiki shows the course notes; a grounded priming note opens with its source', async () => {
      await openApp(page, base);
      await page.waitForTimeout(1500);
      if (!(await page.locator('#view-wiki').isVisible())) await page.locator('#dock-wiki').click();
      await page.locator('#view-wiki').waitFor({ state: 'visible', timeout: 20000 });
      const search = page.locator('#wikiSearchInput');
      await search.fill('Course');
      await page.waitForTimeout(1500);
      await j.screenshot('wiki-course-notes');
      const target = noted.priming.wiki_path ? `Priming: ${NOTED}` : `Course Elaboration: ${NOTED}`;
      await search.fill(target.split(':')[0]);
      await page.waitForTimeout(1500);
      const link = page.locator('#view-wiki').getByText(target, { exact: false }).first();
      await link.click();
      await page.waitForTimeout(1500);
      const text = await page.locator('#view-wiki').innerText();
      if (!NOTE_TERMS.test(text)) throw new Error('the opened note does not show content from the learner note');
      if (/tags: \[|kind: education_course_step/.test(text)) throw new Error('the opened note shows metadata in its body');
      await j.screenshot('grounded-note-open');
    }, { timeoutMs: 90000 });
  },
};