/**
 * CARD-690 journey: Unified Capabilities directory tree studio (ADR-0065 Slice 4).
 * 1) Seed an Agora skill folder `agora-tree-demo` (`SKILL.md`, `references/arch.md`,
 *    pure `tools/format_tag.py`, and network-flagged `tools/ping_endpoint.py`).
 * 2) Open Capabilities Studio (`#dock-capabilities`), verify `#view-capabilities` is visible
 *    with zero horizontal overflow (`scrollWidth <= innerWidth`).
 * 3) Filter `#capabilitiesTreeSearch` for `agora-tree-demo` and verify the Agora folder node
 *    shows `SKILL.md`, `references/arch.md`, `tools/format_tag.py` (`Enabled`), and
 *    `tools/ping_endpoint.py` (`Needs approval`).
 * 4) Select `references/arch.md`, edit in `#capabilitiesFileEditor`, click `#capabilitiesSaveFileBtn`,
 *    and verify the updated content persists via `GET /api/capabilities/skills/agora-tree-demo/file`.
 * 5) Select `tools/ping_endpoint.py`, verify `#capabilitiesToolStatusCard` shows `Disabled (needs approval)`
 *    and `access: network`, click `#capabilitiesToggleToolBtn` to enable it, and verify the status updates
 *    to `Enabled` and `GET /api/capabilities/tree` reports `enabled: true`.
 */
import fs from 'node:fs';
import path from 'node:path';
import { clickExpect, waitFor } from './lib/runner.mjs';
import { getJson, openApp } from './lib/app.mjs';

const SKILL_ID = 'agora-tree-demo';

function resolveDataSkillsDir() {
  const dataDir = process.env.AUTOREIV_DATA_DIR || path.resolve(process.cwd(), 'scratch', 'live_qa_data');
  return path.join(dataDir, 'skills');
}

