"""Summarize bounded architecture CI results without promoting unverified candidates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

PROTECTED_DEPTH = 185


def _read_int(path: Path):
    try:
        return int(path.read_text().strip())
    except Exception:
        return None


def summarize(root: Path) -> str:
    lines = [
        "# Post-185 new architecture suite",
        "",
        "Protected comparison point: **185 / 854 / 18**. A native circuit is called verified only when its exact emitted QASM has a successful `exhaustive_verify.py` report.",
        "",
        "| Method | Run | Native result | Exhaustive | Interpretation |",
        "|---|---:|---|---|---|",
    ]
    for method in ["cofactor", "kg24", "qrom", "mvi", "cst"]:
        folder = root / method
        code = _read_int(folder / "exit_code.txt")
        run = "ok" if code == 0 else ("timeout" if code == 124 else f"exit {code}")
        reports = [p for p in folder.glob("*.json") if p.name not in {"report.json"}]
        data = None
        for path in reports:
            try:
                d = json.loads(path.read_text())
            except Exception:
                continue
            if isinstance(d, dict) and d.get("kind"):
                data = d
                break
        if method == "cofactor" and data:
            best4 = data["best"].get("4", {})
            native = f"structural only; best k=4 max/total ANF {best4.get('max_terms')}/{best4.get('total_terms')}"
            exhaustive = "n/a"
            interpretation = "screen only"
        elif method == "cst" and data:
            native = f"max feasible cluster {data.get('max_cluster_size')} at {data.get('ancillas')} ancillas"
            exhaustive = "n/a"
            interpretation = "screen only"
        elif data:
            depth, cx, width = data.get("depth"), data.get("cx"), data.get("width")
            native = f"{depth} / {cx} / {width}"
            qasm = data.get("qasm")
            verify = None
            if qasm:
                qpath = Path(qasm)
                report_path = qpath.with_suffix(".exhaustive.json")
                if report_path.exists():
                    try:
                        verify = json.loads(report_path.read_text())
                    except Exception:
                        verify = None
            exhaustive = "pass" if verify else "missing/fail"
            if verify and depth is not None and depth < PROTECTED_DEPTH:
                interpretation = "**competitive improvement**"
            elif verify:
                interpretation = "correct but not depth-competitive"
            else:
                interpretation = "not promoted"
        else:
            native = "no report"
            exhaustive = "n/a"
            interpretation = "timeout/failure" if code else "no result"
        lines.append(f"| `{method}` | {run} | {native} | {exhaustive} | {interpretation} |")
    lines += [
        "",
        "The cofactor and CST rows are deliberately diagnostics rather than QASM candidates. Timeouts are UNKNOWN, not negative proofs.",
        "",
    ]
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    text = summarize(a.root)
    a.out.write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
