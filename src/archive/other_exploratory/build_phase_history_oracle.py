"""Construct a phase-history oracle from a primitive gate history.

The input history is a JSON object containing a ``gates`` array in the same
format as the destructive-search artifacts.  Taps can be supplied as a JSON
array of ``{"step": ..., "wire": ...}`` objects, or obtained by auditing the
history with :mod:`phase_history_search`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qiskit import qasm2

from phase_history_search import (
    build_phase_history_circuit,
    compile_u3_cx,
    gates_from_json,
)


def build_from_files(history_path: Path, taps_path: Path):
    history = gates_from_json(history_path)
    taps_data = json.loads(taps_path.read_text())
    taps = taps_data.get("taps", taps_data.get("provenance", {}).get("taps", []))
    return compile_u3_cx(build_phase_history_circuit(history, taps))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("history", type=Path)
    parser.add_argument("taps", type=Path,
                        help="JSON array or audit JSON containing phase taps")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    compiled = build_from_files(args.history, args.taps)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(qasm2.dumps(compiled))
    print(json.dumps({
        "qasm": str(args.out),
        "depth": compiled.depth(),
        "cx_count": compiled.count_ops().get("cx", 0),
        "width": compiled.num_qubits,
        "qubits_initially_zero": False,
    }, indent=2))


if __name__ == "__main__":
    main()
