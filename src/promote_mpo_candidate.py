"""Single conservative promotion gate for MPO-generated QASM.

This wrapper never promotes on optimizer fidelity alone.  It checks the
serialized artifact and delegates correctness to ``exhaustive_verify.py``.
Approximate checkpoints therefore remain diagnostics even when their native
depth is small.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from qiskit import qasm2


def inspect(path: str | Path) -> dict:
    path = Path(path)
    source = path.read_text()
    circuit = qasm2.loads(source)
    operations = set(circuit.count_ops())
    report = {
        "qasm": str(path.resolve()),
        "sha256": hashlib.sha256(source.encode()).hexdigest(),
        "width": circuit.num_qubits,
        "depth": circuit.depth(),
        "cx_count": int(circuit.count_ops().get("cx", 0)),
        "basis": sorted(operations),
        "standalone_basis_ok": operations <= {"u3", "cx"},
        "width_ok": 12 <= circuit.num_qubits <= 18,
        "promoted": False,
    }
    report["preconditions_ok"] = report["standalone_basis_ok"] and report["width_ok"]
    return report


def promote(path: str | Path) -> dict:
    report = inspect(path)
    if not report["preconditions_ok"]:
        report["reason"] = "serialized circuit failed standalone u3/cx or width precondition"
        return report
    try:
        from exhaustive_verify import exhaustive

        exhaustive(str(path))
    except (AssertionError, RuntimeError, ValueError) as error:
        report["reason"] = f"exhaustive verifier rejected candidate: {error}"
        return report
    report["promoted"] = True
    report["reason"] = "passed repository exhaustive verification"
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("qasm")
    args = parser.parse_args()
    result = promote(args.qasm)
    print(json.dumps(result, indent=2))
    Path(args.qasm).with_suffix(".promotion.json").write_text(json.dumps(result, indent=2) + "\n")
