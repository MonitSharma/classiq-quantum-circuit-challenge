"""Comparator-free oracle using a threshold/parity feature encoding.

The six y outputs are [V, L, T, P, A, B].  The disk phase needs the extra
feature Q=T&P, which is computed into dirty V with an exact
compute/phase/uncompute identity.  This is separate from the protected
full_mux source and is always scored from standalone U3/CX QASM.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qasm2, transpile
from qiskit.circuit.library import DiagonalGate

from full_mux import multiplexer
from mcz import phase_cube
from pair_search import pair_circuit
from radius import radius, truth
from search import logo
from threshold_phase_ucr import coefficient_masks, phase_tables

ROOT = Path(__file__).resolve().parents[1]
FULL = (1 << 64) - 1


def build(seed: int = 94) -> QuantumCircuit:
    # Physical outputs: V,L,T,P,A,B.
    v = truth(y for y in range(64) if radius(y) > 0)
    l = truth(y for y in range(64) if radius(y) >= 4)
    t = truth(y for y in range(64) if radius(y) >= 6)
    p = truth(y for y in range(64) if radius(y) & 1)
    a = truth(range(29, 54))
    b = truth(range(39, 44))
    lookup = multiplexer([v, l, t, p, a, b], list(range(12, 18)),
                         list(range(6, 12)), "y", seed)
    q = lookup.copy()

    # Existing left-shape identity, with A=q16, B=q17, V=q12.
    xs, xb = truth(range(2, 27)), truth(range(27, 49))
    xo = FULL ^ xs ^ xb
    q.cx(12, 16); q.cx(12, 17)
    q.compose(multiplexer([xs, xb, xo], [16, 17, 12], list(range(6)),
                          "z", seed + 10000), inplace=True)
    q.z(12); q.cx(12, 17); q.cx(12, 16)

    # The coefficient tables are indexed by the post-fold/guarded x and
    # describe disk-only phase as V,L,T,P,Q parity.
    fold = QuantumCircuit(18)
    for k in range(4): fold.cx(11, k)
    fold.x(3)
    for k in range(3): fold.cx(3, k)
    fold.x(3)
    q.compose(fold, inplace=True)
    q.cx(11, 4); q.x(4)
    tables = phase_tables(coefficient_masks())

    # The first four features are final loaded targets.  A raw UCR has a
    # target-independent branch phase, so compensate it on x below.
    q.compose(multiplexer(tables[:4], [12, 13, 14, 15], list(range(6)),
                          "z", seed + 500), inplace=True)

    # Q=T&P into dirty V. Two diagonal phases synthesize Z_Q while canceling
    # the pre-existing V bit. Exact CCX keeps the pilot correctness proof
    # independent of relative-phase dirty-target assumptions.
    q.compose(multiplexer([tables[4]], [12], list(range(6)), "z",
                          seed + 600), inplace=True)
    q.ccx(14, 15, 12)
    q.compose(multiplexer([tables[4]], [12], list(range(6)), "z",
                          seed + 601), inplace=True)
    q.ccx(14, 15, 12)

    # Direct UCR branch correction: V,L,T,P once and Q twice.
    h = [sum((tables[i] >> x) & 1 for i in range(4))
         + 2 * ((tables[4] >> x) & 1) for x in range(64)]
    q.append(DiagonalGate([np.exp(1j * np.pi * z / 2) for z in h]),
                          list(range(6)))
    q.x(4); q.cx(11, 4)
    q.compose(fold.inverse(), inplace=True)
    q.compose(lookup.inverse(), inplace=True)
    q.compose(pair_circuit(truth([32, 48]), truth(range(17, 22))), inplace=True)
    return transpile(q, basis_gates=["u3", "cx"],
                     qubits_initially_zero=False, optimization_level=3,
                     seed_transpiler=seed)


def main() -> None:
    best = None
    for seed in range(8):
        circuit = build(seed)
        score = (circuit.depth(), circuit.count_ops().get("cx", 0))
        print(seed, score, flush=True)
        if best is None or score < best[0]:
            best = (score, circuit)
    assert best is not None
    out = ROOT / "artifacts/threshold_feature_oracle_candidate.qasm"
    out.write_text(qasm2.dumps(best[1]))
    metrics = {
        "qasm": str(out), "depth": best[0][0], "cx": best[0][1],
        "width": best[1].num_qubits,
        "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        "status": "pending_exhaustive_verification",
        "encoding": ["V", "L", "T", "P", "A", "B"],
    }
    (ROOT / "artifacts/threshold_feature_oracle_candidate.metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
