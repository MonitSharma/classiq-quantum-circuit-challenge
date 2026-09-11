"""Native 3+3-ancilla affine-isometry probe.

This is a focused candidate generator, not a complete oracle.  It uses five
linear garbage parities, computes three code bits into the three clean wires,
and overwrites one data bit with a degree-bounded care-set correction.
"""

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from comparator_oracle_structure import X_C, X_LVL, Y_B, Y_M
from search import esop, truth


def rank2(rows):
    rows = list(rows); rank = 0
    for bit in range(6):
        pivot = next((i for i in range(rank, len(rows)) if rows[i] >> bit & 1), None)
        if pivot is None: continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for i in range(len(rows)):
            if i != rank and rows[i] >> bit & 1: rows[i] ^= rows[rank]
        rank += 1
    return rank


def linear_circuit(rows):
    """CNOT circuit mapping input bits to output parities given by rows."""
    a = list(rows); ops = []
    for col in range(6):
        pivot = next(i for i in range(col, 6) if a[i] >> col & 1)
        if pivot != col:
            for c, t in ((col, pivot), (pivot, col), (col, pivot)):
                a[t] ^= a[c]; ops.append((c, t))
        for i in range(6):
            if i != col and (a[i] >> col & 1):
                a[i] ^= a[col]; ops.append((col, i))
    return list(reversed(ops))


def solve_degree3(points, n=8, degree=3):
    mons = [m for m in range(1 << n) if m.bit_count() <= degree]
    equations = []
    for value, wanted in points.items():
        row = 0
        for j, mon in enumerate(mons):
            if value & mon == mon: row |= 1 << j
        if wanted: row |= 1 << len(mons)
        equations.append(row)
    pivot = 0; pivot_cols = []
    for col in range(len(mons)):
        hit = next((i for i in range(pivot, len(equations)) if equations[i] >> col & 1), None)
        if hit is None: continue
        equations[pivot], equations[hit] = equations[hit], equations[pivot]
        for i in range(len(equations)):
            if i != pivot and equations[i] >> col & 1: equations[i] ^= equations[pivot]
        pivot_cols.append(col)
        pivot += 1
    if any((row & ((1 << len(mons)) - 1)) == 0 and row >> len(mons) & 1 for row in equations):
        return None
    solution = 0
    for row, col in zip(equations[:len(pivot_cols)], pivot_cols):
        if row >> len(mons) & 1: solution |= 1 << col
    return [mons[i] for i in range(len(mons)) if solution >> i & 1]


def emit_toggle(q, target, controls, offset=0):
    controls = [offset + c for c in controls]
    if not controls: q.x(target); return
    q.mcx(controls, target)


def build(side="y", kernel=28, overwrite=0):
    codes = (Y_B, Y_M) if side == "y" else (X_C, X_LVL)
    if side == "y":
        # g=(y0,y1,y5,y2^y3,y2^y4), t=y2
        rows = [1, 2, 32, 4 ^ 8, 4 ^ 16, 4]
    else:
        # g=(x0,x1,x2,x3,x4^x5), t=x4
        rows = [1, 2, 4, 8, 16 ^ 32, 16]
    assert rank2(rows) == 6
    inverse = {}
    for original in range(64):
        transformed = sum(((original & row).bit_count() & 1) << i for i, row in enumerate(rows))
        inverse[transformed] = original
    q = QuantumCircuit(18)
    offset = 6 if side == "y" else 0
    anc = list(range(12, 15)) if side == "y" else list(range(15, 18))
    transform = linear_circuit(rows)
    for c, t in transform: q.cx(offset + c, offset + t)
    # Compute the three non-overwritten code bits into clean ancillas.
    code_tables = []
    def code_value(original, bit):
        return (codes[0][original] if bit == 0 else codes[1][original]) >> (0 if bit == 0 else bit - 1) & 1
    for bit in range(4):
        if bit == overwrite: continue
        table = truth(z for z in range(64) if code_value(inverse[z], bit))
        code_tables.append((bit, table))
    for target, (_, table) in zip(anc, code_tables):
        for mask, value in esop(table, 6):
            neg = [i for i in range(6) if mask >> i & 1 and not (value >> i & 1)]
            for i in neg: q.x(offset + i)
            emit_toggle(q, target, [i for i in range(6) if mask >> i & 1], offset)
            for i in neg: q.x(offset + i)
    # Care-set correction for the overwritten code bit.
    points = {}
    for z, original in inverse.items():
        g = sum(((z >> i) & 1) << i for i in range(5))
        other = 0
        for j, (_, table) in enumerate(code_tables):
            other |= ((table >> z) & 1) << (5 + j)
        desired = code_value(original, overwrite)
        points[g | other] = desired ^ ((z >> 5) & 1)
    correction = solve_degree3(points)
    if correction is None: raise RuntimeError("no cubic care-set completion")
    for mon in correction:
        neg = []
        controls = [i for i in range(8) if mon >> i & 1]
        # Controls are five garbage data wires followed by three code ancillas.
        actual = [offset + i for i in range(5) if mon >> i & 1]
        actual += [anc[j] for j in range(3) if mon >> (5+j) & 1]
        if not actual: q.x(offset + 5)
        else: q.mcx(actual, offset + 5)
    metrics = {"side": side, "kernel_direction": kernel, "overwrite": overwrite,
               "depth": q.depth(), "raw_ops": {k: int(v) for k, v in q.count_ops().items()},
               "correction_monomials": correction, "linear_rows": rows}
    return q, metrics


if __name__ == "__main__":
    q, metrics = build("y", 28, 0)
    out = transpile(q, basis_gates=["u3", "cx"], qubits_initially_zero=False,
                    optimization_level=3, seed_transpiler=0)
    metrics.update({"serialized_depth": out.depth(), "cx_count": out.count_ops().get("cx", 0)})
    d = Path("artifacts/comparator_oracle/three_plus_three")
    d.mkdir(parents=True, exist_ok=True)
    (d / "y_k28_overwrite0.qasm").write_text(qasm2.dumps(out))
    (d / "y_k28_overwrite0.metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))
