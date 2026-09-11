from three_sweep.shell_decoder import build


def test_shell_decoder_builds_basis_circuit():
    circuit = build(0)
    assert circuit.num_qubits == 18
    assert set(circuit.count_ops()) <= {"u3", "cx"}

