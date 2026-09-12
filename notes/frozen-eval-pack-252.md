# Frozen operator eval pack - CARD-252

**Pack**: `notes/frozen-eval-pack-252.json`  
**Runner**: `notes/scripts/frozen_eval_pack_252.py` (pytest: `tests/unit/eval/test_frozen_eval_pack_252.py`)  
**Live artifact**: `notes/marathon-card252-live-smoke.json`  
**Base**: `feat/forge-approve-job-resume-251` @ `c70075e`  
**Models**: grok + qwen (live evidence from marathon smokes on Jarvis serve)

## Observe checklist (every ask)

1. Record `job_id` when Job mints / resumes.
2. Open Observability -> Standing journey (or `GET /api/observability/standing-journey?job_id=...`).
3. Confirm timeline/spans for that `job_id` (not empty theatre / not `jobs=[]` after outcome).
4. Paste `job_id` into notes for the pack run.

## Asks (frozen)

| # | Id | Studio | Prompt (frozen) | Evidence smoke | Live Observe id |
|---|----|--------|-----------------|----------------|-----------------|
| 1 | `ask_chat_outcome_job` | Chat | Wiki note + done-when (CARD-236 CoS ask) | `marathon-card236-live-smoke.json` | `job_0dd0685b3f0c` |
| 2 | `ask_education_ask_quiz` | Education | Education Ask + quiz/retention Job path | `237` + `242` smokes | `job_e757cad8ce1f` / `job_8c58119ac7d0` |
| 3 | `ask_wiki_job` | Wiki | Wiki deliverable bound to durable `job_id` | `marathon-card236-live-smoke.json` | `job_0dd0685b3f0c` |
| 4 | `ask_forge_approve_same_job` | Forge | Park -> Forge Approve -> **same** `job_id` | `marathon-card251-live-smoke.json` | artifact-only (in-process) |

## CI

```bash
pytest -q tests/unit/eval/test_frozen_eval_pack_252.py
python notes/scripts/frozen_eval_pack_252.py --validate
# optional live:
python notes/scripts/frozen_eval_pack_252.py --live --write-smoke
```

## Pass / fail

- **Pass**: all asks green (smoke `ok` + required Observe checklist fields; live Observe where ids exist).
- **Fail**: any ask red => CARD-252 not Done (Architect bar).
