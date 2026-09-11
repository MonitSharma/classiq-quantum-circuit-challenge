from three_sweep.row_pair_analysis import analyze, codebook
from three_sweep.loader5 import tables_from_codebook
from three_sweep.verify_loader import verify
from three_sweep.phase_rank_screen import screen
from three_sweep.dirty_phase_catalyst import parity_catalyst
import numpy as np
from qiskit.quantum_info import Statevector


def test_ordered_row_pairs_have_18_classes():
    result = analyze()
    assert result["distinct_pair_count"] == 18
    assert len(result["rows"]) == 32


def test_deterministic_codebook_uses_five_bits():
    result = analyze()
    codes = codebook(result)["class_to_code"]
    assert len(codes) == 18
    assert len(set(codes.values())) == 18
    assert max(codes.values()) < 32


def test_loader_tables_depend_on_low_five_y_only(tmp_path):
    result = analyze()
    path = tmp_path / "codebook.json"
    import json
    path.write_text(json.dumps(codebook(result)))
    tables = tables_from_codebook(path)
    assert len(tables) == 5
    assert all(table.bit_length() <= 32 for table in tables)


def test_loader_basis_action(tmp_path):
    result = analyze()
    import json
    codebook_path = tmp_path / "codebook.json"
    codebook_path.write_text(json.dumps(codebook(result)))
    report = verify(codebook_path)
    assert report["verified"]


def test_phase_partition_screen_has_all_five_bit_partitions():
    report = screen()
    assert report["partitions"] == 792
    assert all(len(row["chosen_bits"]) == 5 for row in report["results"])


def test_dirty_phase_catalyst_restores_dirty_target_and_phase():
    circuit = parity_catalyst(3)
    for basis in range(16):
        output = Statevector.from_int(basis, dims=16).evolve(circuit).data
        expected = basis
        expected_phase = -1 if ((basis & 1) ^ ((basis >> 1) & 1) ^ ((basis >> 2) & 1)) else 1
        assert np.argmax(np.abs(output)) == expected
        assert abs(output[expected] - expected_phase) < 1e-12
