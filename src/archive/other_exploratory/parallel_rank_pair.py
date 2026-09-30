"""Side-separated rank-pair compiler using three ancillas per coordinate side."""

import json
from pathlib import Path

from qiskit import QuantumCircuit, transpile

from formula import formula, remap
from pebble import smart_compute


def side_compute(table, inputs, output, scratch):
    circuit = QuantumCircuit(18)
    expression = remap(formula(table, 6), list(inputs))
    smart_compute(circuit, expression, output, list(scratch))
    return circuit


def parallel_pair(a, b):
    x = side_compute(a, range(0, 6), 12, (13, 14))
    y = side_compute(b, range(6, 12), 15, (16, 17))
    pre = QuantumCircuit(18)
    pre.compose(x, inplace=True)
    pre.compose(y, inplace=True)
    pair = pre.copy()
    pair.cz(12, 15)
    pair.compose(pre.inverse(), inplace=True)
    return x, y, pre, pair


def score_pair(a, b):
    x, y, pre, pair = parallel_pair(a, b)
    compiled_x = transpile(x, basis_gates=["u3", "cx"],
                           qubits_initially_zero=False, optimization_level=3)
    compiled_y = transpile(y, basis_gates=["u3", "cx"],
                           qubits_initially_zero=False, optimization_level=3)
    compiled_pre = transpile(pre, basis_gates=["u3", "cx"],
                             qubits_initially_zero=False, optimization_level=3)
    compiled_pair = transpile(pair, basis_gates=["u3", "cx"],
                              qubits_initially_zero=False, optimization_level=3)
    return {
        "x_depth": compiled_x.depth(),
        "x_cx": compiled_x.count_ops().get("cx", 0),
        "y_depth": compiled_y.depth(),
        "y_cx": compiled_y.count_ops().get("cx", 0),
        "parallel_compute_depth": compiled_pre.depth(),
        "parallel_compute_cx": compiled_pre.count_ops().get("cx", 0),
        "pair_depth": compiled_pair.depth(),
        "pair_cx": compiled_pair.count_ops().get("cx", 0),
        "width": compiled_pair.num_qubits,
    }


def main():
    bases = {
        "pair_terms": json.loads(Path("artifacts/pair_terms.json").read_text()),
        "rank_terms": json.loads(Path("artifacts/rank_terms.json").read_text()),
        "rank_mc_pareto_terms": json.loads(Path("artifacts/rank_mc_pareto_terms.json").read_text()),
    }
    results = {}
    for basis_name, terms in bases.items():
        rows = []
        for index, (a, b) in enumerate(terms):
            try:
                row = {"term_index": index, **score_pair(a, b)}
            except (ValueError, IndexError) as error:
                row = {"term_index": index, "error": type(error).__name__}
            rows.append(row)
            print(basis_name, index, row, flush=True)
        results[basis_name] = rows
    Path("artifacts/parallel_rank_pair_metrics.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

