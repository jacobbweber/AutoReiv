---
trigger: always_on
description: Never put live AutoReiv user data (packs, *.db, wiki) in the git checkout.
---

# Rule: Checkout working-tree hygiene (CARD-294)

- Live packs, `*_memory.db`, `*_storage.db`, wiki, attachments, and `autoreiv.db` belong **only** under the user data root (`AUTOREIV_DATA_DIR`, else platform default e.g. `%LOCALAPPDATA%\AutoReiv\`).
- Repo `platform-packs/` is **factory seed only** — copied into user-data `packs/` when missing. Runtime reads/writes user data.
- Temporary local work goes **only** under `scratch/` (tracked `.gitkeep`; everything else under `scratch/` is gitignored).
- A `*.db` or live pack under the checkout outside `scratch/` is a **bug or leftover**: fix the writer, delete the leftover (never delete AppData), add a regression test.
- `ensure_live_data_root` in `src/infrastructure/data/resolver.py` must keep refusing checkout live roots.
