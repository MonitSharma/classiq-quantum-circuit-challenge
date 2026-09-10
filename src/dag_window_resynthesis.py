"""Inventory causal DAG windows in the protected 524 QASM.

This milestone is intentionally bounded and analysis-only.  It distinguishes
serialized interleaving from a real dependency crossing; it does not rewrite
or score a replacement circuit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from qiskit import qasm2


def build_gates(circuit):
    previous = {}
    gates = []
    for index, inst in enumerate(circuit.data):
        qubits = tuple(circuit.find_bit(q).index for q in inst.qubits)
        predecessors = sorted({previous[q] for q in qubits if q in previous})
        gate = {"index": index, "name": inst.operation.name, "qubits": list(qubits),
                "predecessors": predecessors}
        gates.append(gate)
        for q in qubits:
            previous[q] = index

    # ASAP levels on the dependency DAG.
    for gate in gates:
        gate["asap"] = max((gates[p]["asap"] + 1 for p in gate["predecessors"]), default=0)
    successors = [[] for _ in gates]
    for gate in gates:
        for p in gate["predecessors"]:
            successors[p].append(gate["index"])
    for gate, succ in zip(gates, successors):
        gate["successors"] = succ
    depth = max((g["asap"] for g in gates), default=-1) + 1
    for gate in reversed(gates):
        gate["alap"] = min((gates[s]["alap"] - 1 for s in gate["successors"]), default=depth - 1)
        gate["slack"] = gate["alap"] - gate["asap"]
    return gates


def close_window(gates, seed, start, end, max_qubits):
    """Return the gates touching a bounded active-wire causal slab."""
    active = set(gates[seed]["qubits"])
    changed = True
    while changed:
        changed = False
        for gate in gates:
            if start <= gate["asap"] <= end and active.intersection(gate["qubits"]):
                old = len(active)
                active.update(gate["qubits"])
                changed |= len(active) != old
                if len(active) > max_qubits:
                    return None
    members = [g for g in gates if start <= g["asap"] <= end and active.intersection(g["qubits"])]
    member_ids = {g["index"] for g in members}
    # A dependency is a true crossing only if it enters from a gate on an
    # outside wire inside the slab.  Boundary predecessors before start are
    # legal frontiers; operations on entirely disjoint wires are spectators.
    crossings = []
    for gate in members:
        for p in gate["predecessors"]:
            if p not in member_ids and start <= gates[p]["asap"] <= end:
                crossings.append((p, gate["index"]))
    return active, members, crossings


def inventory(path: Path) -> dict:
    source = path.read_text()
    circuit = qasm2.loads(source)
    gates = build_gates(circuit)
    depth = max((g["asap"] for g in gates), default=-1) + 1
    critical = [g for g in gates if g["slack"] == 0]
    candidates = []
    for seed in [g["index"] for g in gates if g["asap"] < depth and g["index"] % 7 == 0]:
        for width in (12, 20, 32, 50):
            center = gates[seed]["asap"]
            start, end = max(0, center - width // 3), min(depth - 1, center + width * 2 // 3)
            for limit in (3, 4, 5, 6):
                closed = close_window(gates, seed, start, end, limit)
                if closed is None:
                    continue
                active, members, crossings = closed
                if not members or crossings:
                    continue
                candidates.append({
                    "seed_gate": seed, "start": start, "end": end,
                    "causal_depth": end - start + 1, "active_qubits": sorted(active),
                    "gate_count": len(members),
                    "cx_count": sum(g["name"] == "cx" for g in members),
                    "serialized_first": min(g["index"] for g in members),
                    "serialized_last": max(g["index"] for g in members),
                    "serialized_interleaved": len(members) != max(g["index"] for g in members) - min(g["index"] for g in members) + 1,
                    "critical_seed": gates[seed]["slack"] == 0,
                    "score": (end - start + 1) * (sum(g["name"] == "cx" for g in members) + 1) / len(active),
                })
    # Deduplicate by causal slab and active set; retain the highest score.
    unique = {}
    for row in candidates:
        key = (row["start"], row["end"], tuple(row["active_qubits"]))
        if key not in unique or row["score"] > unique[key]["score"]:
            unique[key] = row
    ranked = sorted(unique.values(), key=lambda x: (x["score"], x["causal_depth"]), reverse=True)
    return {
        "qasm": str(path.resolve()),
        "sha256": hashlib.sha256(source.encode()).hexdigest(),
        "width": circuit.num_qubits, "depth": circuit.depth(),
        "cx_count": circuit.count_ops().get("cx", 0),
        "dag_gate_count": len(gates),
        "critical_gate_count": len(critical),
        "max_active_qubits": 6,
        "candidate_count": len(ranked),
        "top_windows": ranked[:20],
        "status": "inventory_only_no_replacement_synthesized",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = inventory(args.path)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
