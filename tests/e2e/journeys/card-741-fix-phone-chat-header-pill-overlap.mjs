/**
 * CARD-741 journey: Fix phone Chat header pill overlap and retire redundant Pair Tutor button in Education Studio.
 * 1) Creates an active project, opens Chat Studio on desktop and phone (390x844), and verifies #agentSelect and
 *    #chatActiveProjectPill have zero bounding-box overlap and zero horizontal overflow.
 * 2) Opens Education Studio, verifies #educationPairTutorBtn is retired (0 in DOM), enters a study topic in
 *    #educationTopicInput, clicks #educationSetActiveContextBtn ("Set active"), and verifies both
 *    #educationActiveTopic/#educationActiveCourseId and #educationPlayerContextTopic/#educationPlayerContextCourse update.
 * 3) Switches to Chat Studio, clicks #chatStudyEntryBtn ("Study"), verifies #chatEducationModeStrip binds the
 *    Studio-active topic without a second Pair Tutor button, and runs a real Tutor turn confirming Tutor knows the topic.
 */
import { clickExpect, waitFor } from './lib/runner.mjs';
import { openApp, openTab, send, waitReplyIdle } from './lib/app.mjs';

export default {
  id: 'card-741-fix-phone-chat-header-pill-overlap',
  card: 'CARD-741',
  title: 'Fix phone Chat header pill overlap and retire redundant Pair Tutor button in Education Studio',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const vpName = viewport?.name || 'desktop';
    const suffix = `${vpName}-${Date.now() % 100000}`;
    const projSlug = `proj-pill-${suffix}`;
    const topicName = `Raft Consensus ${vpName}`;

    await j.step('1. Verify #agentSelect and #chatActiveProjectPill do not overlap in Chat top bar on desktop and phone', async () => {
      const createRes = await request.post(`${base}/api/projects`, {
        data: { slug: projSlug, name: projSlug },
      });
      if (!createRes.ok()) {
        throw new Error(`POST /api/projects (${projSlug}) failed: ${createRes.status()}`);
      }

      await openApp(page, base);
      await page.evaluate(() => document.getElementById('tab-chat')?.click());
      await page.locator('#view-chat').waitFor({ state: 'visible', timeout: 15000 });

      const pillReady = await waitFor(
        async () => {
          const vis = await page.locator('#chatActiveProjectPill').isVisible().catch(() => false);
          const txt = await page.locator('#chatActiveProjectName').innerText().catch(() => '');
          return vis && txt.trim() === projSlug;
        },
        { timeoutMs: 15000 },
      );
      if (!pillReady) {
        const txt = await page.locator('#chatActiveProjectName').innerText().catch(() => '');
        throw new Error(`Expected #chatActiveProjectPill visible with '${projSlug}', got '${txt}'`);
      }

      const layout = await page.evaluate(() => {
        const sel = document.getElementById('agentSelect');
        const pill = document.getElementById('chatActiveProjectPill');
        const view = document.getElementById('view-chat');
        if (!sel || !pill || !view) return { missing: true };
        const a = sel.getBoundingClientRect();
        const b = pill.getBoundingClientRect();
        const overlapX = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
        const overlapY = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
        return {
          missing: false,
          overlapArea: overlapX * overlapY,
          overlapX,
          overlapY,
          selRect: { left: Math.round(a.left), right: Math.round(a.right), top: Math.round(a.top), bottom: Math.round(a.bottom) },
          pillRect: { left: Math.round(b.left), right: Math.round(b.right), top: Math.round(b.top), bottom: Math.round(b.bottom) },
          overflow: view.scrollWidth - view.clientWidth,
        };
      });

      if (layout.missing) {
        throw new Error('Expected #agentSelect, #chatActiveProjectPill, and #view-chat in DOM');
      }
      if (layout.overlapArea > 0) {
        throw new Error(
          `#agentSelect (${JSON.stringify(layout.selRect)}) overlaps #chatActiveProjectPill (${JSON.stringify(layout.pillRect)}) by ${layout.overlapX}x${layout.overlapY}px on ${vpName}`,
        );
      }
      if (layout.overflow > 2) {
        throw new Error(`Horizontal overflow in #view-chat on ${vpName}: ${layout.overflow}px`);
      }

      j.note(`Zero overlap between #agentSelect and #chatActiveProjectPill on ${vpName} (sel=${JSON.stringify(layout.selRect)}, pill=${JSON.stringify(layout.pillRect)})`);
    }, { timeoutMs: 35000 });

    await j.step('2. Verify #educationPairTutorBtn is retired in Education Studio and Set active updates Operator and Players context', async () => {
      await openTab(page, 'education');
      await page.locator('#view-education').waitFor({ state: 'visible', timeout: 15000 });

      const pairCount = await page.locator('#educationPairTutorBtn').count();
      if (pairCount !== 0) {
        throw new Error(`Expected #educationPairTutorBtn to be retired (0 in DOM), found ${pairCount}`);
      }

      await page.locator('#educationTopicInput').fill(topicName);
      await clickExpect(
        page.locator('#educationSetActiveContextBtn'),
        async () => {
          const opTopic = (await page.locator('#educationActiveTopic').innerText().catch(() => '')).trim();
          const opCourse = (await page.locator('#educationActiveCourseId').innerText().catch(() => '')).trim();
          const plTopic = (await page.locator('#educationPlayerContextTopic').innerText().catch(() => '')).trim();
          const plCourse = (await page.locator('#educationPlayerContextCourse').innerText().catch(() => '')).trim();
          return (
            opTopic === topicName &&
            opCourse.length > 1 &&
            opCourse !== '-' &&
            plTopic === topicName &&
            plCourse === opCourse
          );
        },
        { label: '#educationSetActiveContextBtn', what: 'Operator and Players topic/course badges to update' },
      );

      const overflow = await page.evaluate(() => {
        const el = document.getElementById('view-education');
        return el ? el.scrollWidth - el.clientWidth : 0;
      });
      if (overflow > 2) {
        throw new Error(`Horizontal overflow in #view-education on ${vpName}: ${overflow}px`);
      }

      j.note(`Education Studio Set active updated both Operator and Players badges to '${topicName}' without #educationPairTutorBtn`);
    }, { timeoutMs: 35000 });

    await j.step('3. Verify Chat Study button binds the Set active topic on Tutor and Tutor answers with the active topic', async () => {
      await page.evaluate(() => document.getElementById('tab-chat')?.click());
      await page.locator('#view-chat').waitFor({ state: 'visible', timeout: 15000 });

      await clickExpect(
        page.locator('#chatStudyEntryBtn'),
        async () => {
          const stripVis = await page.locator('#chatEducationModeStrip').isVisible().catch(() => false);
          const stripTopic = (await page.locator('#chatEducationModeTopic').innerText().catch(() => '')).trim();
          const agentVal = await page.locator('#agentSelect').inputValue().catch(() => '');
          return stripVis && stripTopic === topicName && agentVal === 'tutor';
        },
        { label: '#chatStudyEntryBtn', what: `#chatEducationModeStrip visible with topic '${topicName}' and Tutor selected` },
      );

      await send(page, 'What is the active study topic in my course? Reply in one short sentence without calling tools.');
      await waitReplyIdle(page, { timeoutMs: 180000 });

      const replyOk = await waitFor(
        async () => {
          const txt = await page.locator('#messagesContainer').innerText().catch(() => '');
          return /raft/i.test(txt);
        },
        { timeoutMs: 15000 },
      );
      if (!replyOk) {
        const txt = await page.locator('#messagesContainer').innerText().catch(() => '');
        throw new Error(`Expected Tutor reply to mention Raft Consensus, got: ${txt.slice(0, 600)}`);
      }

      j.note(`Tutor bound active topic '${topicName}' from Set active and answered in Chat`);
    }, { timeoutMs: 210000 });
  },
};
