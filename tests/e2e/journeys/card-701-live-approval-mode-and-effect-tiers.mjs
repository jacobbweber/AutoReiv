/**
 * CARD-701 journey: Live ApprovalMode in Settings UI with read_only, state_change, and destructive tool effect tiers.
 * 1) Opens Settings Studio (#dock-settings -> #view-settings) and verifies #settingsApprovalModeCard,
 *    #approvalModeSelect, and #approvalModeSaveBtn render with the default "balanced" mode.
 * 2) Switches ApprovalMode in the live Settings Studio UI to "strict", "balanced", and "hands_off"
 *    without restarting the server, verifying each mode's live enforcement across read_only,
 *    state_change, and destructive tool authoring via /api/capabilities/skills/{id}/file.
 * 3) Restores "balanced" mode and verifies zero horizontal overflow on desktop and phone.
 */
import { waitFor } from './lib/runner.mjs';
import { getJson, openApp, openTab } from './lib/app.mjs';

const SKILL_MD = `---
name: qa-701-approval-skill
description: QA skill for live ApprovalMode and effect tier verification.
version: 1.0.0
tools: []
---
# QA 701 Approval Skill
Used by the CARD-701 live journey to test strict, balanced, and hands_off tool authoring.
`;

const READ_ONLY_CODE = (fnSuffix) => `"""Pure read-only helper ${fnSuffix}."""
RISK = "read_only"

def run(x: int = 3) -> dict:
    return {"value": x * 2, "tag": "${fnSuffix}"}
`;

const STATE_CHANGE_CODE = (fnSuffix) => `"""State-changing helper ${fnSuffix} that imports urllib."""
import urllib.parse

RISK = "write"

def run(path: str = "notes/demo") -> dict:
    return {"encoded": urllib.parse.quote(path), "tag": "${fnSuffix}"}
`;

const DESTRUCTIVE_CODE = (fnSuffix) => `"""Destructive helper ${fnSuffix}."""
RISK = "destructive"

def run(target: str = "scratch_item") -> dict:
    return {"deleted": target, "tag": "${fnSuffix}"}
`;

