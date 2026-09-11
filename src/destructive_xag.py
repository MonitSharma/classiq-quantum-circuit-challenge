"""Exact destructive classifier compiler for an XOR--AND graph.

The compiler builds a reversible classifier C with one predicate wire:

    |x, y, 0^6> -> |garbage, f(x,y)>

It deliberately does not uncompute intermediate XAG values.  The caller can
form the exact oracle as C^dagger Z C, so all intermediate values are garbage
that is removed by the inverse.  Original input wires are recycled only after
their last logical consumer.  This module is intentionally conservative: it
uses the original-coordinate exact seed first and reports a hard failure when
the chosen topological order exceeds the available register file.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from md_xag import AndNode, XAG, logo_truth_table, mask_indices
from xag import linear_best


ROOT = Path(__file__).resolve().parents[1]
N_WIRES = 18
PREDICATE_WIRE = 17
SIGNAL_WIRES = tuple(range(17))


@dataclass(frozen=True)
class ParsedXAG:
    nodes: tuple[AndNode, ...]
    output_affine_mask: int

    @property
    def graph(self) -> XAG:
        return XAG(list(self.nodes), self.output_affine_mask)


def load_xag(path: Path) -> ParsedXAG:
    nodes: list[AndNode] = []
    output = None
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if fields[0] == "AND":
            if len(fields) != 3:
                raise ValueError(f"invalid AND line: {line}")
            nodes.append(AndNode(int(fields[1]), int(fields[2])))
        elif fields[0] == "OUTPUT":
            output = int(fields[1])
        else:
            raise ValueError(f"unknown XAG record: {line}")
    if output is None:
        raise ValueError(f"missing OUTPUT in {path}")
    parsed = ParsedXAG(tuple(nodes), output)
    if not parsed.graph.exact():
        raise ValueError(f"XAG is not exact for the logo: {path}")
    return parsed


def signal_last_use(parsed: ParsedXAG) -> list[int]:
    """Return the last node index that needs each signal.

    Node indices use the md_xag convention: inputs are 1..12 and AND nodes
    begin at 13.  The output affine mask is consumed at classifier start, so
    it does not keep original inputs live.
    """

    total = 13 + len(parsed.nodes)
    last = [0] * total
    for node_index, node in enumerate(parsed.nodes, start=13):
        for mask in (node.left_affine_mask, node.right_affine_mask):
            for signal in mask_indices(mask):
                last[signal] = max(last[signal], node_index)
    return last


def output_nodes(parsed: ParsedXAG) -> set[int]:
    return {signal for signal in mask_indices(parsed.output_affine_mask) if signal >= 13}


def one_signal_register_pressure(parsed: ParsedXAG, beam_width: int = 1000) -> dict:
    """Bound register pressure for one-pass topological XAG evaluation.

    This model gives every nonlinear signal its own register and consumes an
    output root immediately.  It is deliberately weaker than the intended
    affine-frame compiler, but it makes the first falsification checkpoint
    reproducible without constructing a quantum circuit.
    """

    ids = tuple(range(13, 13 + len(parsed.nodes)))
    dependencies: dict[int, set[int]] = {}
    uses: dict[int, list[int]] = {signal: [] for signal in range(13 + len(parsed.nodes))}
    for node_index, node in zip(ids, parsed.nodes):
        dependencies[node_index] = {
            signal
            for mask in (node.left_affine_mask, node.right_affine_mask)
            for signal in mask_indices(mask)
            if signal >= 13
        }
        for signal in {
            signal
            for mask in (node.left_affine_mask, node.right_affine_mask)
            for signal in mask_indices(mask)
        }:
            uses.setdefault(signal, []).append(node_index)
    initial_remaining = tuple(len(uses.get(signal, [])) for signal in range(13 + len(parsed.nodes)))
    # (peak, active_now, order, active_set, remaining_use_counts)
    beam = [(12, 12, tuple(), frozenset(range(1, 13)), initial_remaining)]
    for _ in ids:
        candidates = []
        for peak, _, order, active, remaining in beam:
            done = set(order)
            ready = [node for node in ids if node not in done and dependencies[node] <= done]
            for node in ready:
                next_remaining = list(remaining)
                used = {
                    signal
                    for mask in (parsed.nodes[node - 13].left_affine_mask,
                                 parsed.nodes[node - 13].right_affine_mask)
                    for signal in mask_indices(mask)
                }
                for signal in used:
                    next_remaining[signal] -= 1
                next_active = set(active)
                next_active.add(node)
                for signal in tuple(next_active):
                    if next_remaining[signal] == 0:
                        next_active.remove(signal)
                next_peak = max(peak, len(active) + 1, len(next_active))
                candidates.append((
                    next_peak,
                    len(next_active),
                    order + (node,),
                    frozenset(next_active),
                    tuple(next_remaining),
                ))
        candidates.sort(key=lambda item: (item[0], item[1], len(item[2])))
        beam = candidates[:beam_width]
    best = min(beam, key=lambda item: (item[0], item[1]))
    return {
        "model": "one_signal_per_wire_topological_beam",
        "beam_width": beam_width,
        "nodes": len(parsed.nodes),
        "minimum_observed_peak_registers": best[0],
        "available_wires": N_WIRES,
        "predicate_reserved_wires": 1,
        "available_signal_wires": N_WIRES - 1,
        "fits_reserved_predicate_register": best[0] <= N_WIRES - 1,
        "schedule": list(best[2]),
    }


def apply_affine_output(q: QuantumCircuit, mask: int, wire: dict[int, int]) -> None:
    """Accumulate the XAG's affine output into the predicate wire."""

    for signal in mask_indices(mask):
        if signal == 0:
            q.x(PREDICATE_WIRE)
        elif signal <= 12:
            q.cx(wire[signal - 1], PREDICATE_WIRE)
        else:
            # Nonlinear output signals are accumulated when their node is
            # created, after its physical wire has been allocated.
            continue


