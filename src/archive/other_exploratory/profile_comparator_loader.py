"""Profile the failed serialized comparator y-loader probe."""

import json
from pathlib import Path

from qiskit import qasm2

from comparator_oracle_loader_probe import build_y_loader


def main():
    path = Path("artifacts/comparator_oracle/y_loader/y_loader_esop_probe.qasm")
    q = qasm2.loads(path.read_text())
    per_wire = []
    for wire in range(q.num_qubits):
        ops = {"u3": 0, "cx": 0, "total": 0}
        for inst in q.data:
            wires = [q.find_bit(v).index for v in inst.qubits]
            if wire in wires:
                name = inst.operation.name
                ops[name] = ops.get(name, 0) + 1
                ops["total"] += 1
        per_wire.append({"wire": wire, **ops})
    raw = build_y_loader()
    raw_ops = {name: int(count) for name, count in raw.count_ops().items()}
    profile = {
        "qasm": str(path),
        "depth": q.depth(),
        "cx_count": q.count_ops().get("cx", 0),
        "width": q.num_qubits,
        "per_wire": per_wire,
        "critical_wire_by_total": max(per_wire, key=lambda r: r["total"]),
        "critical_wire_by_cx": max(per_wire, key=lambda r: r["cx"]),
        "raw_pre_lowering_ops": raw_ops,
        "raw_pre_lowering_depth": raw.depth(),
        "interpretation": "serialized cost is dominated by repeated target/scratch participation; abstract predicate count is not the native metric",
    }
    out = Path("artifacts/comparator_oracle/y_loader/esop_failure_profile.json")
    out.write_text(json.dumps(profile, indent=2) + "\n")
    print(json.dumps(profile, indent=2))


if __name__ == "__main__":
    main()
