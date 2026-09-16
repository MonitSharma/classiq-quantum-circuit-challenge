import unittest

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from phase_history_search import (
    ALL_ONES,
    HistoricalBasis,
    TARGET,
    apply_gate_semantic,
    build_phase_history_circuit,
    primitive_events,
    replay_history,
)
from destructive_semantic_search import initial_wire_truth_tables


class PhaseHistoryTests(unittest.TestCase):
    def test_trivial_history_membership(self):
        basis = HistoricalBasis()
        target = 0b101101
        basis.add(target, 3, 5)
        self.assertEqual(basis.reconstruct(target), target)
        result = basis.provenance(target)
        self.assertEqual(result["taps"][0]["step"], 3)
        self.assertEqual(result["taps"][0]["wire"], 5)

    def test_nonlinear_history_identity(self):
        a = 0xAA
        b = 0xCC
        before = 0xF0
        after = before ^ (a & b)
        basis = HistoricalBasis()
        basis.add(before, 0, 2)
        basis.add(after, 1, 2)
        self.assertEqual(basis.reconstruct(before ^ after), before ^ after)
        self.assertEqual(basis.reconstruct(a & b), a & b)

    def test_provenance_backsolve_and_duplicates(self):
        basis = HistoricalBasis()
        a, b, c = 0x1234, 0x0F0F, 0xAAAA
        basis.add(a, 1, 1)
        basis.add(b, 2, 2)
        basis.add(a, 3, 4)
        basis.add(c, 4, 5)
        target = a ^ b ^ c
        result = basis.provenance(target)
        self.assertIsNotNone(result)
        self.assertEqual(len(basis.signals), 4)  # constant plus a,b,c
        self.assertEqual(basis.reconstruct(target), target)

    def test_complement_uses_global_constant(self):
        basis = HistoricalBasis()
        target = 0x1234
        basis.add(target, 1, 1)
        self.assertEqual(basis.reconstruct(target ^ ALL_ONES), target ^ ALL_ONES)
        result = basis.provenance(target ^ ALL_ONES)
        self.assertEqual(result["constant"], 1)

    def test_full_semantic_replay(self):
        gates = (("rccx", 0, 1, 12), ("cx", 12, 13), ("rccx", 2, 3, 14))
        final, basis, snapshots = replay_history(gates)
        wires = initial_wire_truth_tables()
        for gate in gates:
            wires = apply_gate_semantic(wires, gate)
        self.assertEqual(final, wires)
        self.assertEqual(len(snapshots), len(gates) + 1)
        self.assertGreaterEqual(basis.rank, 13)

    def test_phase_tap_round_trip_toy(self):
        # q0 and q1 are controls, q2 starts as T=0.  After RCCX, q2 is A*B.
        # T_before XOR T_after is therefore A*B.
        gates = (("rccx", 0, 1, 2),)
        circuit = build_phase_history_circuit(
            gates, [{"step": 0, "wire": 2}, {"step": 1, "wire": 2}], 3
        )
        compiled = circuit.decompose().decompose()
        for basis_index in range(8):
            state = Statevector.from_int(basis_index, 8)
            result = state.evolve(compiled)
            expected_phase = -1 if ((basis_index & 1) and (basis_index & 2)) else 1
            expected = state * expected_phase
            self.assertTrue(result.equiv(expected), basis_index)

    def test_disjoint_layer_semantics(self):
        gates = (("layer", (("rccx", 0, 1, 2), ("rccx", 3, 4, 5))),)
        final, _, snapshots = replay_history(gates)
        self.assertEqual(len(snapshots), 2)
        initial = initial_wire_truth_tables()
        self.assertEqual(final[2], initial[2] ^ (initial[0] & initial[1]))

    def test_affine_history_records_internal_steps(self):
        gates = (("affine", 0, 1, 2, 12),)
        final, basis, snapshots = replay_history(gates)
        initial = initial_wire_truth_tables()
        self.assertEqual(final[12], initial[12] ^ ((initial[0] ^ initial[1]) & initial[2]))
        self.assertEqual(len(snapshots), 4)
        self.assertGreaterEqual(basis.rank, 14)

    def test_affine_tap_uses_same_internal_timeline_as_builder(self):
        gates = (("affine", 0, 1, 2, 12),)
        self.assertEqual(len(primitive_events(gates)), 3)
        circuit = build_phase_history_circuit(
            gates, [{"step": 1, "wire": 0}], 18
        )
        names = [instruction.operation.name for instruction in circuit.data]
        # The internal tap is emitted after the first CX, before RCCX.
        self.assertEqual(names[:2], ["cx", "z"])


if __name__ == "__main__":
    unittest.main()
