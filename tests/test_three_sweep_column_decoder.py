from three_sweep.column_decoder import build


def test_column_decoder_builds_basis_circuit():
    circuit = build(19)
    assert circuit.num_qubits == 18
    assert set(circuit.count_ops()) <= {"u3", "cx"}

