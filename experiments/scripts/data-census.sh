#!/usr/bin/env bash
# Refresh DATA_SOURCES.md numbers. Run me whenever a new sweep finishes.
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
python3 - <<'PY'
import json, glob, os, datetime
from collections import defaultdict

SOURCES = {
    "experiments/results": "Canonical runner output (post-PR-#55)",
    "experiments/src/results": "Frozen pre-PR-#55 runner output",
    ".claude/worktrees/strange-yalow-8d35ff/experiments/src/results": "Worktree spec-v2/v3 sweep corpus",
}
print("="*100)
print(f"{'source':<60} {'dirs':>5} {'cells':>6} {'oldest':>12} {'newest':>12}")
print("="*100)
total_cells = 0
for label, desc in SOURCES.items():
    r = os.path.expanduser(label)
    if not os.path.isdir(r):
        print(f"  {label:<58} NOT FOUND")
        continue
    cells = 0; dirs = 0; mtimes = []
    for d in os.listdir(r):
        full = os.path.join(r, d)
        if not os.path.isdir(full): continue
        dirs += 1
        for fp in glob.glob(f"{full}/*.json"):
            if "summary" in fp or "secondary" in fp: continue
            try:
                j = json.load(open(fp))
                if "error" not in j:
                    cells += 1
                    mtimes.append(os.path.getmtime(fp))
            except: pass
    total_cells += cells
    old = datetime.datetime.fromtimestamp(min(mtimes)).strftime("%Y-%m-%d") if mtimes else "—"
    new = datetime.datetime.fromtimestamp(max(mtimes)).strftime("%Y-%m-%d") if mtimes else "—"
    print(f"  {label:<58} {dirs:>5} {cells:>6} {old:>12} {new:>12}")
print()
print(f"TOTAL VALID CELLS ACROSS ALL SOURCES: {total_cells}")
print()
print("See experiments/DATA_SOURCES.md for the full inventory + aggregate paired comparisons.")
PY