export default {
  id: 'card-701-live-approval-mode-and-effect-tiers',
  card: 'CARD-701',
  title: 'Settings Studio live ApprovalMode selector enforces strict, balanced, and hands_off across read_only, state_change, and destructive tools without restart',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const skillId = `qa-701-${viewport.name}-${Date.now() % 100000}`;

    await j.step('Open Settings Studio and verify Tool Approval Mode card is visible', async () => {
      // Ensure clean default mode before opening UI
      const resetRes = await request.put(`${base}/api/settings/approval-mode`, {
        data: { mode: 'balanced' },
      });
      if (!resetRes.ok()) throw new Error(`PUT /api/settings/approval-mode -> ${resetRes.status()}`);

      // Create the test skill SKILL.md
      const skillRes = await request.put(
        `${base}/api/capabilities/skills/${encodeURIComponent(skillId)}/file`,
        { data: { path: 'SKILL.md', content: SKILL_MD } },
      );
      if (!skillRes.ok()) throw new Error(`Create SKILL.md -> ${skillRes.status()}`);

      await openApp(page, base);
      await openTab(page, 'settings');
      await page.locator('#settingsApprovalModeCard').waitFor({ state: 'visible', timeout: 15000 });
      await page.locator('#approvalModeSelect').waitFor({ state: 'visible', timeout: 10000 });
      await page.locator('#approvalModeSaveBtn').waitFor({ state: 'visible', timeout: 10000 });

      const loadedBalanced = await waitFor(
        async () => (await page.locator('#approvalModeSelect').inputValue()) === 'balanced',
        { timeoutMs: 10000, intervalMs: 250 },
      );
      if (!loadedBalanced) {
        throw new Error(
          `Expected #approvalModeSelect to start on "balanced", got "${await page.locator('#approvalModeSelect').inputValue()}"`,
        );
      }
      j.note(`Settings Studio Approval Mode card visible on ${viewport.name}`);
    });

    await j.step('Switch to Strict mode in Settings UI and verify read_only tools save disabled', async () => {
      await page.locator('#approvalModeSelect').selectOption('strict');
      await page.locator('#approvalModeSaveBtn').click();

      const savedStrict = await waitFor(
        async () => {
          const text = await page.locator('#approvalModeStatus').innerText().catch(() => '');
          return text.includes('strict');
        },
        { timeoutMs: 10000, intervalMs: 250 },
      );
      if (!savedStrict) {
        throw new Error('Expected #approvalModeStatus to confirm saving strict mode');
      }

      const apiCheck = await getJson(request, `${base}/api/settings/approval-mode`);
      if (apiCheck.approval_mode !== 'strict') {
        throw new Error(`Expected API approval_mode="strict", got ${JSON.stringify(apiCheck)}`);
      }

      const res = await request.put(
        `${base}/api/capabilities/skills/${encodeURIComponent(skillId)}/file`,
        {
          data: {
            path: 'tools/ro_strict_tool.py',
            content: READ_ONLY_CODE('strict'),
          },
        },
      );
      if (!res.ok()) throw new Error(`author ro_strict_tool -> ${res.status()}`);
      const body = await res.json();
      if (body.effect !== 'read_only' || body.approval_mode !== 'strict' || body.auto_enabled !== false) {
        throw new Error(`Strict mode should hold read_only tool disabled, got: ${JSON.stringify(body)}`);
      }
      j.note('Strict mode held read_only tool disabled for operator review');
    });

    await j.step('Switch to Balanced mode in Settings UI and verify read_only auto-mounts while state_change saves disabled', async () => {
      await page.locator('#approvalModeSelect').selectOption('balanced');
      await page.locator('#approvalModeSaveBtn').click();

      const savedBalanced = await waitFor(
        async () => {
          const text = await page.locator('#approvalModeStatus').innerText().catch(() => '');
          return text.includes('balanced');
        },
        { timeoutMs: 10000, intervalMs: 250 },
      );
      if (!savedBalanced) {
        throw new Error('Expected #approvalModeStatus to confirm saving balanced mode');
      }

      const roRes = await request.put(
        `${base}/api/capabilities/skills/${encodeURIComponent(skillId)}/file`,
        {
          data: {
            path: 'tools/ro_balanced_tool.py',
            content: READ_ONLY_CODE('balanced'),
          },
        },
      );
      if (!roRes.ok()) throw new Error(`author ro_balanced_tool -> ${roRes.status()}`);
      const roBody = await roRes.json();
      if (roBody.effect !== 'read_only' || roBody.approval_mode !== 'balanced' || roBody.auto_enabled !== true) {
        throw new Error(`Balanced mode should auto-enable read_only tool, got: ${JSON.stringify(roBody)}`);
      }

      const scRes = await request.put(
        `${base}/api/capabilities/skills/${encodeURIComponent(skillId)}/file`,
        {
          data: {
            path: 'tools/sc_balanced_tool.py',
            content: STATE_CHANGE_CODE('balanced'),
          },
        },
      );
      if (!scRes.ok()) throw new Error(`author sc_balanced_tool -> ${scRes.status()}`);
      const scBody = await scRes.json();
      if (scBody.effect !== 'state_change' || scBody.approval_mode !== 'balanced' || scBody.auto_enabled !== false) {
        throw new Error(`Balanced mode should hold state_change tool disabled, got: ${JSON.stringify(scBody)}`);
      }
      j.note('Balanced mode auto-enabled read_only tool and held state_change tool disabled');
    });

    await j.step('Switch to Hands-off mode in Settings UI and verify state_change auto-mounts while destructive stays gated', async () => {
      await page.locator('#approvalModeSelect').selectOption('hands_off');
      await page.locator('#approvalModeSaveBtn').click();

      const savedHandsOff = await waitFor(
        async () => {
          const text = await page.locator('#approvalModeStatus').innerText().catch(() => '');
          return text.includes('hands_off');
        },
        { timeoutMs: 10000, intervalMs: 250 },
      );
      if (!savedHandsOff) {
        throw new Error('Expected #approvalModeStatus to confirm saving hands_off mode');
      }

      const scRes = await request.put(
        `${base}/api/capabilities/skills/${encodeURIComponent(skillId)}/file`,
        {
          data: {
            path: 'tools/sc_handsoff_tool.py',
            content: STATE_CHANGE_CODE('hands_off'),
          },
        },
      );
      if (!scRes.ok()) throw new Error(`author sc_handsoff_tool -> ${scRes.status()}`);
      const scBody = await scRes.json();
      if (scBody.effect !== 'state_change' || scBody.approval_mode !== 'hands_off' || scBody.auto_enabled !== true) {
        throw new Error(`Hands-off mode should auto-enable state_change tool, got: ${JSON.stringify(scBody)}`);
      }

      const destrRes = await request.put(
        `${base}/api/capabilities/skills/${encodeURIComponent(skillId)}/file`,
        {
          data: {
            path: 'tools/destr_handsoff_tool.py',
            content: DESTRUCTIVE_CODE('hands_off'),
          },
        },
      );
      if (!destrRes.ok()) throw new Error(`author destr_handsoff_tool -> ${destrRes.status()}`);
      const destrBody = await destrRes.json();
      if (destrBody.effect !== 'destructive' || destrBody.approval_mode !== 'hands_off' || destrBody.auto_enabled !== false) {
        throw new Error(`Hands-off mode must keep destructive tool disabled, got: ${JSON.stringify(destrBody)}`);
      }

      // Restore balanced mode via UI and check layout overflow
      await page.locator('#approvalModeSelect').selectOption('balanced');
      await page.locator('#approvalModeSaveBtn').click();
      await waitFor(
        async () => (await page.locator('#approvalModeStatus').innerText().catch(() => '')).includes('balanced'),
        { timeoutMs: 10000, intervalMs: 250 },
      );

      const overflow = await page.evaluate(() => {
        const doc = document.documentElement;
        return doc.scrollWidth - doc.clientWidth;
      });
      if (overflow > 2) {
        throw new Error(`Horizontal overflow detected on ${viewport.name}: ${overflow}px`);
      }
      j.note(`Hands-off mode auto-enabled state_change tool, gated destructive tool, and passed layout check on ${viewport.name}`);
    });
  },
};
