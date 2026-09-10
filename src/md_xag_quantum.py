"""First quantum feasibility prototype for the exact streamed XAG phase basis."""

from __future__ import annotations

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from pebble_md import SeedGraph
from xag import build, linear, plan


ROOT = Path(__file__).resolve().parents[1]


def inverse_rows(rows: list[int]) -> list[int]:
    work = rows[:]
    result = [1 << i for i in range(12)]
    for col in range(12):
        pivot = next(row for row in range(col, 12) if work[row] & (1 << col))
        if pivot != col:
            work[col], work[pivot] = work[pivot], work[col]
            result[col], result[pivot] = result[pivot], result[col]
        for row in range(12):
            if row != col and (work[row] & (1 << col)):
                work[row] ^= work[col]
                result[row] ^= result[col]
    return result


def row_operations(target: list[int]) -> list[tuple[str, int, int]]:
    work = target[:]
    operations: list[tuple[str, int, int]] = []
    for col in range(12):
        pivot = next(row for row in range(col, 12) if work[row] & (1 << col))
        if pivot != col:
            work[col], work[pivot] = work[pivot], work[col]
            operations.append(("swap", col, pivot))
        for row in range(12):
            if row != col and (work[row] & (1 << col)):
                work[row] ^= work[col]
                operations.append(("xor", col, row))
    return list(reversed(operations))


def apply_basis(q: QuantumCircuit, rows: list[int], offset: int) -> None:
    for kind, control, target in row_operations(rows):
        if kind == "xor":
            q.cx(control, target)
        else:
            q.cx(control, target)
            q.cx(target, control)
            q.cx(control, target)
    for bit in range(12):
        if (offset >> bit) & 1:
            q.x(bit)


def affine_output_target(rows: list[int], offset: int) -> int:
    # z = A^{-1}(x + b), so z's affine offset is A^{-1}b.
    inverse = inverse_rows(rows)
    result = 0
    for bit, row in enumerate(inverse):
        if (row & offset).bit_count() & 1:
            result |= 1 << bit
    return result


def build_affine_stream(seed_path: str | None = None) -> QuantumCircuit:
    metadata = json.loads(
        (ROOT / "artifacts/multiplicative_depth/affine/shared_rank_search.json").read_text()
    )["best"]
    rows, offset = metadata["rows"], metadata["offset"]
    graph = SeedGraph(ROOT / (seed_path or metadata["seed"]))
    q = QuantumCircuit(18)
    inverse = inverse_rows(rows)
    apply_basis(q, inverse, affine_output_target(rows, offset))
    wire = {index: index for index in range(12)}
    live: set[int] = set()
    free = list(range(12, 18))

    def toggle(value: int) -> None:
        left, right = graph.nodes[value]
        pre, p, r = linear(q, left, right, wire)
        if value in live:
            target = wire[value]
        else:
            target = free.pop(0)
            wire[value] = target
        q.compose(pre, inplace=True)
        q.rccx(p, r, target)
        q.compose(pre.inverse(), inplace=True)
        if value in live:
            live.remove(value)
            free.append(wire.pop(value))
            free.sort()
        else:
            live.add(value)

    outputs = [index for index in range(13, 13 + len(graph.nodes)) if graph.output & (1 << index)]
    for output in outputs:
        path = plan(graph, frozenset(live), [frozenset([output])], limit=6)
        for value in path:
            toggle(value)
        q.z(wire[output])
        for value in plan(graph, frozenset(live), [], limit=6):
            toggle(value)
    if live:
        raise AssertionError("nonlinear values remain live")
    apply_basis(q, rows, offset)
    return q


def build_source_signal_stream(seed_path: str = "artifacts/multiplicative_depth/seeds/shared_rank.xag") -> QuantumCircuit:
    graph = SeedGraph(ROOT / seed_path)
    q = QuantumCircuit(18)
    wire = {index: index for index in range(12)}
    live: set[int] = set()
    free = list(range(12, 18))

    def toggle(value: int) -> None:
        left, right = graph.nodes[value]
        pre, p, r = linear(q, left, right, wire)
        if value in live:
            target = wire[value]
        else:
            target = free.pop(0)
            wire[value] = target
        q.compose(pre, inplace=True)
        q.rccx(p, r, target)
        q.compose(pre.inverse(), inplace=True)
        if value in live:
            live.remove(value)
            free.append(wire.pop(value))
            free.sort()
        else:
            live.add(value)

    outputs = [index for index in range(13, 13 + len(graph.nodes)) if graph.output & (1 << index)]
    for output in outputs:
        for value in plan(graph, frozenset(live), [frozenset([output])], limit=6):
            toggle(value)
        q.z(wire[output])
        for value in plan(graph, frozenset(live), [], limit=6):
            toggle(value)
    if live:
        raise AssertionError("nonlinear values remain live")
    return q


