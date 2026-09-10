"""Profile a protected QASM circuit for depth-window resynthesis.

This is deliberately analysis-only: it never rewrites the input circuit.  The
ASAP/ALAP schedule is a resource schedule on the existing q[0:18] wires, so
the resulting windows are candidates for later exact or care-set synthesis.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from qiskit import qasm2


TOL = 1e-8


def near_multiple(value: float, unit: float) -> bool:
    return abs(value / unit - round(value / unit)) < TOL


def classify_u3(theta: float, phi: float, lam: float) -> str:
    """A coarse, phase-insensitive gate family label for prioritisation."""
    if abs(math.sin(theta / 2.0)) < TOL:
        return "diagonal"
    if near_multiple(theta, math.pi / 2) and near_multiple(phi, math.pi / 2) and near_multiple(lam, math.pi / 2):
        return "clifford"
    if abs(abs((theta + math.pi) % (2 * math.pi)) - math.pi) < TOL:
        return "x/y-like"
    return "general"


def profile(path: Path) -> dict:
    source = path.read_text()
    circuit = qasm2.loads(source)
    gates = []
    wire_count = circuit.num_qubits
    asap_wire = [0] * wire_count

    # QASM emitted by the repository is already topologically ordered.  The
    # recurrence below also works for any gate list with that property.
    for index, inst in enumerate(circuit.data):
        qubits = [circuit.find_bit(bit).index for bit in inst.qubits]
        start = max((asap_wire[q] for q in qubits), default=0)
        name = inst.operation.name
        if name == "cx":
            family = "cx"
        elif name == "u3":
            family = classify_u3(*(float(x) for x in inst.operation.params))
        else:
            family = name
        gate = {"index": index, "name": name, "family": family,
                "qubits": qubits, "asap": start}
        gates.append(gate)
        for q in qubits:
            asap_wire[q] = start + 1

    depth = max((g["asap"] for g in gates), default=-1) + 1
    # Reverse recurrence gives the latest legal start while preserving the
    # exact gate order and the circuit's qubit-wise dependencies.
    next_wire = [depth] * wire_count
    for gate in reversed(gates):
        latest = min((next_wire[q] for q in gate["qubits"]), default=depth) - 1
        gate["alap"] = latest
        gate["slack"] = latest - gate["asap"]
        for q in gate["qubits"]:
            next_wire[q] = latest

    layers = []
    for level in range(depth):
        members = [g for g in gates if g["asap"] == level]
        layers.append({
            "level": level,
            "gate_count": len(members),
            "cx": sum(g["family"] == "cx" for g in members),
            "u3": sum(g["name"] == "u3" for g in members),
            "critical_gate_count": sum(g["slack"] == 0 for g in members),
            "qubits": sorted({q for g in members for q in g["qubits"]}),
            "families": {f: sum(g["family"] == f for g in members)
                         for f in sorted({g["family"] for g in members})},
        })

    per_qubit = []
    for q in range(wire_count):
        touched = [g for g in gates if q in g["qubits"]]
        per_qubit.append({
            "qubit": q,
            "gate_count": len(touched),
            "cx_count": sum(g["family"] == "cx" for g in touched),
            "critical_gate_count": sum(g["slack"] == 0 for g in touched),
            "first_level": min((g["asap"] for g in touched), default=None),
            "last_level": max((g["asap"] for g in touched), default=None),
        })

    # Maximal ASAP-layer runs containing only CNOTs and diagonal U3s.
    phase_regions = []
    start = None
    for level, layer in enumerate(layers + [{"families": {"other": 1}}]):
        allowed = bool(layer["families"]) and set(layer["families"]) <= {"cx", "diagonal"}
        if allowed and start is None:
            start = level
        if not allowed and start is not None:
            region_layers = layers[start:level]
            phase_regions.append({
                "start": start, "end": level - 1, "depth": level - start,
                "cx": sum(x["cx"] for x in region_layers),
                "gate_count": sum(x["gate_count"] for x in region_layers),
                "qubits": sorted({q for x in region_layers for q in x["qubits"]}),
            })
            start = None

    # Score sliding windows by the plan's depth * critical fraction * CX density.
    candidates = []
    for width in (8, 16, 24, 32, 40):
        for start in range(0, max(0, depth - width + 1)):
            window = layers[start:start + width]
            gate_count = sum(x["gate_count"] for x in window)
            cx = sum(x["cx"] for x in window)
            critical = sum(x["critical_gate_count"] for x in window)
            if gate_count == 0:
                continue
            candidates.append({
                "start": start, "end": start + width - 1, "depth": width,
                "gate_count": gate_count, "cx": cx,
                "critical_fraction": critical / gate_count,
                "cx_density": cx / gate_count,
                "priority": width * (critical / gate_count) * (cx / gate_count),
                "qubits": sorted({q for x in window for q in x["qubits"]}),
            })
    candidates.sort(key=lambda x: (x["priority"], x["critical_fraction"], x["cx"]), reverse=True)
    # Keep non-overlapping-ish representatives so the pilot does not select
    # ten copies of one hot region.
    selected = []
    for candidate in candidates:
        if all(candidate["end"] < old["start"] - 4 or candidate["start"] > old["end"] + 4
               for old in selected):
            selected.append(candidate)
        if len(selected) == 10:
            break

    counts = {}
    for gate in gates:
        counts[gate["family"]] = counts.get(gate["family"], 0) + 1
    return {
        "qasm": str(path.resolve()),
        "sha256": hashlib.sha256(source.encode()).hexdigest(),
        "width": wire_count,
        "depth": depth,
        "cx_count": sum(g["family"] == "cx" for g in gates),
        "gate_count": len(gates),
        "gate_family_counts": counts,
        "critical_gate_count": sum(g["slack"] == 0 for g in gates),
        "per_qubit": per_qubit,
        "layers": layers,
        "phase_regions": sorted(phase_regions, key=lambda x: (x["depth"], x["cx"]), reverse=True),
        "top_windows": selected,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = profile(args.path)
    output = args.output or args.path.with_name(args.path.stem + ".window_profile.json")
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("qasm", "sha256", "width", "depth", "cx_count", "gate_family_counts", "critical_gate_count", "phase_regions", "top_windows")}, indent=2))


if __name__ == "__main__":
    main()
