# CARD-296 delta apply (Jarvis)

Remote tip after MCP partial push may lag local `776a717`.

## Apply remaining code (from repo root)

```powershell
cd D:\Projects\Active\AutoReiv
git fetch origin feat/super-marathon-ui
git checkout feat/super-marathon-ui
git pull --ff-only origin feat/super-marathon-ui
git apply --index docs/cards/CARD-296.delta.patch
git commit -m "feat(chat): sessions drawer, one picker, jump to latest (CARD-296)"
git push origin feat/super-marathon-ui
uv run python scripts/restart_serve.py --port 8000 --host 127.0.0.1
```

SHA256 of authoritative tgz (box): a6299c7d0cfece649417c4b39645f8ff7cf09aa21f1775e5af1dda712a77c5d4
Local tip: 776a717970b96e7d56422b5eee14aefe71a3578f

Vitest: 57 files / 389 tests green on box after implement.