def compile_classifier(parsed: ParsedXAG) -> tuple[QuantumCircuit, dict]:
    """Compile one exact XAG into a reversible destructive classifier."""

    q = QuantumCircuit(N_WIRES)
    # xag.py names inputs 0..11 and nonlinear nodes 13.., while md_xag.py
    # names inputs 1..12 and nonlinear nodes 13... Translate only inputs.
    wire = {signal - 1: signal - 1 for signal in range(1, 13)}
    free = list(range(12, 17))
    last = signal_last_use(parsed)
    roots = output_nodes(parsed)
    apply_affine_output(q, parsed.output_affine_mask, wire)
    events = []
    peak = len(wire)

    def release(signal: int) -> None:
        if signal in wire:
            free.append(wire.pop(signal))
        free.sort()

    for node_index, node in enumerate(parsed.nodes, start=13):
        if not free:
            raise RuntimeError(
                f"register pressure exceeded 17 signal wires before node {node_index}; "
                f"live={sorted(wire)}"
            )
        left_mask = frozenset(
            -1 if signal == 0 else signal - 1 if signal <= 12 else signal
            for signal in mask_indices(node.left_affine_mask)
        )
        right_mask = frozenset(
            -1 if signal == 0 else signal - 1 if signal <= 12 else signal
            for signal in mask_indices(node.right_affine_mask)
        )
        pre, left, right = linear_best(q, left_mask, right_mask, wire)
        target = free.pop(0)
        q.compose(pre, inplace=True)
        q.rccx(left, right, target)
        q.compose(pre.inverse(), inplace=True)
        wire[node_index] = target
        if node_index in roots:
            q.cx(target, PREDICATE_WIRE)
        events.append({"node": node_index, "target": target, "left": left, "right": right})

        # A signal whose last use is this node can be recycled.  Its value is
        # no longer needed for C, and C^dagger will restore the original state.
        used = set(mask_indices(node.left_affine_mask)) | set(mask_indices(node.right_affine_mask))
        for signal in sorted(used):
            if signal != node_index and signal < len(last) and last[signal] == node_index:
                release(signal - 1 if 1 <= signal <= 12 else signal)
        peak = max(peak, len(wire))

    metrics = {
        "exact_xag": parsed.graph.exact(),
        "and_count": len(parsed.nodes),
        "output_node_count": len(roots),
        "forward_depth_untranspiled": q.depth(),
        "forward_cx_untranspiled": q.count_ops().get("cx", 0),
        "peak_logical_registers": peak,
        "predicate_wire": PREDICATE_WIRE,
        "remaining_signals": sorted(wire),
        "events": events,
    }
    return q, metrics


def build_oracle(path: Path) -> tuple[QuantumCircuit, dict]:
    parsed = load_xag(path)
    classifier, metrics = compile_classifier(parsed)
    oracle = classifier.inverse().compose(classifier)
    # The order must be C^dagger, Z, C when read left-to-right in the circuit.
    # Compose explicitly to avoid relying on an optimizer's interpretation.
    oracle = classifier.inverse()
    oracle.z(PREDICATE_WIRE)
    oracle.compose(classifier, inplace=True)
    metrics = dict(metrics)
    metrics.update({
        "oracle_depth_untranspiled": oracle.depth(),
        "oracle_cx_untranspiled": oracle.count_ops().get("cx", 0),
    })
    return oracle, metrics


def lower_exact(q: QuantumCircuit) -> QuantumCircuit:
    return transpile(
        q,
        basis_gates=["u3", "cx"],
        optimization_level=3,
        qubits_initially_zero=False,
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--xag", type=Path, default=ROOT / "artifacts/multiplicative_depth/seeds/shared_rank.xag")
    parser.add_argument("--classifier-qasm", type=Path)
    parser.add_argument("--oracle-qasm", type=Path)
    parser.add_argument("--metrics", type=Path)
    parser.add_argument("--pressure-report", type=Path)
    args = parser.parse_args()
    parsed = load_xag(args.xag)
    if args.pressure_report:
        args.pressure_report.write_text(
            json.dumps(one_signal_register_pressure(parsed), indent=2) + "\n"
        )
        print(json.dumps(one_signal_register_pressure(parsed), indent=2))
        if not args.oracle_qasm and not args.metrics and not args.classifier_qasm:
            return
    oracle, metrics = build_oracle(args.xag)
    if args.classifier_qasm:
        # Rebuild only for the optional diagnostic output.
        classifier, _ = compile_classifier(load_xag(args.xag))
        args.classifier_qasm.write_text(qasm2.dumps(lower_exact(classifier)))
    lowered = lower_exact(oracle)
    if args.oracle_qasm:
        args.oracle_qasm.write_text(qasm2.dumps(lowered))
    metrics.update({
        "oracle_depth_u3_cx": lowered.depth(),
        "oracle_cx_u3_cx": lowered.count_ops().get("cx", 0),
    })
    if args.metrics:
        args.metrics.write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
