"""Exact dirty-wire phase catalyst for parity toggles.

For a dirty target d and h equal to the parity of control wires, the sequence
Z(d), C_h, Z(d), C_h (read right-to-left as an operator product) is equivalent
to a phase (-1)^h while restoring d.  The implementation below emits the
left-to-right circuit C_h, Z(d), C_h, Z(d).
"""

from qiskit import QuantumCircuit


def append_parity_catalyst(circuit: QuantumCircuit, controls, target: int):
    controls = list(controls)
    if target in controls:
        raise ValueError("dirty target must be distinct from all controls")
    for control in controls:
        circuit.cx(control, target)
    circuit.z(target)
    for control in reversed(controls):
        circuit.cx(control, target)
    circuit.z(target)


def parity_catalyst(controls: int = 2) -> QuantumCircuit:
    circuit = QuantumCircuit(controls + 1)
    append_parity_catalyst(circuit, range(controls), controls)
    return circuit

