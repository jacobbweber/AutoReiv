/**
 * CARD-704 journey: Staged RCA self-healing proposals on recurring tool or routine failures.
 * 1) Seed a user Agora skill `qa-rca-math` (`SKILL.md` + `tools/calc_unit_ratio.py`) via
 *    `PUT /api/capabilities/skills/{skill_id}/file` (which passes ToolCheckService with default
 *    `denominator=2` and auto-enables `calc_unit_ratio`), then in Chat ask AutoReiv to open
 *    `qa-rca-math` with `skill_view` and call `calc_unit_ratio(numerator=10, denominator=0)` once
 *    so it raises `ZeroDivisionError` and records a failed tool span.
 * 2) Open Capabilities Studio (`#view-capabilities`) and verify `#capabilitiesRcaProposalsPanel`
 *    is visible with the staged RCA proposal card (`rca:tool:calc_unit_ratio`), failure count,
 *    trace reference (`[data-testid="rca-trace-ref"]`), error detail (`ZeroDivisionError`), and
 *    zero horizontal overflow on desktop and phone.
 * 3) Click "Repair in Chat" (`[data-rca-repair="rca:tool:calc_unit_ratio"]`), verify it opens an
 *    AutoReiv Chat session and dispatches the RCA repair prompt, wait for AutoReiv to repair
 *    `tools/calc_unit_ratio.py` via `write_skill_file`, and verify the repaired tool file handles
 *    `denominator=0` cleanly and the RCA proposal is resolved.
 */
import fs from 'node:fs';
import path from 'node:path';
import { clickExpect, waitFor } from './lib/runner.mjs';
import { getJson, openApp, openTab, send, waitReplyIdle } from './lib/app.mjs';

const AGENT_ID = 'autoreiv';

