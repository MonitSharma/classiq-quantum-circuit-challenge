"""Integrate the direct five-output y loader into the full oracle skeleton.

This is an apples-to-apples diagnostic against ``full_mux``.  It loads
R0,R1,R2,A,B with the persistent output-frame loader, derives V=R1 OR R2
into q17, then reuses the original left-shape and disk-correction logic.
The relative-phase loader is deliberately checked by the complete oracle
verifier; no loader-only phase assumption is accepted here.
"""

from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from full_mux import multiplexer
from mcz import phase_cube
from pair_search import pair_circuit
from radius import radius, truth
from vector_output_frame_loader import build as build_loader


def build(seed: int = 0):
    loader = build_loader()
    q = loader.copy()

    # V = R1 OR R2, with q17 initially clean.
    q.cx(13, 17)
    q.cx(14, 17)
    q.ccx(13, 14, 17)

    xs = truth(range(2, 27))
    xb = truth(range(27, 49))
    xo = ((1 << 64) - 1) ^ xs ^ xb
    q.cx(17, 15)
    q.cx(17, 16)
    left = multiplexer([xs, xb, xo], [15, 16, 17], list(range(6)), "z", seed + 10000)
    q.compose(left, inplace=True)
    q.z(17)
    q.cx(17, 16)
    q.cx(17, 15)

    fold = QuantumCircuit(18)
    for k in range(4):
        fold.cx(11, k)
    fold.x(3)
    for k in range(3):
        fold.cx(3, k)
    fold.x(3)
    q.compose(fold, inplace=True)

    comp = QuantumCircuit(18)
    comp.x([0, 1, 2])
    carry = 3
    for i in range(3):
        comp.cx(12 + i, i)
        comp.cx(12 + i, carry)
        comp.rccx(carry, i, 12 + i)
        carry = 12 + i
    q.compose(comp, inplace=True)
    q.cx(11, 4)
    q.x(4)
    phase_cube(q, frozenset([18, 6, 5, 15]), [])
    q.x(4)
    q.cx(11, 4)
    q.compose(comp.inverse(), inplace=True)
    q.compose(fold.inverse(), inplace=True)

    # Uncompute V before reversing the five-output loader.
    q.ccx(13, 14, 17)
    q.cx(14, 17)
    q.cx(13, 17)
    q.compose(loader.inverse(), inplace=True)
    q.compose(pair_circuit(truth([32, 48]), truth(range(17, 22))), inplace=True)
    return transpile(q, basis_gates=["u3", "cx"],
                     qubits_initially_zero=False, optimization_level=3)


def main() -> None:
    best = None
    for seed in range(8):
        candidate = build(seed)
        score = (candidate.depth(), candidate.count_ops().get("cx", 0))
        print(seed, score, flush=True)
        if best is None or score < best[0]:
            best = (score, candidate, seed)
    score, candidate, seed = best
    path = Path("artifacts/vector_loader_oracle_candidate.qasm")
    path.write_text(qasm2.dumps(candidate))
    Path("artifacts/vector_loader_oracle_candidate.metrics.json").write_text(
        '{\n'
        f'  "seed": {seed},\n  "depth": {score[0]},\n'
        f'  "cx": {score[1]},\n  "width": {candidate.num_qubits}\n'
        '}\n'
    )
    print({"seed": seed, "depth": score[0], "cx": score[1], "width": candidate.num_qubits})


if __name__ == "__main__":
    main()
