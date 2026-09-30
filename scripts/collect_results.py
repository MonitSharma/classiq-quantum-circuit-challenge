#!/usr/bin/env python3
"""Build results/verified_circuits.csv from the milestone folders in artifacts/.

Every circuit that has an exhaustive verification report next to it
(<name>.exhaustive.json) is listed with its depth, CX and U3 counts, SHA-256,
the maximum verification error and the date it was first committed (dates already
present in the CSV are kept).  With
--verify each circuit is re-verified from scratch (about 1 s per circuit).

Usage:
    python scripts/collect_results.py            # read existing reports
    python scripts/collect_results.py --verify   # re-run the exhaustive check
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_circuit as vc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MILESTONE = re.compile(r"^\d+[a-z]?(_cx\d+)?$")


def first_commit_date(rel: str) -> str:
    try:
        out = subprocess.run(["git", "log", "--diff-filter=A", "--format=%ad", "--date=short", "--", rel],
                             cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
        return out[-1] if out else ""
    except (OSError, subprocess.CalledProcessError):
        return ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", action="store_true", help="re-run the exhaustive verification")
    ap.add_argument("--out", default=str(ROOT / "results" / "verified_circuits.csv"))
    args = ap.parse_args(argv)

    # keep dates already recorded (a shallow or squashed clone cannot recover them from git)
    known = {}
    if Path(args.out).exists():
        with open(args.out, newline="") as fh:
            known = {r["path"]: r.get("date_added", "") for r in csv.DictReader(fh)}

    rows = []
    for folder in sorted((ROOT / "artifacts").iterdir()):
        if not folder.is_dir() or not MILESTONE.match(folder.name):
            continue
        for qasm in sorted(folder.glob("*.qasm")):
            report = qasm.with_suffix(".exhaustive.json")
            if not report.exists():
                continue
            rel = qasm.relative_to(ROOT).as_posix()
            n, gates, text = vc.parse_qasm(qasm)
            stats = vc.depth_and_counts(n, gates)
            if args.verify:
                r = vc.verify(qasm)
                if not r["passed"]:
                    print(f"FAIL {rel}", file=sys.stderr)
                    return 1
                err = r["max_error"]
            else:
                err = json.loads(report.read_text()).get("max_error")
            rows.append({
                "depth": stats["depth"], "cx": stats["cx"], "u3": stats["u3"], "width": n,
                "max_error": f"{err:.2e}" if err is not None else "",
                "date_added": known.get(rel) or first_commit_date(rel),
                "sha256": vc.hashlib.sha256(text.encode()).hexdigest(),
                "path": rel,
            })
    rows.sort(key=lambda r: (r["depth"], r["cx"], r["path"]))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} verified circuits -> {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
