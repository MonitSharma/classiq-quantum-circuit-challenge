"""Shared Shannon/Davio-style five-output y-feature loader diagnostic."""
import functools
import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile
from vector_feature_analysis import truth_rows, FEATURES

N = 64
VALUES = [sum(row[f] << row['y'] for row in truth_rows()) for f in FEATURES]

def remove_bit(i, pos):
    return (i & ((1 << pos) - 1)) | ((i >> (pos + 1)) << pos)

def gate_cost(k):
    return 1 if k <= 1 else 6 if k == 2 else 20 + 4 * k

@functools.lru_cache(None)
def plan(tables, variables, path_length):
    full = (1 << (1 << len(variables))) - 1
    if all(table in (0, full) for table in tables):
        return (sum(gate_cost(path_length) for table in tables if table == full),
                ('leaf', tables))
    best = (10**9, None)
    for variable in variables:
        position = variables.index(variable)
        remaining = variables[:position] + variables[position + 1:]
        low, high = [], []
        for table in tables:
            lo = hi = 0
            for index in range(1 << len(variables)):
                if table >> index & 1:
                    target = remove_bit(index, position)
                    if index >> position & 1:
                        hi |= 1 << target
                    else:
                        lo |= 1 << target
            low.append(lo); high.append(hi)
        delta = tuple(lo ^ hi for lo, hi in zip(low, high))
        low_cost, low_plan = plan(tuple(low), remaining, path_length)
        delta_cost, delta_plan = plan(delta, remaining, path_length + 1)
        if low_cost + delta_cost < best[0]:
            best = (low_cost + delta_cost,
                    ('split', variable, low_plan, delta_plan))
    return best

def emit(circuit, node, variables, controls, outputs):
    if node[0] == 'leaf':
        full = (1 << (1 << len(variables))) - 1
        for output, table in enumerate(node[1]):
            if table != full:
                continue
            target = outputs[output]
            if not controls:
                circuit.x(target)
            elif len(controls) == 1:
                circuit.cx(6 + controls[0], target)
            elif len(controls) == 2:
                circuit.ccx(6 + controls[0], 6 + controls[1], target)
            else:
                circuit.mcx([6 + bit for bit in controls], target)
        return
    _, variable, low_plan, delta_plan = node
    position = variables.index(variable)
    remaining = variables[:position] + variables[position + 1:]
    emit(circuit, low_plan, remaining, controls, outputs)
    emit(circuit, delta_plan, remaining, controls + [variable], outputs)

def build():
    _, plan_node = plan(tuple(VALUES), tuple(range(6)), 0)
    circuit = QuantumCircuit(18)
    emit(circuit, plan_node, list(range(6)), [], list(range(12, 17)))
    return transpile(circuit, basis_gates=['u3', 'cx'],
                     qubits_initially_zero=False, optimization_level=3)

def main():
    circuit = build()
    output = Path('artifacts/shared_vector_shannon_loader.qasm')
    output.write_text(qasm2.dumps(circuit))
    metrics = {'depth': circuit.depth(), 'cx': circuit.count_ops().get('cx', 0),
               'width': circuit.num_qubits, 'estimated': plan(tuple(VALUES), tuple(range(6)), 0)[0]}
    Path('artifacts/shared_vector_shannon_loader_metrics.json').write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))

if __name__ == '__main__':
    main()
