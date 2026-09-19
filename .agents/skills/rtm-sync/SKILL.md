---
name: rtm-sync
description: >-
  Legacy runbook for historical Requirements Traceability Matrix verification. RTM is retired as an active gate and archived under docs/archive_artifacts/rtm.json.
---

# RTM Traceability (Retired / Legacy Archive)

> **Notice**: As part of AutoReiv's SDLC streamlining, per-feature 3-file specs and the machine-readable Requirements Traceability Matrix (`docs/rtm.json`) have been retired and archived under `docs/archive_artifacts/`.
>
> AutoReiv uses the **Pragmatic Triad**:
>
> 1. **Living Steering**: `steering/` (`product.md`, `tech.md`, `structure.md`, `roadmap.md`)
> 2. **Active Work Cards**: `docs/cards/CARD-xxx.md` (Four Beats, EARS acceptance criteria, test-locked delivery)
> 3. **Architectural Decisions**: `docs/adr/` (ADR-0001+)
>
> Pre-flight verification is run via `npm run preflight` (or `.agents/skills/preflight/`).

---

## Historical Reference

To inspect or validate the archived RTM for historical forensics:

```bash
python .agents/skills/rtm-sync/scripts/verify_rtm.py --impact <path_to_modified_file>
```
