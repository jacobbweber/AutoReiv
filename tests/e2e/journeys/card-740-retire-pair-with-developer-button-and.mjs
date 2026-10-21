/**
 * CARD-740 journey: Retire Pair with Developer button and keep Set Active as single project lever.
 * 1) Opens Projects Studio, verifies #projectsPairDeveloperBtn is absent from the DOM, creates two projects,
 *    switches to Projects Manager (#projectsModeManagerBtn), clicks "Set as Active" on the first project,
 *    and verifies #projectsActiveName and #projectsActiveBadge update with zero horizontal overflow.
 * 2) Switches to Chat Studio, verifies #chatActiveProjectPill is visible with the active project slug and
 *    #promptInput is empty, and clicks #chatActiveProjectPill to verify round-trip navigation back to Projects Studio.
 * 3) Switches to Chat Studio and runs a real AutoReiv turn calling list_project_dir(path=".") to verify
 *    Set Active alone pins the active project for AutoReiv's system prompt and tools.
 */
import fs from 'node:fs';
import path from 'node:path';
import { clickExpect, waitFor } from './lib/runner.mjs';
import { getJson, openApp, openTab, send, waitReplyIdle } from './lib/app.mjs';

export default {
  id: 'card-740-retire-pair-with-developer-button-and',
  card: 'CARD-740',
  title: 'Retire Pair with Developer button and keep Set Active as single project lever',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const suffix = `${viewport?.name || 'desktop'}-${Date.now() % 100000}`;
    const slugA = `proj-alpha-${suffix}`;
    const slugB = `proj-beta-${suffix}`;

    await j.step('1. Create two projects, verify #projectsPairDeveloperBtn is retired, and click Set as Active in Projects Manager', async () => {
      const resA = await request.post(`${base}/api/projects`, {
        data: { slug: slugA, name: slugA },
      });
      if (!resA.ok()) throw new Error(`POST /api/projects (${slugA}) failed: ${resA.status()}`);
      const createdA = await resA.json();
      fs.writeFileSync(path.join(createdA.path, 'ALPHA_MARKER.md'), `# ${slugA}\n`);

      const resB = await request.post(`${base}/api/projects`, {
        data: { slug: slugB, name: slugB },
      });
      if (!resB.ok()) throw new Error(`POST /api/projects (${slugB}) failed: ${resB.status()}`);

      await openApp(page, base);
      await openTab(page, 'projects');
      await page.locator('#view-projects').waitFor({ state: 'visible', timeout: 15000 });

      const pairBtnCount = await page.locator('#projectsPairDeveloperBtn').count();
      if (pairBtnCount !== 0) {
        throw new Error(`Expected #projectsPairDeveloperBtn to be retired (0 in DOM), found ${pairBtnCount}`);
      }

      // Switch to Projects Manager and click "Set as Active" on slugA
      await clickExpect(
        page.locator('#projectsModeManagerBtn'),
        async () => page.locator('#projectsManagerView').isVisible().catch(() => false),
        { label: '#projectsModeManagerBtn', what: '#projectsManagerView to become visible' },
      );

      const setActiveBtn = page.locator(`#projectsList button[data-act="set-active"][data-slug="${slugA}"]`);
      await setActiveBtn.waitFor({ state: 'visible', timeout: 15000 });
      await clickExpect(
        setActiveBtn,
        async () => {
          const activeText = await page.locator('#projectsActiveName').innerText().catch(() => '');
          return activeText.trim() === slugA;
        },
        { label: `Set as Active (${slugA})`, what: `#projectsActiveName to equal ${slugA}` },
      );

      const badgeVisible = await page.locator('#projectsActiveBadge').isVisible().catch(() => false);
      if (!badgeVisible) {
        throw new Error('Expected #projectsActiveBadge to be visible when project is active');
      }

      if ((await page.locator('#projectsPairDeveloperBtn').count()) !== 0) {
        throw new Error('Expected #projectsPairDeveloperBtn to remain absent after Set Active');
      }

      const overflow = await page.evaluate(() => {
        const el = document.getElementById('view-projects');
        return el ? el.scrollWidth - el.clientWidth : 0;
      });
      if (overflow > 2) {
        throw new Error(`Horizontal overflow in #view-projects on ${viewport?.name}: ${overflow}px`);
      }

      j.note(`Set Active switched active project to ${slugA} without #projectsPairDeveloperBtn`);
    }, { timeoutMs: 40000 });

    await j.step('2. Verify #chatActiveProjectPill in Chat Studio reflects Set Active and round-trips to Projects Studio', async () => {
      await openTab(page, 'chat');
      await page.locator('#view-chat').waitFor({ state: 'visible', timeout: 15000 });

      const pillReady = await waitFor(
        async () => {
          const vis = await page.locator('#chatActiveProjectPill').isVisible().catch(() => false);
          const txt = await page.locator('#chatActiveProjectName').innerText().catch(() => '');
          return vis && txt.trim() === slugA;
        },
        { timeoutMs: 15000 },
      );
      if (!pillReady) {
        const txt = await page.locator('#chatActiveProjectName').innerText().catch(() => '');
        throw new Error(`Expected #chatActiveProjectPill visible with '${slugA}', got '${txt}'`);
      }

      const composerVal = await page.locator('#promptInput').inputValue();
      if (composerVal.trim() !== '') {
        throw new Error(`Expected empty #promptInput without legacy pairing text, got: '${composerVal}'`);
      }

      await clickExpect(
        page.locator('#chatActiveProjectPill'),
        async () => page.locator('#view-projects').isVisible().catch(() => false),
        { label: '#chatActiveProjectPill', what: 'navigation to #view-projects' },
      );

      j.note(`#chatActiveProjectPill displayed ${slugA} and navigated to #view-projects`);
    }, { timeoutMs: 30000 });

    await j.step('3. Verify AutoReiv in Chat Studio already knows the active project from Set Active', async () => {
      await openTab(page, 'chat');
      await page.locator('#view-chat').waitFor({ state: 'visible', timeout: 15000 });

      await send(
        page,
        'Call list_project_dir with path="." right now and tell me the markdown file name in the active project.',
      );
      await waitReplyIdle(page, { timeoutMs: 180000 });

      const sessions = await getJson(request, `${base}/api/chat/sessions?agent_id=autoreiv`);
      const latest = Array.isArray(sessions) && sessions.length ? sessions[0] : null;
      if (!latest || !latest.id) {
        throw new Error(`Expected an active autoreiv chat session, got: ${JSON.stringify(sessions)}`);
      }
      const messages = await getJson(request, `${base}/api/chat/sessions/${encodeURIComponent(latest.id)}/messages`);
      const serialized = JSON.stringify(messages);
      if (!serialized.includes('ALPHA_MARKER.md')) {
        throw new Error(`Expected AutoReiv turn to see ALPHA_MARKER.md in active project ${slugA}, got: ${serialized.slice(0, 600)}`);
      }

      j.note(`AutoReiv listed ALPHA_MARKER.md in active project ${slugA} via Set Active alone`);
    }, { timeoutMs: 210000 });
  },
};
