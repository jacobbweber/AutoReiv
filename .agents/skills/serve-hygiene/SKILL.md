---
name: serve-hygiene
description: >-
  Restart Jacob's AutoReiv serve on Jarvis (:8000) and check health on both hosts.
---

# Serve hygiene (Jarvis)

Goal: exactly one serve on `:8000`, from the current `qa` tip, reachable from the phone.

```powershell
pwsh -NoProfile -File scripts\restart_serve.ps1 -Status
pwsh -NoProfile -File scripts\restart_serve.ps1 -HostAddr 0.0.0.0 -Port 8000
Invoke-WebRequest http://127.0.0.1:8000/api/health -UseBasicParsing | Select-Object StatusCode
Invoke-WebRequest http://192.168.1.99:8000/api/health -UseBasicParsing | Select-Object StatusCode
```

- Both health checks return 200.
- The restart script kills orphans and prints `app.js?v=`; after a restart, Ctrl+F5 in the browser.
- `git status` shows no new `*.db` or `packs/` in the checkout.

Source: `scripts/restart_serve.py` (CARD-256), wrapper `scripts/restart_serve.ps1`.
