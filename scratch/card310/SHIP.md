# CARD-310 ship note

Remote tip includes structured matcher/API + rjs parts + assemble/apply.

On Jarvis (`D:\\Projects\\Active\\AutoReiv`, branch `feat/super-marathon-ui`):

```powershell
git fetch origin feat/super-marathon-ui
git checkout feat/super-marathon-ui
git pull --ff-only origin feat/super-marathon-ui
bash scratch/card310/APPLY_CARD310_UI.sh
# or: python scratch/card310/assemble_routines_js.py
#      then apply scratch/card310/index_310.patch if panel missing
#      python scripts/restart_serve.py --port 8000
```

Then Ctrl+F5 → Routines → verify months/weekdays/DOM/time/every-N-weeks, both agent dropdowns full `/api/agents`, Next fire preview, enabled=false blocks.
