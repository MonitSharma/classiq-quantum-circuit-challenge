from three_sweep.interleaved_decoder import build


def test_interleaved_decoder_builds_exact_basis_circuit():
    circuit = build(0)
    assert circuit.num_qubits == 18
    assert set(circuit.count_ops()) <= {"u3", "cx"}

