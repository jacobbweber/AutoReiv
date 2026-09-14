#!/usr/bin/env python3
from pathlib import Path
root = Path(__file__).resolve().parents[2]
parts = sorted((root/"scratch/card310").glob("rjs_*.txt"), key=lambda p: int(p.stem.split("_")[1]))
text = "".join(p.read_text() for p in parts)
out = root/"src/web/static/modules/studios/routines.js"
out.write_text(text)
print("wrote", out, len(text))
