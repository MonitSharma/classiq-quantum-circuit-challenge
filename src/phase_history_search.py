"""Phase-history synthesis primitives for the logo phase oracle.

This module deliberately separates Boolean history semantics from quantum
verification.  A historical signal is a 4096-bit truth table that existed on
a physical wire at a particular point in a reversible trajectory.  If the
target is in the GF(2) span of those signals, Z taps at their provenance
points, followed by the exact inverse trajectory, implement the target phase.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from qiskit import QuantumCircuit, qasm2, transpile
from qiskit.circuit.library import RC3XGate, RCCXGate

from destructive_semantic_search import (
    ALL_ONES,
    N_INPUTS,
    N_WIRES,
    TARGET,
    apply_rccx_semantic,
    initial_wire_truth_tables,
)


Gate = tuple


def truth_table_hash(value: int) -> str:
    return hashlib.blake2b(
        value.to_bytes((N_INPUTS + 7) // 8, "little"), digest_size=12
    ).hexdigest()


@dataclass(frozen=True)
class Signal:
    signal_id: int
    value: int
    step: int
    wire: int
    value_hash: str


class HistoricalBasis:
    """Incremental GF(2) basis with recoverable signal provenance."""

    def __init__(self) -> None:
        self.signals: list[Signal] = []
        self.pivots: dict[int, tuple[int, int]] = {}
        self.first_signal_for_value: dict[int, int] = {}
        self.occurrences: dict[int, list[tuple[int, int]]] = {}
        self.add(ALL_ONES, 0, -1, "constant-one")

    def add(self, value: int, step: int, wire: int, label: str = "") -> int:
        """Record a signal and insert it if it increases the span.

        The returned ID always identifies the canonical signal for ``value``.
        Duplicate values retain all occurrence locations while avoiding rank
        inflation.
        """
        if value in self.first_signal_for_value:
            signal_id = self.first_signal_for_value[value]
            self.occurrences.setdefault(signal_id, []).append((step, wire))
            return signal_id
        signal_id = len(self.signals)
        signal = Signal(signal_id, value, step, wire, truth_table_hash(value))
        self.signals.append(signal)
        self.first_signal_for_value[value] = signal_id
        self.occurrences[signal_id] = [(step, wire)]
        coeff = 1 << signal_id
        reduced = value
        while reduced:
            pivot = reduced.bit_length() - 1
            old = self.pivots.get(pivot)
            if old is None:
                self.pivots[pivot] = (reduced, coeff)
                break
            reduced ^= old[0]
            coeff ^= old[1]
        return signal_id

    @property
    def rank(self) -> int:
        return len(self.pivots)

    def solve(self, target: int) -> tuple[int, int] | None:
        """Return ``(coefficient_mask, constant_bit)`` or ``None``."""
        reduced = target
        coeff = 0
        while reduced:
            pivot = reduced.bit_length() - 1
            old = self.pivots.get(pivot)
            if old is None:
                return None
            reduced ^= old[0]
            coeff ^= old[1]
        constant_id = self.first_signal_for_value[ALL_ONES]
        return coeff & ~(1 << constant_id), int(bool(coeff & (1 << constant_id)))

    def remainder(self, target: int) -> int:
        """Return the deterministic Gaussian-elimination remainder."""
        reduced = target
        while reduced:
            pivot = reduced.bit_length() - 1
            old = self.pivots.get(pivot)
            if old is None:
                break
            reduced ^= old[0]
        return reduced

    def greedy_residual(self, target: int) -> int:
        """Heuristic Hamming residual using repeated improving signals.

        This is intentionally not presented as a minimum-distance calculation;
        it only gives the beam a target-correlation signal before exact span
        membership is reached.
        """
        residual = target
        while True:
            best = residual
            best_distance = residual.bit_count()
            for signal in self.signals:
                candidate = residual ^ signal.value
                distance = candidate.bit_count()
                if distance < best_distance:
                    best, best_distance = candidate, distance
            if best == residual:
                return residual
            residual = best

    def provenance(self, target: int = TARGET) -> dict | None:
        solved = self.solve(target)
        if solved is None:
            return None
        mask, constant = solved
        selected = [self.signals[i] for i in range(len(self.signals))
                    if mask & (1 << i)]
        return {
            "constant": constant,
            "signal_ids": [s.signal_id for s in selected],
            "taps": [
                {
                    "step": s.step,
                    "wire": s.wire,
                    "signal_id": s.signal_id,
                    "truth_table_hash": s.value_hash,
                }
                for s in selected
                if s.step >= 0 and s.wire >= 0
            ],
        }

    def reconstruct(self, target: int) -> int | None:
        solved = self.solve(target)
        if solved is None:
            return None
        mask, constant = solved
        value = ALL_ONES if constant else 0
        for signal_id, signal in enumerate(self.signals):
            if mask & (1 << signal_id):
                value ^= signal.value
        return value


def apply_gate_semantic(wires: tuple[int, ...], gate: Gate) -> tuple[int, ...]:
    kind = gate[0]
    if kind == "x":
        out = list(wires)
        out[gate[1]] ^= ALL_ONES
        return tuple(out)
    if kind == "cx":
        out = list(wires)
        out[gate[2]] ^= out[gate[1]]
        return tuple(out)
    if kind == "rccx":
        return apply_rccx_semantic(wires, gate[1], gate[2], gate[3])
    if kind in {"rc3x", "rcccx"}:
        _, a, b, c, target = gate
        out = list(wires)
        out[target] ^= out[a] & out[b] & out[c]
        return tuple(out)
    raise ValueError(f"unsupported semantic gate: {gate}")


def replay_history(
    gates: Sequence[Gate], initial: tuple[int, ...] | None = None,
) -> tuple[tuple[int, ...], HistoricalBasis, list[tuple[int, ...]]]:
    """Replay a primitive trajectory and collect every new target signal."""
    wires = initial if initial is not None else initial_wire_truth_tables()
    basis = HistoricalBasis()
    for wire, value in enumerate(wires):
        basis.add(value, 0, wire, "initial")
    snapshots = [wires]
    for step, gate in enumerate(gates, start=1):
        before = wires
        wires = apply_gate_semantic(wires, gate)
        if wires == before:
            snapshots.append(wires)
            continue
        if gate[0] == "x":
            touched_targets = (gate[1],)
        elif gate[0] == "cx":
            touched_targets = (gate[2],)
        elif gate[0] == "rccx":
            touched_targets = (gate[3],)
        elif gate[0] in {"rc3x", "rcccx"}:
            touched_targets = (gate[4],)
        else:
            raise ValueError(f"unsupported semantic gate: {gate}")
        for wire in touched_targets:
            basis.add(wires[wire], step, wire, gate[0])
        snapshots.append(wires)
    return wires, basis, snapshots


def gates_from_json(path: Path) -> tuple[Gate, ...]:
    records = json.loads(path.read_text())
    return tuple(tuple(gate) for gate in records["gates"])


def gates_from_circuit(circuit: QuantumCircuit) -> tuple[Gate, ...]:
    gates: list[Gate] = []
    for instruction in circuit.data:
        name = instruction.operation.name
        wires = tuple(circuit.find_bit(q).index for q in instruction.qubits)
        if name == "rccx":
            gates.append(("rccx", *wires))
        elif name in {"rc3x", "rcccx"}:
            gates.append(("rc3x", *wires))
        elif name == "cx":
            gates.append(("cx", *wires))
        elif name == "x":
            gates.append(("x", wires[0]))
        else:
            raise ValueError(f"non-primitive operation in history: {name}")
    return tuple(gates)


def _append_gate(circuit: QuantumCircuit, gate: Gate, inverse: bool = False) -> None:
    kind = gate[0]
    if kind == "x":
        circuit.x(gate[1])
    elif kind == "cx":
        circuit.cx(gate[1], gate[2])
    elif kind == "rccx":
        operation = RCCXGate()
        circuit.append(operation.inverse() if inverse else operation,
                       [gate[1], gate[2], gate[3]])
    elif kind in {"rc3x", "rcccx"}:
        operation = RC3XGate()
        circuit.append(operation.inverse() if inverse else operation,
                       [gate[1], gate[2], gate[3], gate[4]])
    else:
        raise ValueError(f"unsupported quantum gate: {gate}")


def build_phase_history_circuit(
    gates: Sequence[Gate], taps: Iterable[dict], n_qubits: int = N_WIRES,
) -> QuantumCircuit:
    """Build forward, historical Z taps, and exact reverse trajectory."""
    by_step: dict[int, list[int]] = {}
    for tap in taps:
        by_step.setdefault(int(tap["step"]), []).append(int(tap["wire"]))
    circuit = QuantumCircuit(n_qubits)
    for step in range(len(gates) + 1):
        for wire in sorted(set(by_step.get(step, []))):
            circuit.z(wire)
        if step < len(gates):
            _append_gate(circuit, gates[step])
    for gate in reversed(gates):
        _append_gate(circuit, gate, inverse=True)
    return circuit


def compile_u3_cx(circuit: QuantumCircuit) -> QuantumCircuit:
    return transpile(
        circuit,
        basis_gates=["u3", "cx"],
        qubits_initially_zero=False,
        optimization_level=3,
    )


def audit(gates: Sequence[Gate]) -> dict:
    final_wires, basis, _ = replay_history(gates)
    solution = basis.provenance(TARGET)
    reconstructed = basis.reconstruct(TARGET)
    return {
        "primitive_count": len(gates),
        "historical_unique_signals": len(basis.signals),
        "historical_rank": basis.rank,
        "target_marked_states": TARGET.bit_count(),
        "target_in_history_span": solution is not None,
        "target_reconstructed_exactly": reconstructed == TARGET,
        "complement_reconstructed_exactly": reconstructed == (TARGET ^ ALL_ONES),
        "tap_count": len(solution["taps"]) if solution else 0,
        "final_semantic_hash": hashlib.blake2b(
            b"".join(v.to_bytes((N_INPUTS + 7) // 8, "little")
                     for v in final_wires), digest_size=16
        ).hexdigest(),
        "gate_kinds": {kind: sum(g[0] == kind for g in gates)
                       for kind in sorted({g[0] for g in gates})},
        "provenance": solution,
    }


@dataclass(frozen=True)
class HistoryState:
    wires: tuple[int, ...]
    gates: tuple[Gate, ...]
    basis: HistoricalBasis
    estimated_depth: int


def history_state(gates: Sequence[Gate], depth: int = 0) -> HistoryState:
    wires, basis, _ = replay_history(gates)
    return HistoryState(wires, tuple(gates), basis, depth)


def history_score(state: HistoryState) -> tuple:
    remainder = state.basis.remainder(TARGET)
    greedy = state.basis.greedy_residual(TARGET)
    best_single = min(
        (TARGET ^ signal.value).bit_count()
        for signal in state.basis.signals
        if signal.step >= 0
    )
    return (
        0 if state.basis.solve(TARGET) is not None else 1,
        greedy.bit_count(),
        best_single,
        remainder.bit_count(),
        -state.basis.rank,
        state.estimated_depth,
        truth_table_hash(state.wires[0]),
    )


def history_proposals(
    state: HistoryState, limit: int, rng: random.Random,
) -> list[tuple[int, int, int]]:
    """Generate bounded RCCX proposals using history-aware cheap filters."""
    target_remainder = state.basis.remainder(TARGET)
    proposals = []
    for a in range(N_WIRES):
        for b in range(a + 1, N_WIRES):
            product = state.wires[a] & state.wires[b]
            if not product:
                continue
            for target in range(N_WIRES):
                if target in (a, b):
                    continue
                new_value = state.wires[target] ^ product
                if new_value == state.wires[target]:
                    continue
                # This is only a proposal filter. Exact ranking rebuilds the
                # complete cumulative basis for each retained child.
                novelty = 0 if new_value in state.basis.first_signal_for_value else 1
                distance = (target_remainder ^ new_value).bit_count()
                direct = (TARGET ^ new_value).bit_count()
                proposals.append((novelty, min(distance, direct), rng.random(),
                                  a, b, target))
    proposals.sort()
    return [(a, b, target) for _, _, _, a, b, target in proposals[:limit]]


def search_history(
    beam_width: int = 16,
    layers: int = 4,
    proposal_limit: int = 64,
    seed: int = 0,
    checkpoint_dir: Path | None = None,
) -> tuple[HistoryState, int]:
    """Run a small deterministic history-span beam search.

    This first implementation intentionally uses single RCCX moves. It is a
    bounded diagnostic for the new objective; layer moves can be added after
    the scoring behavior is characterized.
    """
    rng = random.Random(seed)
    beam = [history_state(())]
    best = beam[0]
    for layer in range(1, layers + 1):
        children: list[HistoryState] = []
        for state in beam:
            for a, b, target in history_proposals(state, proposal_limit, rng):
                gates = state.gates + (("rccx", a, b, target),)
                child = history_state(gates, layer * 7)
                children.append(child)
        children.sort(key=history_score)
        beam = children[:beam_width]
        if not beam:
            break
        if history_score(beam[0]) < history_score(best):
            best = beam[0]
        print(json.dumps({
            "layer": layer,
            "beam": len(beam),
            "best_score": history_score(beam[0])[:4],
            "best_rank": beam[0].basis.rank,
            "best_remainder_bits": beam[0].basis.remainder(TARGET).bit_count(),
            "target_in_span": beam[0].basis.solve(TARGET) is not None,
        }), flush=True)
        if checkpoint_dir is not None:
            checkpoint_dir.mkdir(parents=True, exist_ok=True)
            with (checkpoint_dir / f"history_layer_{layer:03d}.pkl").open("wb") as handle:
                pickle.dump({"layer": layer, "beam": beam, "best": best}, handle,
                            protocol=pickle.HIGHEST_PROTOCOL)
        found = next((item for item in beam if item.basis.solve(TARGET) is not None), None)
        if found is not None:
            return found, layer
    return best, layers


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-json", type=Path)
    parser.add_argument("--audit-fused-tail", action="store_true")
    parser.add_argument("--search", action="store_true")
    parser.add_argument("--beam", type=int, default=16)
    parser.add_argument("--layers", type=int, default=4)
    parser.add_argument("--proposal-limit", type=int, default=64)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--checkpoint-dir", type=Path)
    parser.add_argument("--out", type=Path,
                        default=Path("artifacts/phase_history"))
    args = parser.parse_args()
    if args.search:
        result, completed_layer = search_history(
            beam_width=args.beam,
            layers=args.layers,
            proposal_limit=args.proposal_limit,
            seed=args.seed,
            checkpoint_dir=args.checkpoint_dir or args.out / "checkpoints",
        )
        args.out.mkdir(parents=True, exist_ok=True)
        payload = {
            "mode": "history_beam_diagnostic",
            "seed": args.seed,
            "beam_width": args.beam,
            "layers": args.layers,
            "proposal_limit": args.proposal_limit,
            "completed_layer": completed_layer,
            "history_rank": result.basis.rank,
            "remainder_bits": result.basis.remainder(TARGET).bit_count(),
            "target_in_span": result.basis.solve(TARGET) is not None,
            "estimated_forward_depth": result.estimated_depth,
            "gates": [list(gate) for gate in result.gates],
            "provenance": result.basis.provenance(TARGET),
        }
        output = args.out / f"search_seed{args.seed}_beam{args.beam}_layers{args.layers}.json"
        output.write_text(json.dumps(payload, indent=2) + "\n")
        print(json.dumps(payload, indent=2))
        return
    if args.audit_fused_tail:
        from high_order_affine_fused_tail import build_chain
        gates = gates_from_circuit(build_chain()[0])
        name = "fused_tail"
    elif args.audit_json:
        gates = gates_from_json(args.audit_json)
        name = args.audit_json.stem
    else:
        parser.error("choose --audit-json or --audit-fused-tail")
    result = audit(gates)
    args.out.mkdir(parents=True, exist_ok=True)
    output = args.out / f"audit_{name}.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
