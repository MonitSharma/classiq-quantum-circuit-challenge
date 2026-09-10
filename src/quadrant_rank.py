"""Quadrant-specific GF(2) rank decomposition diagnostic."""

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from pair_search import pair_circuit
from search import logo


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
    for i, basis_row in enumerate(basis_rows):
        x_table = 0
        for x, coeff in enumerate(coefficients):
            if (coeff >> i) & 1:
                x_table |= 1 << ((x5 << 5) | x)
        y_table = sum(
            ((basis_row >> y) & 1) << ((y5 << 5) | y)
            for y in range(32)
        )
        terms.append((x_table, y_table))

    for x in range(32):
        for y in range(32):
            reconstructed = 0
            for x_table, y_table in terms:
                reconstructed ^= ((x_table >> ((x5 << 5) | x)) & 1) & ((y_table >> ((y5 << 5) | y)) & 1)
            assert reconstructed == logo((x5 << 5) | x, (y5 << 5) | y)
    return terms


def build():
    terms = []
    ranks = {}
    for x5 in (0, 1):
        for y5 in (0, 1):
            local = quadrant_factor(x5, y5)
            ranks[(x5, y5)] = len(local)
            terms.extend(local)
    q = QuantumCircuit(18)
    for term in terms:
        q.compose(pair_circuit(*term), inplace=True)
    out = transpile(q, basis_gates=['u3', 'cx'], qubits_initially_zero=False, optimization_level=3)
    return out, terms, ranks


if __name__ == '__main__':
    q, terms, ranks = build()
    print('ranks', ranks, 'terms', len(terms), 'depth', q.depth(), 'cx', q.count_ops().get('cx', 0), flush=True)
    Path('artifacts/quadrant_rank.qasm').write_text(qasm2.dumps(q))
    Path('artifacts/quadrant_rank_terms.json').write_text(json.dumps(terms))
    Path('artifacts/quadrant_rank.meta.json').write_text(json.dumps({'ranks': {f'{x5},{y5}': r for (x5, y5), r in ranks.items()}, 'depth': q.depth(), 'cx': q.count_ops().get('cx', 0)}, indent=2))
