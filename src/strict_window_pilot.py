"""Try exact-unitary resynthesis on a small set of profiled windows.

Candidates are spliced only when the selected ASAP layers form a contiguous
subcircuit on their active wires.  The original QASM is never overwritten.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile


def profile_layers(circuit):
    wire_level = [0] * circuit.num_qubits
    levels = []
    for inst in circuit.data:
        qs = [circuit.find_bit(q).index for q in inst.qubits]
        level = max((wire_level[q] for q in qs), default=0)
        levels.append(level)
        for q in qs:
            wire_level[q] = level + 1
    return levels


def make_window(circuit, levels, start, end):
    indices = [i for i, level in enumerate(levels) if start <= level <= end]
    if not indices:
        return None
    first, last = min(indices), max(indices)
    if indices != list(range(first, last + 1)):
        return None
    active = sorted({circuit.find_bit(q).index for i in indices for q in circuit.data[i].qubits})
    local = QuantumCircuit(len(active), global_phase=0)
    mapping = {circuit.qubits[q]: local.qubits[j] for j, q in enumerate(active)}
    for i in indices:
        inst = circuit.data[i]
        local.append(inst.operation, [mapping[q] for q in inst.qubits])
    return first, last, active, local


def splice(circuit, first, last, active, replacement):
    out = QuantumCircuit(circuit.num_qubits, global_phase=circuit.global_phase)
    for i, inst in enumerate(circuit.data):
        if i == first:
            for rep in replacement.data:
                out.append(rep.operation, [out.qubits[active[replacement.find_bit(q).index]] for q in rep.qubits])
        if first <= i <= last:
            continue
        out.append(inst.operation, [out.qubits[circuit.find_bit(q).index] for q in inst.qubits])
    return out


def run(path: Path, windows):
    circuit = qasm2.loads(path.read_text())
    levels = profile_layers(circuit)
    rows = []
    for start, end in windows:
        item = make_window(circuit, levels, start, end)
        row = {"start": start, "end": end}
        if item is None:
            row["status"] = "rejected_noncontiguous"
            rows.append(row)
            continue
        first, last, active, local = item
        row.update({"status": "tested", "gate_indices": [first, last], "active": active,
                    "input_depth": local.depth(), "input_cx": local.count_ops().get("cx", 0)})
        replacement = transpile(local, basis_gates=["u3", "cx"], optimization_level=3,
                                qubits_initially_zero=False)
        candidate = splice(circuit, first, last, active, replacement)
        row.update({"replacement_depth": replacement.depth(), "replacement_cx": replacement.count_ops().get("cx", 0),
                    "full_depth": candidate.depth(), "full_cx": candidate.count_ops().get("cx", 0),
                    "depth_delta": candidate.depth() - circuit.depth(),
                    "cx_delta": candidate.count_ops().get("cx", 0) - circuit.count_ops().get("cx", 0)})
        rows.append(row)
    return {"qasm": str(path.resolve()), "input_depth": circuit.depth(),
            "input_cx": circuit.count_ops().get("cx", 0), "windows": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.path, [(473, 482), (473, 487), (483, 487), (498, 504), (498, 507), (505, 507)])
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
