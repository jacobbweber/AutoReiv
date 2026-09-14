#!/usr/bin/env python3
"""CARD-310: assemble routines.js from scratch/card310/rjs_*.txt parts."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
parts = sorted(
    (root / "scratch/card310").glob("rjs_*.txt"),
    key=lambda p: int(p.stem.split("_")[1]),
)
if not parts:
    raise SystemExit("no rjs_*.txt parts found")
chunks = []
for i, p in enumerate(parts):
    raw = p.read_text()
    # GitHub Contents API may append a trailing newline to part 0 only.
    if i == 0:
        raw = raw.rstrip("\n")
    chunks.append(raw)
text = "".join(chunks)
out = root / "src/web/static/modules/studios/routines.js"
out.write_text(text)
print("wrote", out, "bytes", len(text), "from", [p.name for p in parts])
