from three_sweep.shell_decoder import build
from three_sweep.codebook_search import search


def test_shell_decoder_builds_basis_circuit():
    circuit = build(0)
    assert circuit.num_qubits == 18
    assert set(circuit.count_ops()) <= {"u3", "cx"}


def test_codebook_search_is_available_for_shell_decoder():
    result = search()
    assert result["lower_best"]["cost"] <= result["lower_baseline_cost"]
