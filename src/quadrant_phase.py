"""Specialized quadrant-rank phase construction using direct selector controls."""

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from formula import compute, formula
from factor import phase_cube
from search import logo


def remap(expr, variables):
    if isinstance(expr, int):
        return expr
    if expr[0] == 'v':
        return ('v', variables[expr[1]])
    return (expr[0], *(remap(x, variables) for x in expr[1:]))


def quadrant_factor(x5, y5):
    rows = [
        sum(logo((x5 << 5) | x, (y5 << 5) | y) << y for y in range(32))
        for x in range(32)
    ]
    basis = {}
    basis_rows = []
    coefficients = []
    for row in rows:
        residual = row
        coeff = 0
        while residual:
            pivot = residual.bit_length() - 1
            if pivot in basis:
                base_row, base_coeff = basis[pivot]
                residual ^= base_row
                coeff ^= base_coeff
            else:
                own = 1 << len(basis_rows)
                basis[pivot] = (residual, own)
                basis_rows.append(residual)
                coeff ^= own
                break
        coefficients.append(coeff)
    terms = []
    for i, base_row in enumerate(basis_rows):
        x_table = sum(1 << x for x, c in enumerate(coefficients) if (c >> i) & 1)
        y_table = base_row
        terms.append((x5, y5, x_table, y_table))
    return terms


def build():
    terms = sum((quadrant_factor(x5, y5) for x5 in (0, 1) for y5 in (0, 1)), [])
    q = QuantumCircuit(18)
    for x5, y5, x_table, y_table in terms:
        x_expr = remap(formula(x_table, 5), range(5))
        y_expr = remap(formula(y_table, 5), range(6, 11))
        x_pre = QuantumCircuit(18)
        y_pre = QuantumCircuit(18)
        compute(x_pre, x_expr, 12, [13, 14, 15, 16, 17])
        compute(y_pre, y_expr, 13, [14, 15, 16, 17])
        q.compose(x_pre, inplace=True)
        q.compose(y_pre, inplace=True)
        controls = [13, 14, 6 if x5 else -6, 12 if y5 else -12]
        phase_cube(q, frozenset(controls), [])
        q.compose(y_pre.inverse(), inplace=True)
        q.compose(x_pre.inverse(), inplace=True)
    out = transpile(q, basis_gates=['u3', 'cx'], qubits_initially_zero=False, optimization_level=3)
    return out, terms


if __name__ == '__main__':
    q, terms = build()
    print('terms', len(terms), 'depth', q.depth(), 'cx', q.count_ops().get('cx', 0), flush=True)
    Path('artifacts/quadrant_phase.qasm').write_text(qasm2.dumps(q))
    Path('artifacts/quadrant_phase_terms.json').write_text(json.dumps(terms))
    Path('artifacts/quadrant_phase.meta.json').write_text(json.dumps({'terms': len(terms), 'depth': q.depth(), 'cx': q.count_ops().get('cx', 0)}, indent=2))
