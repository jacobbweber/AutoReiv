/**
 * CARD-733 journey: Remember approved cli_exec commands for the active project.
 * 1) Select a project and ask AutoReiv to run `cli_exec(command="echo card733_check_ok")`; click "Approve & remember for project".
 * 2) Ask AutoReiv to run the same `cli_exec` command again; verify it runs with zero approval prompt.
 * 3) Open Projects Studio -> Projects Manager, verify the remembered command is listed, click Remove, and verify it is revoked.
 */
import { clickExpect, waitFor } from './lib/runner.mjs';
import {
  HITL_CARD,
  freshProjectDir,
  getJson,
  isStreaming,
  openApp,
  openTab,
  send,
  trackStreams,
  waitReplyIdle,
} from './lib/app.mjs';

const isHidden = (loc) => loc.evaluate((el) => el.classList.contains('hidden')).catch(() => true);

export default {
  id: 'card-733-remember-approved-cli-exec',
  card: 'CARD-733',
  title: 'Remember approved cli_exec commands per project and revoke from Projects Studio',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const slug = `proj-733-${viewport.name}`.replace(/[^a-z0-9-]/gi, '').toLowerCase();
    const cmd = 'echo card733_check_ok';
    const streams = trackStreams(page);

    await freshProjectDir(request, base, slug);
    const selRes = await request.put(`${base}/api/projects/selected`, { data: { slug } });
    if (!selRes.ok()) throw new Error(`PUT /api/projects/selected -> ${selRes.status()}`);

    try {
      await j.step('First cli_exec parks with Approve & remember for project button; clicking it remembers the command', async () => {
        await openApp(page, base);
        await openTab(page, 'chat');
        await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 15000 });
        if (await page.locator('#newSessionBtn').isVisible().catch(() => false)) {
          await page.locator('#newSessionBtn').click();
          await page.waitForTimeout(400);
        }

        const n = streams.count;
        await send(
          page,
          `First call skill_view(skill_id="software-development"), then call cli_exec(command="${cmd}") in the active project. Do not call any other tools.`,
        );
        await waitFor(() => streams.count > n, { timeoutMs: 20000, label: 'first stream started' });

        const rememberBtn = page
          .locator(`${HITL_CARD} [data-hitl-remember="project"], #messagesContainer [data-approval-id] [data-hitl-remember="project"]`)
          .first();
        await waitFor(() => rememberBtn.isVisible().catch(() => false), {
          timeoutMs: 180000,
          intervalMs: 1000,
          label: 'cli_exec HITL card with Approve & remember for project button',
        });

        await rememberBtn.click();
        await waitReplyIdle(page, { timeoutMs: 120000 });

        const approved = await getJson(request, `${base}/api/projects/approved-commands`);
        if (approved.slug !== slug || !Array.isArray(approved.commands) || !approved.commands.includes(cmd)) {
          throw new Error(`Expected ${cmd} in approved commands for ${slug}, got ${JSON.stringify(approved)}`);
        }
        j.note(`Remembered "${cmd}" for ${slug}`);
      }, { timeoutMs: 240000 });

      await j.step('Second run of the same cli_exec command in the active project executes with zero approval prompt', async () => {
        const n = streams.count;
        await send(
          page,
          `Now call cli_exec(command="${cmd}") one more time and report the output.`,
        );
        await waitFor(() => streams.count > n, { timeoutMs: 20000, label: 'second stream started' });

        let sawHitl = false;
        await waitFor(
          async () => {
            const visibleBtn = page.locator(
              `${HITL_CARD} [data-hitl-decision="APPROVED"], #messagesContainer [data-approval-id] [data-hitl-decision="APPROVED"]:not([disabled])`,
            );
            if ((await visibleBtn.count()) > 0 && (await visibleBtn.first().isVisible().catch(() => false))) {
              sawHitl = true;
              return true;
            }
            return !(await isStreaming(page));
          },
          { timeoutMs: 120000, intervalMs: 1000, label: 'second cli_exec turn finishes without parking' },
        );
        await waitReplyIdle(page, { timeoutMs: 60000 });
        if (sawHitl) {
          throw new Error('Second run of remembered cli_exec command unexpectedly parked for approval');
        }
      }, { timeoutMs: 240000 });

      await j.step('Projects Studio lists the remembered command and Remove revokes it', async () => {
        await openTab(page, 'projects');
        await clickExpect(
          page.locator('#projectsModeManagerBtn'),
          async () => !(await isHidden(page.locator('#projectsManagerView'))),
          { label: 'Switch to Projects Manager', timeoutMs: 10000 },
        );

        const revokeBtn = page.locator(`#projectsApprovedCommandsList button[data-revoke-command="${cmd}"]`);
        await waitFor(() => revokeBtn.isVisible().catch(() => false), {
          timeoutMs: 15000,
          label: 'Projects Manager shows remembered command with Remove button',
        });

        await clickExpect(
          revokeBtn,
          async () => (await revokeBtn.count()) === 0,
          { label: 'Remove remembered command', timeoutMs: 15000 },
        );

        const afterRevoke = await getJson(request, `${base}/api/projects/approved-commands`);
        if ((afterRevoke.commands || []).includes(cmd)) {
          throw new Error(`Command "${cmd}" still present after Remove: ${JSON.stringify(afterRevoke)}`);
        }

        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
        );
        if (overflow > 2) throw new Error(`Horizontal overflow on ${viewport.name}: ${overflow}px`);
      });
    } finally {
      await request.put(`${base}/api/projects/selected`, { data: {} }).catch(() => {});
      await request.delete(`${base}/api/projects/${encodeURIComponent(slug)}?confirm=true`).catch(() => {});
    }
  },
};
