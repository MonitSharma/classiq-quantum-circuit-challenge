"""Inventory joint logic sharing and run bounded ABC multi-output flows."""

from __future__ import annotations

import json
import subprocess
from collections import Counter
from pathlib import Path

from vector_feature_analysis import ARTIFACTS, FEATURES, truth_rows, output_inventory


ROOT = Path(__file__).resolve().parents[1]
ABC = ROOT / "experiments/abc/abc"


def write_pla(rows: list[dict[str, int]], path: Path) -> None:
    lines = [f".i 6", f".o {len(FEATURES)}", ".ilb y0 y1 y2 y3 y4 y5",
             ".ob " + " ".join(FEATURES)]
    for row in rows:
        inputs = "".join(str((row["y"] >> bit) & 1) for bit in range(6))
        outputs = "".join(str(row[name]) for name in FEATURES)
        lines.append(f"{inputs} {outputs}")
    lines.append(".e")
    path.write_text("\n".join(lines) + "\n")


def run_abc(pla: Path, name: str, script: str) -> dict:
    output = ARTIFACTS / f"vector_feature_abc_{name}.bench"
    command = f"read_pla {pla}; {script}; ps; write_bench {output}"
    result = subprocess.run([str(ABC), "-c", command], cwd=ROOT,
                            text=True, capture_output=True, check=False)
    return {
        "name": name,
        "script": script,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "output": str(output.relative_to(ROOT)) if output.exists() else None,
    }


def main() -> None:
    rows = truth_rows()
    algebra, shared = output_inventory(rows)
    pla = ARTIFACTS / "vector_feature.pla"
    write_pla(rows, pla)

    flows = {
        "strash_balance_rewrite_refactor_resub":
            "strash; balance; rewrite; refactor; resub; balance",
        "strash_rewrite_z_balance_refactor":
            "strash; rewrite -z; balance; refactor; rewrite -z; balance",
        "strash_balance_rewrite_resub_balance":
            "strash; balance; rewrite; resub; balance; rewrite -z; balance",
    }
    abc_runs = [run_abc(pla, name, script) for name, script in flows.items()]
    inventory = {
        "inputs": 6,
        "outputs": list(FEATURES),
        "scalar_anf_term_count": shared["sum_scalar_anf_terms"],
        "unique_anf_monomial_count": shared["unique_anf_monomial_count"],
        "shared_anf_monomial_count": len(shared["shared_monomials"]),
        "shared_anf_monomials": shared["shared_monomials"],
        "per_output": {
            name: {
                "anf_term_count": spec["anf_term_count"],
                "algebraic_degree": spec["algebraic_degree"],
            }
            for name, spec in algebra.items()
        },
        "abc_binary": str(ABC.relative_to(ROOT)),
        "abc_runs": abc_runs,
        "note": "ABC outputs are synthesis inventories only; no reversible loader is claimed.",
    }
    (ARTIFACTS / "vector_feature_logic_inventory.json").write_text(
        json.dumps(inventory, indent=2) + "\n"
    )
    print(json.dumps({
        "pla": str(pla.relative_to(ROOT)),
        "abc_runs": [
            {"name": r["name"], "returncode": r["returncode"], "output": r["output"]}
            for r in abc_runs
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
