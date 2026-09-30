"""Native 3+3-ancilla affine-isometry probe.

This is a focused candidate generator, not a complete oracle.  It uses five
linear garbage parities, computes three code bits into the three clean wires,
and overwrites one data bit with a degree-bounded care-set correction.
"""

import json
import hashlib
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


def kernel_rows(kernel):
    """Return five independent parities orthogonal to ``kernel`` plus a pivot."""
    rows = []
    for candidate in range(1, 64):
        if (candidate & kernel).bit_count() & 1:
            continue
        if rank2(rows + [candidate]) > len(rows):
            rows.append(candidate)
        if len(rows) == 5:
            break
    if len(rows) != 5:
        raise RuntimeError(f"could not find five kernel-orthogonal rows for {kernel}")
    pivot = next(candidate for candidate in range(1, 64)
                 if rank2(rows + [candidate]) == 6)
    return rows + [pivot]


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


def verify_raw(q, side, rows, overwrite, codes):
    """Check the classical action on every six-bit basis input."""
    offset = 6 if side == "y" else 0
    anc = list(range(12, 15)) if side == "y" else list(range(15, 18))
    code_bits = [bit for bit in range(4) if bit != overwrite]
    for original in range(64):
        bits = [0] * 18
        for i in range(6):
            bits[offset + i] = (original >> i) & 1
        for inst in q.data:
            name = inst.operation.name
            qubits = [q.find_bit(v).index for v in inst.qubits]
            if name == "x":
                bits[qubits[0]] ^= 1
            elif name == "cx":
                bits[qubits[1]] ^= bits[qubits[0]]
            elif name in {"rccx", "ccx", "mcx", "c3_x", "c4_x", "c5_x", "c6_x"}:
                bits[qubits[-1]] ^= int(all(bits[v] for v in qubits[:-1]))
            else:
                raise RuntimeError(f"unexpected raw gate {name}")
        for j, target in enumerate(anc):
            code_bit = code_bits[j]
            expected = (codes[0][original] if code_bit == 0 else codes[1][original])
            expected >>= 0 if code_bit == 0 else code_bit - 1
            if bits[target] != (expected & 1):
                return False, f"ancilla input={original} bit={code_bit}"
        for i, row in enumerate(rows):
            expected = (codes[0][original] if overwrite == 0 else codes[1][original])
            if i == 5:
                expected >>= 0 if overwrite == 0 else overwrite - 1
            else:
                expected = (original & row).bit_count() & 1
            if bits[offset + i] != (expected & 1):
                return False, f"data input={original} wire={i}"
    return True, "all 64 inputs"


def build(side="y", kernel=28, overwrite=0):
    codes = (Y_B, Y_M) if side == "y" else (X_C, X_LVL)
    if side == "y":
        # g=(y0,y1,y5,y2^y3,y2^y4), t=y2
        rows = [1, 2, 32, 4 ^ 8, 4 ^ 16, 4] if kernel == 28 else kernel_rows(kernel)
    else:
        # g=(x0,x1,x2,x3,x4^x5), t=x4
        rows = [1, 2, 4, 8, 16 ^ 32, 16] if kernel == 48 else kernel_rows(kernel)
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
        key = g | other
        value = desired ^ ((z >> 5) & 1)
        if key in points and points[key] != value:
            raise RuntimeError(f"inconsistent care-set collision at {key:#x}")
        points[key] = value
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
               "care_points": len(points),
               "depth": q.depth(), "raw_ops": {k: int(v) for k, v in q.count_ops().items()},
               "correction_monomials": correction, "linear_rows": rows}
    metrics["raw_verification"] = verify_raw(q, side, rows, overwrite, codes)
    if not metrics["raw_verification"][0]:
        raise RuntimeError(metrics["raw_verification"][1])
    return q, metrics


if __name__ == "__main__":
    d = Path("artifacts/comparator_oracle/three_plus_three")
    d.mkdir(parents=True, exist_ok=True)
    results = []
    for kernel in (28, 35):
        for overwrite in range(4):
            try:
                q, metrics = build("y", kernel, overwrite)
            except RuntimeError as exc:
                results.append({"side": "y", "kernel_direction": kernel,
                                "overwrite": overwrite, "status": "failed", "error": str(exc)})
                continue
            out = transpile(q, basis_gates=["u3", "cx"], qubits_initially_zero=False,
                            optimization_level=3, seed_transpiler=0)
            metrics.update({"serialized_depth": out.depth(), "cx_count": out.count_ops().get("cx", 0)})
            stem = f"y_k{kernel}_overwrite{overwrite}"
            qasm_text = qasm2.dumps(out)
            qasm_path = d / f"{stem}.qasm"
            qasm_path.write_text(qasm_text)
            metrics["qasm_sha256"] = hashlib.sha256(qasm_text.encode()).hexdigest()
            (d / f"{stem}.metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
            results.append(metrics)
    (d / "screen.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))
