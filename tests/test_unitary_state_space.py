from pathlib import Path
import json

import numpy as np

from src.mpo_target import DEFAULT_ORDER, ordered_tensor, tt_ranks
from src.tensor_rank_exact import PRIMES, rank_mod
from src.nie_zi_finite import parameter_rows


def test_modular_tensor_profile_matches_tt_profile():
    tensor = np.asarray(ordered_tensor(DEFAULT_ORDER), dtype=np.int64)
    profile = []
    for cut in range(1, 12):
        unfolding = tensor.reshape(2**cut, 2 ** (12 - cut))
        ranks = {rank_mod(unfolding, prime) for prime in PRIMES}
        assert len(ranks) == 1
        profile.append(ranks.pop())
    assert profile == tt_ranks(tensor)[1:-1]
    assert max(profile) == 13


def test_nie_zi_enumerates_all_nontrivial_splits():
    rows = parameter_rows()
    assert len(rows) == 11
    assert all(row["p"] + row["q"] == 12 for row in rows)
    assert min(row["optimistic_total_with_prefix"] for row in rows) > 300


def test_stage_a_artifact_records_stop_and_target_metadata():
    path = Path("artifacts/unitary_state_space/nie_zi_finite_resource.json")
    data = json.loads(path.read_text())
    assert data["n"] == 12
    assert data["ancillas"] == 6
    assert data["verdict"] == "STOP"
    assert data["paper"].startswith("arXiv:2607.28402")


def test_exact_tt_witness_was_reconstructed():
    witness = json.loads(Path("artifacts/unitary_state_space/tensor_tt_exact.json").read_text())
    assert witness["all_4096_entries_reconstructed"] is True
    assert len(witness["cores"]) == 12


def test_tt_same_bond_diagnostic_records_algebraic_obstructions():
    data = json.loads(Path("artifacts/unitary_state_space/tt/tt_dilation_feasibility.json").read_text())
    assert data["decision"].startswith("STOP_SAME_BOND")
    assert data["obstructed_layers"]
