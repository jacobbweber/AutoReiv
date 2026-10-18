/**
 * CARD-715 journey: Backend monolith decomposition across education, system updates,
 * job orchestration, and card/education tools.
 */
import { waitFor } from './lib/runner.mjs';
import { getJson, openApp } from './lib/app.mjs';

async function postJson(request, url, data) {
  const res = await request.post(url, { data });
  if (!res.ok()) throw new Error(`POST ${url} -> ${res.status()}`);
  return res.json();
}

export default {
  id: 'card-715-backend-monolith-decomposition',
  card: 'CARD-715',
  title: 'Education routers, course pipeline, retention due helper, and system update git ops verification',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const suffix = `${viewport.name.toLowerCase()}_${Date.now() % 10000}`;
    const topic = `Card 715 Topic ${suffix}`;
    const itemId = `edu_card715_${suffix}`;

    await j.step('Verify decomposed Education routers (course, mastery, quiz grade, retention force-due, environment, depth)', async () => {
      const startRes = await postJson(request, `${base}/api/education/course/start`, {
        agent_id: 'tutor',
        topic_id: topic,
      });
      if (!startRes || !startRes.course || !startRes.course.course_id) {
        throw new Error(`Expected course_id from /api/education/course/start, got: ${JSON.stringify(startRes)}`);
      }
      const courseId = startRes.course.course_id;

      const upsertRes = await postJson(request, `${base}/api/education/mastery/upsert`, {
        agent_id: 'tutor',
        item_id: itemId,
        topic,
        wiki_path: `00_Inbox/${itemId}.md`,
        prompt: 'What is the maximum line count enforced by CARD-715 for backend Python files?',
        expected_answer: '800',
      });
      if (!upsertRes || upsertRes.item_id !== itemId) {
        throw new Error(`Failed to upsert mastery item: ${JSON.stringify(upsertRes)}`);
      }

      const gradeRes = await postJson(request, `${base}/api/education/quiz/grade`, {
        agent_id: 'tutor',
        item_id: itemId,
        answer: '800',
      });
      if (!gradeRes || gradeRes.correct !== true || gradeRes.grade !== 'pass') {
        throw new Error(`Expected binary pass on /api/education/quiz/grade, got: ${JSON.stringify(gradeRes)}`);
      }

      const retRes = await postJson(request, `${base}/api/education/retention/run`, {
        agent_id: 'tutor',
        force_due_item_id: itemId,
      });
      if (!retRes || !retRes.result || retRes.result.status !== 'ok') {
        throw new Error(`Expected retention/run status=ok with force_due_item_id, got: ${JSON.stringify(retRes)}`);
      }

      const envProfiles = await getJson(request, `${base}/api/education/environment/profiles`);
      if (!envProfiles || !Array.isArray(envProfiles.profiles) || envProfiles.profiles.length === 0) {
        throw new Error(`Expected delivery profiles from /api/education/environment/profiles`);
      }

      const depthRes = await getJson(
        request,
        `${base}/api/education/course/depth?agent_id=tutor&course_id=${encodeURIComponent(courseId)}`
      );
      if (!depthRes || !depthRes.success || !depthRes.depth) {
        throw new Error(`Expected depth ladder from /api/education/course/depth, got: ${JSON.stringify(depthRes)}`);
      }

      j.note(`course=${courseId}, graded=${gradeRes.grade}, retention=${retRes.result.status}, profiles=${envProfiles.profiles.length}`);
    }, { timeoutMs: 30000 });

    await j.step('Verify System UpdateService git ops endpoints (/api/system/version, branches, history)', async () => {
      const version = await getJson(request, `${base}/api/system/version`);
      if (!version || typeof version.current_version !== 'string') {
        throw new Error(`Unexpected /api/system/version payload: ${JSON.stringify(version)}`);
      }
      const branches = await getJson(request, `${base}/api/system/updates/branches`);
      if (!branches || !Array.isArray(branches.branches)) {
        throw new Error(`Unexpected /api/system/updates/branches payload: ${JSON.stringify(branches)}`);
      }
      const history = await getJson(request, `${base}/api/system/updates/history`);
      if (!history || !Array.isArray(history.entries)) {
        throw new Error(`Unexpected /api/system/updates/history payload: ${JSON.stringify(history)}`);
      }
      j.note(`version=${version.current_version} (${version.commit || 'no-sha'}), branches=${branches.branches.length}`);
    }, { timeoutMs: 20000 });

    await j.step('Open Education Studio (#view-education) and verify UI renders cleanly', async () => {
      await openApp(page, base);
      await page.evaluate(() => {
        if (typeof window.switchView === 'function') {
          window.switchView('education');
        } else {
          const btn = document.getElementById('dock-education');
          if (btn) btn.click();
        }
      });
      await page.locator('#view-education').waitFor({ state: 'visible', timeout: 15000 });
      await waitFor(async () => {
        const visible = await page.locator('#view-education').isVisible();
        return visible;
      }, { timeoutMs: 10000, label: 'education studio visible' });
    }, { timeoutMs: 30000 });
  },
};
