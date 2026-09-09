"""Relative-phase dirty-ancilla variant of shared_vector_shannon."""
import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile
from qiskit.circuit.library import RCCXGate
from qiskit.synthesis import synth_mcx_n_dirty_i15

from shared_vector_shannon import FEATURES, VALUES, plan

def relative_mcx(circuit, controls, target, outputs):
    k = len(controls)
    if k == 0:
        circuit.x(target)
    elif k == 1:
        circuit.cx(controls[0], target)
    elif k == 2:
        circuit.append(RCCXGate(), controls + [target])
    else:
        dirty = [wire for wire in outputs + [17]
                 if wire not in controls and wire != target][:k - 2]
        sub = synth_mcx_n_dirty_i15(k, relative_phase=True)
        circuit.compose(sub, controls + [target] + dirty, inplace=True)

def emit(circuit, node, variables, controls, outputs):
    if node[0] == 'leaf':
        full = (1 << (1 << len(variables))) - 1
        for i, table in enumerate(node[1]):
            if table == full:
                relative_mcx(circuit, [6 + b for b in controls], outputs[i], outputs)
        return
    _, variable, low, delta = node
    position = variables.index(variable)
    remaining = variables[:position] + variables[position + 1:]
    emit(circuit, low, remaining, controls, outputs)
    emit(circuit, delta, remaining, controls + [variable], outputs)

def build():
    _, node = plan(tuple(VALUES), tuple(range(6)), 0)
    circuit = QuantumCircuit(18)
    emit(circuit, node, list(range(6)), [], list(range(12, 17)))
    return transpile(circuit, basis_gates=['u3', 'cx'],
                     qubits_initially_zero=False, optimization_level=3)

def main():
    circuit = build()
    output = Path('artifacts/shared_vector_shannon_rp_loader.qasm')
    output.write_text(qasm2.dumps(circuit))
    metrics = {'depth': circuit.depth(), 'cx': circuit.count_ops().get('cx', 0),
               'width': circuit.num_qubits, 'relative_phase': True}
    Path('artifacts/shared_vector_shannon_rp_loader_metrics.json').write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))

if __name__ == '__main__':
    main()
