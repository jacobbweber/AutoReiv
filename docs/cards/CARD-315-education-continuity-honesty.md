# [CARD-315] Education honesty / continuity (shell)

> **Status**: In Review
> **Branch**: `feat/super-marathon-ui`
> **Created**: 2026-09-14
> **Depends**: CARD-237 / CARD-250 viewport wrap; CARD-240 Job chrome; REQ-HITL-ORIGIN (Chat P0)

## Three Beats

1. **Means**: Education usable — Ask works, panels not a wall, scroll works, journey/HITL stay on the Education session that minted the job.
2. **Now**: Pedagogy panels are always-open cards under `#educationPedagogyColumns`; viewport wrap exists (CARD-250); Ask already mints fresh Education session + keeps SSE for HITL (REQ-HITL-ORIGIN) but needs chrome/contract proof + collapsed sections.
3. **Change**: Collapse panels into `details.edu-section` (no `open` on load); `#view-education` min-h-0 + scroll like Settings/Observe; harden/prove origin-session journey/HITL; bump `app.js` cache.

## Intent

Shell + honesty only. Structure/interaction so Ask + job chrome do not blank or orphan the rail. **Do not** deepen Learning OS engines / amplifiers / fake mastery theatre.

## Done bars (locked)

1. Finish Education shell continuity (CARD-237 / viewport) so Ask + job chrome don’t blank or orphan the rail.
2. Same studio rules: Learning OS sections **collapsed on load**; expand fully scrollable (phone + desktop) — Observe/Settings pattern.
3. Journey / HITL stay on the **origin Education session** (no refresh theatre) — reuse Chat P0 / existing REQ-HITL-ORIGIN pattern in `education.js`.
4. No new pedagogy theatre — structure/interaction only.

## Acceptance

- [x] Each Learning OS panel under `#educationPedagogyColumns` wrapped in `<details class="edu-section">` with summary + `.edu-section-body`; **no `open` on load**
- [x] `#view-education` / hosted desktop: `min-h-0` + overflow-y auto so expanded content fully reachable (phone + desktop); CARD-250 wrap/`overflow-x-hidden` preserved
- [x] Ask form + session list usable; studio rail not blanked
- [x] Ask mints **fresh Education session** (not Chat `activeSessionId`); SSE not aborted on `job_created` (REQ-HITL-ORIGIN); phase events forward to Job chrome (CARD-240)
- [x] Vitest `education_continuity_315.test.js` green; cache `app.js?v=2.0.51`
- [x] No new quiz/SRS/amplifier/mastery APIs or fake progress chrome

## Out of scope

- Reopening quiz / SRS / amplifier engines
- Merge to `qa` / `main`
- Committing `uv.lock`