def main() -> None:
    terms = json.loads((ROOT / "artifacts/rank_terms.json").read_text())
    circuit, _, _ = build(terms, clear_each=True)
    lowered = transpile(
        circuit,
        basis_gates=["u3", "cx"],
        qubits_initially_zero=False,
        optimization_level=3,
    )
    out = ROOT / "artifacts/multiplicative_depth/md_rank_stream.qasm"
    out.write_text(qasm2.dumps(lowered))
    report = out.with_suffix(".exhaustive.json")
    print(json.dumps({
        "qasm": str(out),
        "width": lowered.num_qubits,
        "depth": lowered.depth(),
        "cx_count": lowered.count_ops().get("cx", 0),
        "qubits_initially_zero": False,
        "phase_history_streaming": True,
        "exhaustive_verification": str(report) if report.exists() else "pending",
    }, indent=2))

    balanced = transpile(
        build_source_signal_stream("artifacts/multiplicative_depth/optimized/shared_balance.xag"),
        basis_gates=["u3", "cx"],
        qubits_initially_zero=False,
        optimization_level=3,
    )
    balanced_out = ROOT / "artifacts/multiplicative_depth/md_balanced_signal_stream.qasm"
    balanced_out.write_text(qasm2.dumps(balanced))
    print(json.dumps({
        "qasm": str(balanced_out),
        "width": balanced.num_qubits,
        "depth": balanced.depth(),
        "cx_count": balanced.count_ops().get("cx", 0),
        "qubits_initially_zero": False,
        "phase_history_streaming": True,
        "exhaustive_verification": "pending",
    }, indent=2))

    optimized = transpile(
        build_affine_stream("artifacts/multiplicative_depth/optimized/affine_balance_118.xag"),
        basis_gates=["u3", "cx"],
        qubits_initially_zero=False,
        optimization_level=3,
    )
    optimized_out = ROOT / "artifacts/multiplicative_depth/md_optimized_affine_stream.qasm"
    optimized_out.write_text(qasm2.dumps(optimized))
    print(json.dumps({
        "qasm": str(optimized_out),
        "width": optimized.num_qubits,
        "depth": optimized.depth(),
        "cx_count": optimized.count_ops().get("cx", 0),
        "qubits_initially_zero": False,
        "phase_history_streaming": True,
        "exhaustive_verification": "pending",
    }, indent=2))

    signal = transpile(
        build_source_signal_stream(),
        basis_gates=["u3", "cx"],
        qubits_initially_zero=False,
        optimization_level=3,
    )
    signal_out = ROOT / "artifacts/multiplicative_depth/md_rank_signal_stream.qasm"
    signal_out.write_text(qasm2.dumps(signal))
    print(json.dumps({
        "qasm": str(signal_out),
        "width": signal.num_qubits,
        "depth": signal.depth(),
        "cx_count": signal.count_ops().get("cx", 0),
        "qubits_initially_zero": False,
        "phase_history_streaming": True,
        "exhaustive_verification": "pending",
    }, indent=2))

    affine = transpile(
        build_affine_stream(),
        basis_gates=["u3", "cx"],
        qubits_initially_zero=False,
        optimization_level=3,
    )
    affine_out = ROOT / "artifacts/multiplicative_depth/md_affine_stream.qasm"
    affine_out.write_text(qasm2.dumps(affine))
    print(json.dumps({
        "qasm": str(affine_out),
        "width": affine.num_qubits,
        "depth": affine.depth(),
        "cx_count": affine.count_ops().get("cx", 0),
        "qubits_initially_zero": False,
        "phase_history_streaming": True,
        "exhaustive_verification": "pending",
    }, indent=2))


if __name__ == "__main__":
    main()
