# CARD-310 ship / Jarvis apply

**Remote tip:** `6de88b216dd2b6fe2557abfbf2f70a24fa638d93` (assemble fix).
**Local box tip (full UI already applied):** `6265bdcfe91442955004cda70f93b4814f978e97`.

Backend (matcher, `schedule_rule`, preview API, STRUCTURED, tests) is on the branch.
UI `routines.js` is shipped as `scratch/card310/rjs_0.txt`…`rjs_4.txt` + assembler (GitHub Contents could not accept a single 30KB push from this agent in one shot). Index panel is in `scratch/card310/index_310.patch`.

## Jarvis (D:\\Projects\\Active\\AutoReiv)

```powershell
cd D:\Projects\Active\AutoReiv
git fetch origin feat/super-marathon-ui
git checkout feat/super-marathon-ui
git pull --ff-only origin feat/super-marathon-ui
python scratch/card310/assemble_routines_js.py
# if panel missing:
git apply scratch/card310/index_310.patch
python scripts/restart_serve.py --port 8000
```

Or: `bash scratch/card310/APPLY_CARD310_UI.sh`

Leave `uv.lock` dirty/uncommitted.

## Ctrl+F5 checklist
1. Hard refresh (Ctrl+F5) — Network shows `app.js?v=2.0.46`
2. Routines → New: months (12), weekdays (7), DOM (1–31), hour/minute, every N weeks + anchor
3. Biweekly Tue 18:00 + anchor → Next fire preview; cron shows only when representable
4. Filter agent + create agent dropdowns list full `/api/agents` (not 3-agent fallback)
5. Pause / enabled=false still blocks scheduler fire
