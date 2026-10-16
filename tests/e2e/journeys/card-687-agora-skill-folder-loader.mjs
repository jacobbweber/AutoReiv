/**
 * CARD-687 journey: Agora skill folder loader for colocated tools and references.
 * 1) Seed a user Agora skill folder (`agora-checksum`) with `SKILL.md`, `references/guide.md`, and `tools/calc_checksum.py`.
 * 2) Verify `GET /api/capabilities/tree` and `GET /api/capabilities/skills/agora-checksum/file` return the Agora folder tree,
 *    inferred JSON Schema parameters from `def run(...)`, and reference file contents.
 * 3) Enable `calc_checksum` via `POST /api/capabilities/skills/agora-checksum/tools/calc_checksum/toggle`, tick `agora-checksum`
 *    on Architect in Agent Studio, and verify the tool appears in the agent's allowed tools.
 * 4) Disable `calc_checksum` and restore Architect's skill list.
 */
import fs from 'node:fs';
import path from 'node:path';
import { waitFor, clickExpect } from './lib/runner.mjs';
import { getJson, openApp } from './lib/app.mjs';

const SKILL_ID = 'agora-checksum';
const TOOL_NAME = 'calc_checksum';
const AGENT_ID = 'architect';

function resolveDataSkillsDir() {
  const dataDir = process.env.AUTOREIV_DATA_DIR || path.resolve(process.cwd(), 'scratch', 'live_qa_data');
  return path.join(dataDir, 'skills');
}

