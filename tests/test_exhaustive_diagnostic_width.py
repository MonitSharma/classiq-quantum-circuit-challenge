from pathlib import Path
import pytest
from qiskit import QuantumCircuit,qasm2
from exhaustive_verify import exhaustive


def test_default_oracle_verifier_still_rejects_oversized_circuits(tmp_path):
    path=tmp_path/'oversized.qasm'
    path.write_text(qasm2.dumps(QuantumCircuit(23)))
    with pytest.raises(AssertionError):exhaustive(path)
