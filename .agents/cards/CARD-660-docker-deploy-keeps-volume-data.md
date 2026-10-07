---
id: CARD-660
title: "1.0 gate — Docker deploy keeps mounted volume data through remove and recreate"
type: feature
status: Ready
priority: P1
milestone: M23
needs_decision: build
proof:
  journeys: []
  checks: []
branch:
log: {minutes: 90, qa_runs: 1, findings: 1}
created: 2026-10-06
completed:
related:
  - CARD-658
  - CARD-659
  - CARD-661
  - CARD-662
  - CARD-663
  - CARD-664
  - CARD-665
  - CARD-666
  - CARD-667
  - CARD-668
---

# CARD-660 1.0 gate — Docker deploy keeps mounted volume data through remove and recreate

## 1.0 gate set
This card is part of the AutoReiv 1.0 gate set: CARD-658, CARD-659, CARD-660, CARD-661, CARD-662, CARD-663, CARD-664, CARD-665, CARD-666, CARD-667, CARD-668.
Do not start work until Jacob approves a build for this card.


## Intent
Before calling AutoReiv 1.0 in Docker, prove that running with a mounted data volume, using the product, removing the container, and creating it again leaves the volume's data intact and findable.

## Goal
An operator can start AutoReiv with Docker Compose (or equivalent) and a mounted data volume, send a real chat message, remove the container, confirm the volume still holds the data, recreate the container with the same volume, and see the same chat (or the same data) still present.

## Acceptance
- Deploy with a mounted data volume (database and wiki as the compose file expects).
- Run one real chat turn that is saved into that volume.
- Remove the container (do not delete the volume).
- Confirm the volume data is intact on disk.
- Recreate the container with the same volume mount; the earlier chat (or equivalent saved data) is still there.

## Plan and decisions
Needs Jacob's build approval before any work starts. Use a throwaway volume name for the check.

## Results
| Check | Result | Notes |
|---|---|---|
| Expected Docker data path | documented | Named volume → `/data` (`AUTOREIV_DATA_DIR=/data`); wiki via `AUTOREIV_WIKI_HOST_PATH` bind or `autoreiv-wiki` volume (compose + CARD-414). |
| Stock `docker compose build` | FAIL | Product `Dockerfile` still `COPY`s `platform-packs/` which does not exist (repo uses `platform/`). See CARD-669. |
| Gate run with local-only Dockerfile override | PASS | Image `autoreiv-1.0-gate-test:local`, project `autoreiv10gate`, port **8781**, volume **`autoreiv-1.0-gate-test-data`**, wiki bind `C:\Users\jacob\AppData\Local\AutoReiv-1.0-gate-test-docker-wiki`. Health 200 (`0.46.0`). Marker token `gate660-20261006-231623` written to `/data/1.0-gate-marker.txt`. |
| Uninstall = `docker compose down` (no `-v`) | PASS | Container gone; volume `autoreiv-1.0-gate-test-data` still present. |
| Recreate same volume | PASS | Marker returned identical. Live AppData file count unchanged at 43. |
| Cleanup | PASS | `docker compose down -v`, removed test wiki bind dir, removed test image. |
| Chat turn | PARTIAL | Session created (`6bd70cef-...`); stream POST returned 422 with the bodies tried. |

**Verdict: PASS (persistence)** for Docker named-volume keep/recreate, using a **local test Dockerfile** because stock build is broken (CARD-669). Do not treat stock `docker compose up` from qa tip alone as green until 669 lands.

**Implications:** CARD-668 should say: never `down -v` unless you mean to wipe; wiki host path is required. CARD-662 Docker recreate-with-same-volume is supported by this evidence.

