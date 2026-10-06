/**
 * CARD-639: the course "amplifiers" step is gone. A course started from the Education Studio goes
 * from environment straight to retention, jumping to "amplifiers" is refused, and no filler
 * "Course Visual Amplifiers" note or "How does the visual amplifier model..." quiz item is written.
 * No model is called.
 */
import { getJson, openApp } from './lib/app.mjs';

const AGENT = 'tutor';
const TOPIC = 'TCP three-way handshake';

async function post(request, url, data) {
  const res = await request.post(url, { data });
  let body;
  try { body = await res.json(); } catch { body = null; }
  return { status: res.status(), body };
}

function fillerItems(items) {
  return (items || []).filter((r) => /amplifier/i.test(String(r.prompt || '')) || String(r.item_id || '').endsWith('_amplifiers'));
}

export default {
  id: 'card-639-course-skips-amplifier-step',
  card: 'CARD-639',
  title: 'Course skips the removed amplifiers step',
  async run(j, { page, request, base }) {
    let courseId = '';

    await j.step('Set a topic active in the Education Studio; the course has no amplifiers step', async () => {
      await openApp(page, base);
      await page.waitForTimeout(1500);
      if (!(await page.locator('#view-education').isVisible())) await page.locator('#dock-education').click();
      await page.locator('#view-education').waitFor({ state: 'visible', timeout: 20000 });
      await page.locator('#educationTopicInput').fill(TOPIC);
      await page.locator('#educationSetActiveContextBtn').click();
      let data = null;
      for (let i = 0; i < 20 && !courseId; i += 1) {
        await page.waitForTimeout(500);
        data = await getJson(request, `${base}/api/education/course?agent_id=${AGENT}&topic_id=${encodeURIComponent(TOPIC)}`);
        courseId = (data.course && data.course.course_id) || '';
      }
      if (!courseId) throw new Error('Set active did not create a course');
      const steps = data.chrome.steps || [];
      j.note(`course ${courseId} steps: ${steps.join(' > ')}; default steps: ${(data.chrome.default_steps || []).join(' > ')}`);
      if (steps.includes('amplifiers') || (data.chrome.default_steps || []).includes('amplifiers')) throw new Error('amplifiers is still a course step');
      if (steps.indexOf('retention') !== steps.indexOf('environment') + 1) throw new Error('retention does not follow environment');
      await j.screenshot('education-course-active');
    }, { timeoutMs: 60000 });

    await j.step('Completing environment moves the course to retention', async () => {
      const jump = await post(request, `${base}/api/education/course/jump`, { agent_id: AGENT, course_id: courseId, step: 'environment' });
      if (jump.status !== 200) throw new Error(`jump to environment -> ${jump.status}`);
      const done = await post(request, `${base}/api/education/course/complete-step`, { agent_id: AGENT, course_id: courseId });
      if (done.status !== 200) throw new Error(`complete-step -> ${done.status}`);
      j.note(`completed ${done.body.completed_step}; wrote ${done.body.wiki_path || 'no note'}; next step ${done.body.course.current_step}`);
      if (done.body.completed_step !== 'environment') throw new Error(`completed ${done.body.completed_step}`);
      if (done.body.course.current_step !== 'retention') throw new Error(`next step is ${done.body.course.current_step}, not retention`);
    }, { timeoutMs: 60000 });

    await j.step('Jumping to the removed step is refused', async () => {
      const jump = await post(request, `${base}/api/education/course/jump`, { agent_id: AGENT, course_id: courseId, step: 'amplifiers' });
      j.note(`jump to amplifiers -> ${jump.status} ${JSON.stringify(jump.body && jump.body.detail)}`);
      if (jump.status !== 422) throw new Error(`jump to amplifiers -> ${jump.status}, expected 422`);
    }, { timeoutMs: 30000 });

    await j.step('Completing retention finishes the course with no filler amplifier quiz item', async () => {
      const done = await post(request, `${base}/api/education/course/complete-step`, { agent_id: AGENT, course_id: courseId });
      if (done.status !== 200) throw new Error(`complete-step -> ${done.status}`);
      j.note(`completed ${done.body.completed_step}; course status ${done.body.course.status}`);
      if (done.body.completed_step !== 'retention' || done.body.course.status !== 'completed') throw new Error('course did not finish after retention');
      const ledger = await getJson(request, `${base}/api/education/mastery?agent_id=${AGENT}`);
      const filler = fillerItems(ledger.items);
      j.note(`mastery ledger: ${ledger.count} item(s), amplifier filler ${filler.length}`);
      if (filler.length) throw new Error(`filler items written: ${filler.map((r) => r.item_id).join(', ')}`);
      await page.reload({ waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(2500);
      if (!(await page.locator('#view-education').isVisible())) await page.locator('#dock-education').click();
      await page.locator('#view-education').waitFor({ state: 'visible', timeout: 20000 });
      await j.screenshot('education-after-course');
    }, { timeoutMs: 60000 });
  },
};
