"""Comparator-free disk phase pilot using threshold/parity radius features.

The existing fold maps the two disk centres to one folded coordinate.  On the
guarded region (folded x5=1 and folded x4=y5), the remaining disk predicate
is a linear parity of five y features:

    V=[r>0], L=[r>=4], T=[r>=6], P=r&1, Q=T&P.

This module keeps the verified six-output loader and left-shape phase from
``full_mux``.  It replaces only the Cuccaro comparator and its phase cube by
feature-controlled x multiplexors.  T and Q are computed into dirty V with
compute/diagonal/uncompute, so their relative phases cancel around the
diagonal phase blocks.
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
from radius import radius, truth, R
from search import esop, logo

ROOT = Path(__file__).resolve().parents[1]
FULL = (1 << 64) - 1


def disk_marked(x: int, y: int) -> bool:
    """The disk component only; square/bar are already handled by left phase."""
    return ((x - 55) ** 2 + (y - 41) ** 2 <= 42 or
            (x - 40) ** 2 + (y - 19) ** 2 <= 72)


def fold_value(x: int, y5: int) -> int:
    """Classical action of the exact fold circuit used by full_mux."""
    for k in range(4):
        if y5:
            x ^= 1 << k
    x ^= 1 << 3
    for k in range(3):
        if (x >> 3) & 1:
            x ^= 1 << k
    x ^= 1 << 3
    return x & 63


def unfold_value(x: int, y5: int) -> int:
    """Inverse of ``fold_value`` (the fold is not self-inverse)."""
    x ^= 1 << 3
    for k in reversed(range(3)):
        if (x >> 3) & 1:
            x ^= 1 << k
    x ^= 1 << 3
    for k in reversed(range(4)):
        if y5:
            x ^= 1 << k
    return x & 63


def feature_bits(y: int) -> tuple[int, int, int, int, int, int]:
    r = radius(y)
    y5 = (y >> 5) & 1
    # B is already loaded by the trusted six-output architecture and equals
    # y5 AND [r>=6].  It is the extra basis vector needed for every folded row.
    return (int(r > 0), int(r >= 4), int(r >= 6), r & 1,
            int(r >= 6) & (r & 1), y5 & int(r >= 6))


def coefficient_masks() -> list[int | None]:
    """Find the minimum-Hamming feature parity for each folded x.

    Only post-guard folded x values with x5=x4=1 participate.  The equality
    guard maps both relevant y halves to that same x4=1 slice.
    """
    out: list[int | None] = [None] * 64
    for xf in range(64):
        if ((xf >> 5) & 1) != 1 or ((xf >> 4) & 1) != 1:
            continue
        ys = list(range(64))
        rhs = []
        for y in ys:
            y5 = (y >> 5) & 1
            pre_guard = (xf & 15) | (y5 << 4) | (1 << 5)
            xo = unfold_value(pre_guard, y5)
            rhs.append(int(disk_marked(xo, y) and not
                           (xo in (32, 48) and 17 <= y <= 21)))
        candidates: list[tuple[int, int]] = []
        for mask in range(64):
            if all(sum(((mask >> i) & 1) * feature_bits(y)[i]
                       for i in range(6)) % 2 == bit
                       for y, bit in zip(ys, rhs)):
                candidates.append((mask.bit_count(), mask))
        if not candidates:
            raise AssertionError(f"no feature parity for folded x={xf}")
        out[xf] = min(candidates)[1]
    return out


def phase_tables(masks: list[int | None]) -> list[int]:
    tables = [0] * 6
    for x, mask in enumerate(masks):
        if mask is None:
            continue
        for i in range(6):
            if mask & (1 << i):
                tables[i] |= 1 << x
    return tables


def apply_feature_phase_esop(q: QuantumCircuit, table: int, target: int) -> None:
    """Apply the exact diagonal ``(-1)^(table(x)*target)``.

    A bare multiplexed RZ has an x-dependent zero-branch phase unless its
    tables form a partition.  The first pilot exposed that issue.  This exact
    ESOP version uses MCZ cubes, so it is suitable for a correctness test.
    """
    for mask, value in esop(table, 6):
        controls = {target + 1}
        for i in range(6):
            if mask & (1 << i):
                controls.add((i + 1) if (value & (1 << i)) else -(i + 1))
        phase_cube(q, frozenset(controls), [])


def build(seed: int = 94) -> QuantumCircuit:
    a = truth(range(29, 54))
    b = truth(range(39, 44))
    v = truth(y for y in range(64) if radius(y) > 0)
    lookup = multiplexer(R + [a, b, v], list(range(12, 18)),
                         list(range(6, 12)), "y", seed)
    q = lookup.copy()

    # Existing left-shape identity, unchanged from full_mux.
    xs, xb = truth(range(2, 27)), truth(range(27, 49))
    xo = FULL ^ xs ^ xb
    q.cx(17, 15)
    q.cx(17, 16)
    q.compose(multiplexer([xs, xb, xo], [15, 16, 17], list(range(6)),
                          "z", seed + 10000), inplace=True)
    q.z(17)
    q.cx(17, 16)
    q.cx(17, 15)

    # Fold and form the exact x4 == y5 guard.  The phase tables below are
    # zero unless x5=1 and the guard is satisfied.
    fold = QuantumCircuit(18)
    for k in range(4):
        fold.cx(11, k)
    fold.x(3)
    for k in range(3):
        fold.cx(3, k)
    fold.x(3)
    q.compose(fold, inplace=True)
    q.cx(11, 4)
    q.x(4)

    masks = coefficient_masks()
    tables = phase_tables(masks)

    # V, L=R2, and P=R0 are already available as targets.  Use exact phase
    # cubes rather than a bare RZ multiplexer (which has x-only branch phase).
    for table, target in ((tables[0], 17), (tables[1], 14),
                          (tables[3], 12), (tables[5], 16)):
        apply_feature_phase_esop(q, table, target)

    # T=R2&R1 into dirty V, phase, then restore V.  This pilot deliberately
    # uses exact Toffoli compute/uncompute: a relative-phase pair can leave a
    # control-dependent phase when the target is a nonzero dirty feature.
    if tables[2]:
        # Z_V * Z_(V XOR T) = Z_T, so the dirty target's pre-existing V
        # value is cancelled rather than mistaken for the computed feature.
        apply_feature_phase_esop(q, tables[2], 17)
        q.ccx(14, 13, 17)
        apply_feature_phase_esop(q, tables[2], 17)
        q.ccx(14, 13, 17)

    # Q=R2&R1&R0.  This pilot uses an exact no-ancilla MCX into dirty V;
    # unlike a clean-workspace assumption, the target is restored explicitly.
    if tables[4]:
        apply_feature_phase_esop(q, tables[4], 17)
        q.mcx([12, 13, 14], 17, mode="noancilla")
        apply_feature_phase_esop(q, tables[4], 17)
        q.mcx([12, 13, 14], 17, mode="noancilla")

    q.x(4)
    q.cx(11, 4)
    q.compose(fold.inverse(), inplace=True)
    q.compose(lookup.inverse(), inplace=True)
    q.compose(pair_circuit(truth([32, 48]), truth(range(17, 22))), inplace=True)
    return transpile(q, basis_gates=["u3", "cx"],
                     qubits_initially_zero=False, optimization_level=3,
                     seed_transpiler=seed)


def build_ucr_corrected(seed: int = 94) -> QuantumCircuit:
    """Bare-UCR phase-gadget pilot with its exact x-only branch correction."""
    a = truth(range(29, 54))
    b = truth(range(39, 44))
    v = truth(y for y in range(64) if radius(y) > 0)
    lookup = multiplexer(R + [a, b, v], list(range(12, 18)),
                         list(range(6, 12)), "y", seed)
    q = lookup.copy()
    xs, xb = truth(range(2, 27)), truth(range(27, 49))
    xo = FULL ^ xs ^ xb
    q.cx(17, 15); q.cx(17, 16)
    q.compose(multiplexer([xs, xb, xo], [15, 16, 17], list(range(6)),
                          "z", seed + 10000), inplace=True)
    q.z(17); q.cx(17, 16); q.cx(17, 15)

    fold = QuantumCircuit(18)
    for k in range(4): fold.cx(11, k)
    fold.x(3)
    for k in range(3): fold.cx(3, k)
    fold.x(3)
    q.compose(fold, inplace=True)
    q.cx(11, 4); q.x(4)
    tables = phase_tables(coefficient_masks())

    # Direct feature phases. Their UCR zero branch contributes -pi/2 per
    # active table entry; T and Q are each used twice around dirty compute.
    q.compose(multiplexer([tables[0], tables[1], tables[3]], [17, 14, 12],
                          list(range(6)), "z", seed + 500), inplace=True)
    q.compose(multiplexer([tables[2]], [17], list(range(6)), "z",
                          seed + 600), inplace=True)
    q.ccx(14, 13, 17)
    q.compose(multiplexer([tables[2]], [17], list(range(6)), "z",
                          seed + 601), inplace=True)
    q.ccx(14, 13, 17)
    q.compose(multiplexer([tables[4]], [17], list(range(6)), "z",
                          seed + 700), inplace=True)
    q.mcx([12, 13, 14], 17, mode="noancilla")
    q.compose(multiplexer([tables[4]], [17], list(range(6)), "z",
                          seed + 701), inplace=True)
    q.mcx([12, 13, 14], 17, mode="noancilla")

    # Cancel the branch phase. The table index is the post-fold/guarded x.
    h = [((tables[0] >> x) & 1) + ((tables[1] >> x) & 1)
         + ((tables[3] >> x) & 1)
         + 2 * ((tables[2] >> x) & 1)
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
    masks = coefficient_masks()
    print("masks", masks)
    best = None
    for seed in range(4):
        circuit = build(seed)
        score = (circuit.depth(), circuit.count_ops().get("cx", 0))
        print(seed, score, flush=True)
        if best is None or score < best[0]:
            best = (score, circuit)
    ucr_best = ((10**9, 10**9), None)
    for seed in range(2):
        circuit = build_ucr_corrected(seed)
        print("ucr_corrected", seed, (circuit.depth(),
              circuit.count_ops().get("cx", 0)), flush=True)
        if seed == 0 or (circuit.depth(), circuit.count_ops().get("cx", 0)) < ucr_best[0]:
            ucr_best = ((circuit.depth(), circuit.count_ops().get("cx", 0)), circuit)
    ucr_out = ROOT / "artifacts/threshold_phase_ucr_ucr_corrected_candidate.qasm"
    assert ucr_best[1] is not None
    ucr_out.write_text(qasm2.dumps(ucr_best[1]))
    ucr_metrics = {
        "qasm": str(ucr_out), "depth": ucr_best[0][0],
        "cx": ucr_best[0][1], "width": ucr_best[1].num_qubits,
        "sha256": hashlib.sha256(ucr_out.read_bytes()).hexdigest(),
        "status": "pending_exhaustive_verification",
        "representation": "UCR feature phases plus exact x-only branch correction",
    }
    (ROOT / "artifacts/threshold_phase_ucr_ucr_corrected_candidate.metrics.json").write_text(
        json.dumps(ucr_metrics, indent=2) + "\n")
    print(json.dumps(ucr_metrics, indent=2))
    assert best is not None
    out = ROOT / "artifacts/threshold_phase_ucr_candidate.qasm"
    out.write_text(qasm2.dumps(best[1]))
    metrics = {"qasm": str(out), "depth": best[0][0], "cx": best[0][1],
               "width": best[1].num_qubits,
               "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
               "coefficient_masks": masks,
               "status": "pending_exhaustive_verification"}
    (ROOT / "artifacts/threshold_phase_ucr_candidate.metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
