"""Finite-size resource audit for the Nie--Zi general-oracle construction.

This is deliberately a resource calculator, not an oracle synthesizer.  The
paper gives asymptotic bounds and uses conditional-clean ancillas for m < n;
it does not publish a finite n=12,m=6 gate schedule in the challenge's u3/cx
model.  The script makes that missing constant explicit and calibrates common
primitive lowerings with the repository's Qiskit toolchain.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from qiskit import QuantumCircuit, transpile


N = 12
M = 6
PRIMITIVES = ("x", "cx", "ccx", "rccx", "mcx3", "mcx4", "mcx5", "mcx6")


def calibrated_primitives() -> dict:
    """Measure standalone primitive depth/CX in the scoring basis.

    These are calibration facts, not claims that the paper's abstract
    fan-out/Toffoli primitives have these exact costs.
    """
    circuits = {}
    c = QuantumCircuit(1)
    c.x(0)
    circuits["x"] = c
    c = QuantumCircuit(2)
    c.cx(0, 1)
    circuits["cx"] = c
    c = QuantumCircuit(3)
    c.ccx(0, 1, 2)
    circuits["ccx"] = c
    c = QuantumCircuit(3)
    c.rccx(0, 1, 2)
    circuits["rccx"] = c
    for controls in range(3, 7):
        c = QuantumCircuit(controls + 1)
        c.mcx(list(range(controls)), controls)
        circuits[f"mcx{controls}"] = c
    result = {}
    for name, circuit in circuits.items():
        lowered = transpile(
            circuit,
            basis_gates=["u3", "cx"],
            optimization_level=0,
            qubits_initially_zero=False,
        )
        result[name] = {
            "qubits": lowered.num_qubits,
            "depth": lowered.depth(),
            "cx": lowered.count_ops().get("cx", 0),
            "ops": dict(lowered.count_ops()),
        }
    return result


def parameter_rows() -> list[dict]:
    """Enumerate p+q=12 splits used by Section 4.3.

    The paper writes the admissibility condition with Theta notation.  The
    explicit `unit_constant_condition` is therefore only a transparent
    conservative screen, never a theorem-level finite-size proof.
    """
    rows = []
    for q in range(1, N):
        p = N - q
        workspace = p + M
        asymptotic_capacity = (2**q) / q
        rows.append({
            "p": p,
            "q": q,
            "prefix_iterations": 2**p,
            "conditional_clean_workspace": workspace,
            "unit_constant_condition": workspace <= asymptotic_capacity,
            "paper_capacity_ratio": workspace / asymptotic_capacity,
            # The per-prefix f_S term is the dominant Section 4.3 term.
            "optimistic_table_slots": (2**q) / workspace,
            "optimistic_round_trip_slots": 2 * (2**q) / workspace,
            "optimistic_total_slots": 2 * (2**N) / workspace,
            "prefix_overhead_slots": 2 * p + 3,
        })
    for row in rows:
        row["optimistic_total_with_prefix"] = (
            row["prefix_iterations"]
            * (row["optimistic_round_trip_slots"] + row["prefix_overhead_slots"])
        )
    return rows


def main() -> dict:
    root = Path(__file__).resolve().parents[1]
    calibration = calibrated_primitives()
    rows = parameter_rows()
    legal = [row for row in rows if row["unit_constant_condition"]]
    best = min(legal, key=lambda row: row["optimistic_total_with_prefix"]) if legal else None
    result = {
        "kind": "Nie-Zi finite-size resource audit",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "command": "PYTHONPATH=src .venv/bin/python src/nie_zi_finite.py",
        "paper": "arXiv:2607.28402v1, Section 4.3, Theorem 1",
        "n": N,
        "ancillas": M,
        "output_bits": 1,
        "construction_regime": "m < n conditional-clean prefix construction",
        "parameter_rows": rows,
        "best_unit_constant_screened_split": best,
        "calibrated_primitives": calibration,
        "paper_limits": {
            "theorem_depth_bound": "O(2^n/(n+m)) for m<n",
            "hidden_constants": "not specified in the paper",
            "gate_model": "constant-width finite gate set, not directly u3/cx depth",
            "finite_schedule": "not supplied; this report does not claim an implementation",
        },
    }
    if best is None or best["optimistic_total_with_prefix"] > 300:
        verdict = "STOP"
    elif best["optimistic_total_with_prefix"] > 230:
        verdict = "CONDITIONAL GO"
    else:
        verdict = "GO"
    result["verdict"] = verdict
    result["verdict_basis"] = (
        "Even the unit-constant screened estimate exceeds the requested native-depth gate; "
        "the paper's asymptotic theorem cannot justify implementing a full n=12,m=6 oracle here."
        if verdict == "STOP" else
        "Screened estimate is promising but does not include a faithful native schedule."
    )
    path = root / "artifacts/unitary_state_space/nie_zi_finite_resource.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()
