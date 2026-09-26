/**
 * CARD-532 live QA runner CLI. Reuses @playwright/test's chromium (no new dependencies).
 *   node tests/e2e/journeys/run.mjs --base http://127.0.0.1:8770 --journeys card-520,card-530 --viewports desktop,phone
 * Options: --out <dir> (default <temp>/autoreiv-qa/<card-or-run>), --attempts N, --headed, --judge (off by default).
 * Exit code 0 when every journey passed (warnings allowed), 1 otherwise.
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import { chromium } from '@playwright/test';
import { JourneyRun, VIEWPORTS, defaultReportRoot, reportDirFor, writeReport } from './lib/runner.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));

export function parseArgs(argv) {
  const out = { base: 'http://127.0.0.1:8770', journeys: [], viewports: ['desktop', 'phone'], out: '', card: '', attempts: 1, headed: false, judge: false, append: false };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    const next = () => argv[++i];
    if (a === '--base') out.base = next();
    else if (a === '--journeys') out.journeys = next().split(',').map((s) => s.trim()).filter(Boolean);
    else if (a === '--viewports') out.viewports = next().split(',').map((s) => s.trim()).filter(Boolean);
    else if (a === '--out') out.out = next();
    else if (a === '--card') out.card = next();
    else if (a === '--attempts') out.attempts = Math.max(1, Number(next()) || 1);
    else if (a === '--headed') out.headed = true;
    else if (a === '--judge') out.judge = true;
    else if (a === '--append') out.append = true;
  }
  return out;
}

export function listJourneyFiles(dir = HERE) {
  return fs.readdirSync(dir).filter((f) => /^card-\d+-.+\.mjs$/.test(f)).sort();
}

/** "card-530" or a full id prefix selects journey files. Empty selects all. */
export function selectJourneyFiles(files, wanted) {
  if (!wanted || !wanted.length) return files;
  return files.filter((f) => wanted.some((w) => f.startsWith(w)));
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const files = selectJourneyFiles(listJourneyFiles(), args.journeys);
  if (!files.length) { console.error('No journeys matched', args.journeys); process.exit(2); }
  const vps = VIEWPORTS.filter((v) => args.viewports.includes(v.name));
  const outDir = args.out || reportDirFor(args.card || (args.journeys.length === 1 ? args.journeys[0] : 'journeys'), defaultReportRoot());
  const startedAt = new Date().toString();
  const judge = { enabled: args.judge || process.env.AUTOREIV_QA_JUDGE === '1', url: process.env.AUTOREIV_QA_JUDGE_URL || '', model: process.env.AUTOREIV_QA_JUDGE_MODEL || '' };
  const browser = await chromium.launch({ headless: !args.headed });
  // --append: add to the report of an earlier run (live_qa.py runs each journey and viewport in a fresh env).
  const prior = path.join(outDir, 'report.json');
  const runs = args.append && fs.existsSync(prior) ? (JSON.parse(fs.readFileSync(prior, 'utf-8')).runs || []) : [];
  const firstNew = runs.length;
  try {
    for (const file of files) {
      const journey = (await import(pathToFileURL(path.join(HERE, file)).href)).default;
      for (const vp of vps) {
        let run = null;
        for (let attempt = 1; attempt <= args.attempts; attempt += 1) {
          const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
          const page = await ctx.newPage();
          const id = attempt === 1 ? journey.id : `${journey.id}-try${attempt}`;
          run = new JourneyRun({ page, viewport: vp, outDir, journeyId: id, allow: journey.allow, allowConsole: journey.allowConsole }).watch();
          console.info(`[live-qa] ${id} (${vp.name}) ...`);
          try {
            await journey.run(run, { page, request: ctx.request, base: args.base, viewport: vp, judge });
          } catch (err) {
            run.results.push({ step: 'journey crashed', status: 'fail', reason: String(err).slice(0, 300), screenshot: await run.screenshot('crash'), ms: 0 });
          }
          await ctx.close();
          console.info(`[live-qa] ${id} (${vp.name}): ${run.outcome().toUpperCase()}`);
          runs.push(run.toJSON());
          if (run.outcome() !== 'fail') break;
        }
      }
    }
  } finally {
    await browser.close();
  }
  const { mdPath, jsonPath } = writeReport(outDir, runs, { title: 'AutoReiv live QA', startedAt, base: args.base });
  console.info(`[live-qa] summary: ${mdPath}`);
  console.info(`[live-qa] report:  ${jsonPath}`);
  // A journey passes when its last attempt did not fail.
  const last = new Map();
  runs.slice(firstNew).forEach((r) => last.set(`${r.journey.replace(/-try\d+$/, '')}|${r.viewport}`, r.outcome));
  process.exit([...last.values()].some((o) => o === 'fail') ? 1 : 0);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((err) => { console.error(err); process.exit(1); });
}