function resolveDataSkillsDir() {
  const dataDir = process.env.AUTOREIV_DATA_DIR || path.resolve(process.cwd(), 'scratch', 'live_qa_data');
  return path.join(dataDir, 'skills');
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
  id: 'card-704-staged-rca-self-healing-proposals',
  card: 'CARD-704',
  title: 'Staged RCA self-healing proposals surface recurring tool failure evidence with one-click Repair in Chat via write_skill_file',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const suffix = `${viewport.name}`.replace(/[^a-z0-9]/gi, '').toLowerCase();
    const skillId = `qa-rca-${suffix}`;
    const toolName = `calc_ratio_${suffix}`;
    const proposalId = `rca:tool:${toolName}`;
    const skillsRoot = resolveDataSkillsDir();
    fs.rmSync(path.join(skillsRoot, skillId), { recursive: true, force: true });

    try {
      await j.step('Seed user Agora tool and trigger a failing tool call in Chat', async () => {
        const modeRes = await request.put(`${base}/api/settings/approval-mode`, {
          data: { mode: 'balanced' },
        });
        if (!modeRes.ok()) throw new Error(`Set balanced mode -> ${modeRes.status()}`);

        const skillMd = [
          '---',
          `name: QA RCA Skill (${suffix})`,
          `description: Compute ratios with ${toolName}.`,
          '---',
          `# QA RCA Skill (${suffix})`,
          `Use ${toolName}(numerator=..., denominator=...) to compute integer ratios.`,
        ].join('\n');

        const createSkillRes = await request.put(
          `${base}/api/capabilities/skills/${encodeURIComponent(skillId)}/file`,
          { data: { path: 'SKILL.md', content: skillMd } },
        );
        if (!createSkillRes.ok()) {
          throw new Error(`Create SKILL.md -> ${createSkillRes.status()}`);
        }

        const brokenPy = [
          `"""Compute ratio of numerator and denominator."""`,
          'RISK = "read_only"',
          '',
          'def run(numerator: int = 10, denominator: int = 2) -> dict:',
          '    return {"ratio": int(numerator) // int(denominator)}',
        ].join('\n');

        const createToolRes = await request.put(
          `${base}/api/capabilities/skills/${encodeURIComponent(skillId)}/file`,
          { data: { path: `tools/${toolName}.py`, content: brokenPy } },
        );
        if (!createToolRes.ok()) {
          throw new Error(`Create tools/${toolName}.py -> ${createToolRes.status()}`);
        }
        const toolBody = await createToolRes.json();
        if (!toolBody.enabled) {
          throw new Error(`Expected ${toolName} to auto-enable in balanced mode, got: ${JSON.stringify(toolBody)}`);
        }

        await openApp(page, base);
        await ensureChatOpen(page);

        await send(
          page,
          `Step 1: call skill_view with skill_id "${skillId}". ` +
            `Step 2: call ${toolName} with numerator 10 and denominator 0 once. ` +
            `Do NOT call write_skill_file or edit any file on this turn — stop and report the error message only.`,
        );
        await waitReplyIdle(page, { timeoutMs: 180000 });

        const rcaData = await getJson(request, `${base}/api/telemetry/rca-proposals`);
        const staged = (rcaData.proposals || []).find((p) => p.id === proposalId);
        if (!staged) {
          throw new Error(
            `Expected staged RCA proposal ${proposalId} after failing tool call, got: ${JSON.stringify(rcaData)}`,
          );
        }
        if (!String(staged.latest_error || '').includes('ZeroDivisionError')) {
          throw new Error(`Expected ZeroDivisionError in latest_error, got: ${JSON.stringify(staged)}`);
        }
        if (!Array.isArray(staged.trace_ids) || staged.trace_ids.length === 0) {
          throw new Error(`Expected non-empty trace_ids on staged RCA proposal, got: ${JSON.stringify(staged)}`);
        }
        j.note(`Staged RCA proposal ${proposalId} with trace ${staged.trace_ids[0]} and error "${staged.latest_error}"`);
      }, { timeoutMs: 210000 });

      await j.step('Open Capabilities Studio and verify staged RCA proposal card renders with trace reference and Repair in Chat', async () => {
        await openTab(page, 'capabilities');
        await page.locator('#view-capabilities').waitFor({ state: 'visible', timeout: 20000 });
        await page.locator('#capabilitiesRcaProposalsPanel').waitFor({ state: 'visible', timeout: 15000 });

        const cardLoc = page.locator(
          `[data-testid="rca-proposal-card"][data-proposal-id="${proposalId}"]`,
        );
        await cardLoc.waitFor({ state: 'visible', timeout: 15000 });

        const traceText = await cardLoc.locator('[data-testid="rca-trace-ref"]').innerText();
        const errText = await cardLoc.locator('[data-testid="rca-error-detail"]').innerText();
        if (!traceText.includes('trace:') || !errText.includes('ZeroDivisionError')) {
          throw new Error(`Unexpected RCA card text: trace="${traceText}", err="${errText}"`);
        }

        const overflow = await page.evaluate(() => ({
          scrollWidth: document.documentElement.scrollWidth,
          innerWidth: window.innerWidth,
        }));
        if (overflow.scrollWidth > overflow.innerWidth) {
          throw new Error(
            `Horizontal overflow in #view-capabilities on ${viewport.name}: ${overflow.scrollWidth} > ${overflow.innerWidth}`,
          );
        }
        j.note(`RCA proposal card visible in #view-capabilities on ${viewport.name} (${traceText})`);
      });

      await j.step('Click "Repair in Chat" and verify AutoReiv repairs the tool via write_skill_file', async () => {
        const repairBtn = page.locator(`[data-rca-repair="${proposalId}"]`);
        await clickExpect(
          repairBtn,
          async () => page.locator('#promptInput').isVisible().catch(() => false),
          { what: 'click Repair in Chat on RCA proposal', label: `[data-rca-repair="${proposalId}"]` },
        );

        await waitReplyIdle(page, { timeoutMs: 240000 });

        const repaired = await waitFor(
          async () => {
            const fileRes = await getJson(
              request,
              `${base}/api/capabilities/skills/${encodeURIComponent(skillId)}/file?path=${encodeURIComponent(`tools/${toolName}.py`)}`,
            );
            const content = String(fileRes?.content || '');
            return content.includes('def run') && (content.includes('== 0') || content.includes('ZeroDivisionError') || content.includes('not denominator'));
          },
          { timeoutMs: 15000, intervalMs: 500 },
        );
        if (!repaired) {
          const fileRes = await getJson(
            request,
            `${base}/api/capabilities/skills/${encodeURIComponent(skillId)}/file?path=${encodeURIComponent(`tools/${toolName}.py`)}`,
          );
          throw new Error(`Expected AutoReiv to repair tools/${toolName}.py via write_skill_file, current content:\n${fileRes?.content}`);
        }

        const rcaAfter = await getJson(request, `${base}/api/telemetry/rca-proposals`);
        const stillStaged = (rcaAfter.proposals || []).find((p) => p.id === proposalId);
        if (stillStaged) {
          throw new Error(`Expected ${proposalId} to be resolved after write_skill_file repair, got: ${JSON.stringify(stillStaged)}`);
        }
        j.note(`AutoReiv repaired ${skillId}/tools/${toolName}.py via write_skill_file and resolved ${proposalId}`);
      }, { timeoutMs: 260000 });
    } finally {
      fs.rmSync(path.join(skillsRoot, skillId), { recursive: true, force: true });
    }
  },
};