export default {
  id: 'card-690-unified-capabilities-directory-tree-studio',
  card: 'CARD-690',
  title: 'Unified Capabilities directory tree studio',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const skillsRoot = resolveDataSkillsDir();
    const marker = `agora-tree-${viewport.name}-${Date.now() % 100000}`;

    await j.step('Seed Agora skill folder agora-tree-demo with SKILL.md, references/arch.md, and two tools', async () => {
      await openApp(page, base);

      const r1 = await request.put(`${base}/api/capabilities/skills/${SKILL_ID}/file`, {
        data: {
          path: 'SKILL.md',
          content: [
            '---',
            'name: Agora Tree Demo',
            'description: Demo skill folder for the Capabilities tree studio.',
            'tools: []',
            '---',
            '# Agora Tree Demo',
            'Use format_tag or ping_endpoint.',
            '',
          ].join('\n'),
        },
      });
      if (!r1.ok()) throw new Error(`Failed to write SKILL.md: ${r1.status()}`);

      const r2 = await request.put(`${base}/api/capabilities/skills/${SKILL_ID}/file`, {
        data: {
          path: 'references/arch.md',
          content: '# Architecture Guide\n\nInitial reference note.\n',
        },
      });
      if (!r2.ok()) throw new Error(`Failed to write references/arch.md: ${r2.status()}`);

      const r3 = await request.put(`${base}/api/capabilities/skills/${SKILL_ID}/file`, {
        data: {
          path: 'tools/format_tag.py',
          content: [
            '"""Format a tag label."""',
            'RISK = "read_only"',
            '',
            'def run(tag: str = "v1") -> dict:',
            '    return {"formatted": f"[{tag}]"}',
            '',
          ].join('\n'),
        },
      });
      if (!r3.ok()) throw new Error(`Failed to write tools/format_tag.py: ${r3.status()}`);

      const r4 = await request.put(`${base}/api/capabilities/skills/${SKILL_ID}/file`, {
        data: {
          path: 'tools/ping_endpoint.py',
          content: [
            '"""Ping a remote endpoint over network."""',
            'import urllib.request',
            '',
            'def run(url: str = "https://example.com") -> dict:',
            '    return {"url": url}',
            '',
          ].join('\n'),
        },
      });
      if (!r4.ok()) throw new Error(`Failed to write tools/ping_endpoint.py: ${r4.status()}`);
    });

    await j.step('Open Capabilities Studio and verify Agora tree layout and zero horizontal overflow', async () => {
      if (!(await page.locator('#view-capabilities').isVisible().catch(() => false))) {
        const dockBtn = page.locator('#dock-capabilities');
        if (await dockBtn.isVisible().catch(() => false)) {
          await dockBtn.click();
        } else {
          await page.locator('#tab-capabilities').click();
        }
      }
      await page.locator('#view-capabilities').waitFor({ state: 'visible', timeout: 20000 });
      await page.locator('#capabilitiesRefreshBtn').click();

      const search = page.locator('#capabilitiesTreeSearch');
      await search.waitFor({ state: 'visible', timeout: 15000 });
      await search.fill(SKILL_ID);
      await search.dispatchEvent('input');

      const treeReady = await waitFor(
        async () => {
          const text = await page.locator('#capabilitiesTreeList').innerText().catch(() => '');
          return (
            text.includes(`${SKILL_ID}/`) &&
            text.includes('SKILL.md') &&
            text.includes('arch.md') &&
            text.includes('format_tag.py') &&
            text.includes('ping_endpoint.py')
          );
        },
        { timeoutMs: 15000 }
      );
      if (!treeReady) {
        const actual = await page.locator('#capabilitiesTreeList').innerText().catch(() => '');
        throw new Error(`Expected ${SKILL_ID} files in #capabilitiesTreeList, got: ${actual}`);
      }

      const overflow = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
      }));
      if (overflow.scrollWidth > overflow.innerWidth + 2) {
        throw new Error(`Horizontal overflow on ${viewport.name}: scrollWidth=${overflow.scrollWidth} > innerWidth=${overflow.innerWidth}`);
      }
      j.note(`Capabilities tree rendered cleanly on ${viewport.name} (${overflow.scrollWidth}px <= ${overflow.innerWidth}px)`);
    });

    await j.step('Select references/arch.md in the tree, edit and save in the inspector', async () => {
      const refBtn = page.locator(`#capabilitiesTreeList [data-skill-id="${SKILL_ID}"][data-skill-file="references/arch.md"]`);
      await refBtn.scrollIntoViewIfNeeded();
      await refBtn.click();

      const loaded = await waitFor(
        async () => (await page.locator('#capabilitiesFileEditor').inputValue()).includes('Architecture Guide'),
        { timeoutMs: 10000 }
      );
      if (!loaded) throw new Error('references/arch.md did not load into #capabilitiesFileEditor');

      const updatedMd = `# Architecture Guide\n\nUpdated via Capabilities Studio (${marker}).\n`;
      await page.locator('#capabilitiesFileEditor').fill(updatedMd);

      const saveBtn = page.locator('#capabilitiesSaveFileBtn');
      await saveBtn.scrollIntoViewIfNeeded();
      await clickExpect(
        saveBtn,
        async () => {
          const fileData = await getJson(
            request,
            `${base}/api/capabilities/skills/${SKILL_ID}/file?path=${encodeURIComponent('references/arch.md')}`
          );
          return String(fileData.content || '').includes(marker);
        },
        { label: 'Save File', what: 'references/arch.md updated on disk', timeoutMs: 15000 }
      );
    });

    await j.step('Select tools/ping_endpoint.py, inspect access report, and toggle Enable Tool', async () => {
      const toolBtn = page.locator(`#capabilitiesTreeList [data-skill-id="${SKILL_ID}"][data-skill-file="tools/ping_endpoint.py"]`);
      await toolBtn.scrollIntoViewIfNeeded();
      await toolBtn.click();

      const statusCard = page.locator('#capabilitiesToolStatusCard');
      await statusCard.waitFor({ state: 'visible', timeout: 10000 });
      const cardReady = await waitFor(
        async () => {
          const txt = await statusCard.innerText().catch(() => '');
          return txt.includes('Disabled (needs approval)') && txt.includes('network');
        },
        { timeoutMs: 10000 }
      );
      if (!cardReady) throw new Error('ping_endpoint status card did not show Disabled (needs approval) and network');

      const toggleBtn = page.locator('#capabilitiesToggleToolBtn');
      await toggleBtn.scrollIntoViewIfNeeded();
      await clickExpect(
        toggleBtn,
        async () => {
          const tree = await getJson(request, `${base}/api/capabilities/tree`);
          const entry = (tree.skills || []).find((s) => (s.id || s.skill_id) === SKILL_ID);
          const tools = (entry && (entry.colocated_tools || (entry.files && entry.files.tools))) || [];
          const tool = tools.find((t) => t.name === 'ping_endpoint');
          return Boolean(tool && tool.enabled);
        },
        { label: 'Enable Tool', what: 'ping_endpoint enabled via Capabilities toggle', timeoutMs: 15000 }
      );

      const badgeUpdated = await waitFor(
        async () => (await page.locator('[data-testid="capabilities-tool-state-badge"]').innerText()) === 'Enabled',
        { timeoutMs: 10000 }
      );
      if (!badgeUpdated) throw new Error('Status badge did not update to Enabled');
      j.note('Toggled ping_endpoint from Disabled (needs approval) to Enabled in Capabilities Studio');
    });

    await j.step('Clean up temporary skill folder agora-tree-demo', async () => {
      fs.rmSync(path.join(skillsRoot, SKILL_ID), { recursive: true, force: true });
    });
  },
};