export default {
  id: 'card-687-agora-skill-folder-loader',
  card: 'CARD-687',
  title: 'Agora skill folder: AST-inferred colocated tools, references, and capabilities tree',
  allow: [],
  async run(j, { page, request, base }) {
    const skillsRoot = resolveDataSkillsDir();
    const skillDir = path.join(skillsRoot, SKILL_ID);
    const refsDir = path.join(skillDir, 'references');
    const toolsDir = path.join(skillDir, 'tools');

    await j.step('Seed an Agora skill folder on disk and verify /api/capabilities/tree infers schema via AST', async () => {
      fs.mkdirSync(refsDir, { recursive: true });
      fs.mkdirSync(toolsDir, { recursive: true });
      fs.writeFileSync(
        path.join(skillDir, 'SKILL.md'),
        [
          '---',
          'name: Agora Checksum Kit',
          'description: Compute deterministic checksums and inspect format guides.',
          '---',
          '# Agora Checksum Kit',
          'Use `calc_checksum` and read `references/guide.md`.',
          '',
        ].join('\n'),
        'utf-8'
      );
      fs.writeFileSync(
        path.join(refsDir, 'guide.md'),
        '# Checksum Reference Guide\nAlways strip trailing newlines before computing byte sums.\n',
        'utf-8'
      );
      fs.writeFileSync(
        path.join(toolsDir, `${TOOL_NAME}.py`),
        [
          '"""Compute a byte-sum checksum for a text string."""',
          'RISK = "read_only"',
          '',
          'def run(text: str, modulo: int = 65535) -> dict:',
          '    return {"checksum": sum(text.encode("utf-8")) % int(modulo), "length": len(text)}',
          '',
        ].join('\n'),
        'utf-8'
      );

      await openApp(page, base);
      const tree = await getJson(request, `${base}/api/capabilities/tree`);
      const entry = (tree.skills || []).find((s) => s.id === SKILL_ID);
      if (!entry) throw new Error(`Skill ${SKILL_ID} missing from /api/capabilities/tree`);
      if (!entry.references || !entry.references.some((r) => r.name === 'guide.md')) {
        throw new Error(`references/guide.md missing from tree: ${JSON.stringify(entry.references)}`);
      }
      const toolSpec = (entry.colocated_tools || []).find((t) => t.name === TOOL_NAME);
      if (!toolSpec) throw new Error(`Colocated tool ${TOOL_NAME} missing from tree`);
      if (toolSpec.enabled !== false || toolSpec.approval !== 'disabled') {
        throw new Error(`Unapproved user tool should start disabled, got: ${JSON.stringify(toolSpec)}`);
      }
      const reqParams = (toolSpec.parameters && toolSpec.parameters.required) || [];
      if (!reqParams.includes('text')) {
        throw new Error(`Expected 'text' in inferred required parameters, got: ${JSON.stringify(toolSpec.parameters)}`);
      }
      const refFile = await getJson(
        request,
        `${base}/api/capabilities/skills/${SKILL_ID}/file?path=${encodeURIComponent('references/guide.md')}`
      );
      if (!refFile.content || !refFile.content.includes('Checksum Reference Guide')) {
        throw new Error('Failed to read references/guide.md via capabilities file endpoint');
      }
      j.note(`Tree verified for ${SKILL_ID}: files=${entry.files.join(', ')}; tool=${toolSpec.name} (${toolSpec.approval})`);
    });

    await j.step('Enable colocated tool via toggle API and verify it mounts into Agent Studio skill list', async () => {
      const toggleRes = await request.post(
        `${base}/api/capabilities/skills/${SKILL_ID}/tools/${TOOL_NAME}/toggle`,
        { data: { enabled: true } }
      );
      if (!toggleRes.ok()) throw new Error(`Toggle enable failed: ${toggleRes.status()}`);
      const toggled = await toggleRes.json();
      if (!toggled.enabled || !toggled.mounted) {
        throw new Error(`Expected tool to be enabled and mounted, got: ${JSON.stringify(toggled)}`);
      }

      if (!(await page.locator('#forgeAgentSelect').isVisible().catch(() => false))) {
        await page.locator('#dock-agents').click();
      }
      await page.locator('#forgeAgentSelect').waitFor({ state: 'visible', timeout: 20000 });
      await waitFor(
        async () => (await page.locator(`#forgeAgentSelect option[value="${AGENT_ID}"]`).count()) > 0,
        { timeoutMs: 20000 }
      );
      await page.selectOption('#forgeAgentSelect', AGENT_ID);
      await waitFor(
        async () => /architect/i.test(await page.inputValue('#forgeNameInput').catch(() => '')),
        { timeoutMs: 20000 }
      );
      const caps = page.locator('details[data-section="capabilities"]');
      await waitFor(async () => (await caps.getAttribute('aria-busy').catch(() => 'true')) !== 'true', { timeoutMs: 20000 });
      if (!(await caps.evaluate((el) => el.open).catch(() => true))) {
        await caps.locator('summary').first().click();
      }
      const ok = await waitFor(
        async () => (await page.locator(`.forge-skill-row[data-skill-id="${SKILL_ID}"]`).count()) > 0,
        { timeoutMs: 20000 }
      );
      if (!ok) throw new Error(`Skill row ${SKILL_ID} did not render in Agent Studio`);
      await page.waitForTimeout(800);

      const pill = page.locator(`.forge-skill-pill[data-skill-id="${SKILL_ID}"]`).first();
      await pill.scrollIntoViewIfNeeded();
      await pill.click();
      await waitFor(
        async () => (await page.locator(`[data-skill-group-list="enabled"] .forge-skill-row[data-skill-id="${SKILL_ID}"]`).count()) > 0,
        { timeoutMs: 5000 }
      );
      await page.locator('#saveAgentBtn').scrollIntoViewIfNeeded().catch(() => {});
      await clickExpect(
        page.locator('#saveAgentBtn'),
        async () => {
          const ag = await getJson(request, `${base}/api/agents/${AGENT_ID}`);
          const skills = Array.isArray(ag.allowed_skill) ? ag.allowed_skill : [];
          const tools = Array.isArray(ag.allowed_tools) ? ag.allowed_tools : [];
          return skills.includes(SKILL_ID) && tools.includes(TOOL_NAME);
        },
        { label: 'Save Profile', what: `${TOOL_NAME} granted via ${SKILL_ID}`, timeoutMs: 20000 }
      );
      j.note(`Architect granted colocated tool ${TOOL_NAME} through Agora skill ${SKILL_ID}`);
    });

    await j.step('Clean up: untick skill on Architect and disable colocated tool', async () => {
      await page.waitForTimeout(800);
      const pill = page.locator(`.forge-skill-pill[data-skill-id="${SKILL_ID}"]`).first();
      await pill.waitFor({ state: 'visible', timeout: 10000 });
      await pill.scrollIntoViewIfNeeded();
      await pill.click();
      await waitFor(
        async () => (await page.locator(`[data-skill-group-list="available"] .forge-skill-row[data-skill-id="${SKILL_ID}"]`).count()) > 0,
        { timeoutMs: 5000 }
      );
      await page.locator('#saveAgentBtn').scrollIntoViewIfNeeded().catch(() => {});
      await clickExpect(
        page.locator('#saveAgentBtn'),
        async () => {
          const ag = await getJson(request, `${base}/api/agents/${AGENT_ID}`);
          return !(ag.allowed_skill || []).includes(SKILL_ID);
        },
        { label: 'Save Profile', what: `${SKILL_ID} unticked`, timeoutMs: 20000 }
      );
      const offRes = await request.post(
        `${base}/api/capabilities/skills/${SKILL_ID}/tools/${TOOL_NAME}/toggle`,
        { data: { enabled: false } }
      );
      if (!offRes.ok()) throw new Error(`Toggle disable failed: ${offRes.status()}`);
      fs.rmSync(skillDir, { recursive: true, force: true });
    });
  },
};
