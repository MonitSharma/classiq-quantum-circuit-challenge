from qbp.finite_group import (
    CENTRAL,
    CENTRALIZER_ORBIT_REPS,
    CONJUGACY_REPRESENTATIVES,
    ELEMENTS,
    GROUP_ORDER,
    IDENTITY,
    MINUS_IDENTITY,
    MULTIPLY,
    evaluate,
)
from qbp.resource import quaternion_matrix
from qbp.mitm import _batch_trajectories, trajectory

import numpy as np


def test_binary_icosahedral_table_is_closed_and_has_identity():
    assert len(ELEMENTS) == GROUP_ORDER == 120
    assert len(MULTIPLY) == GROUP_ORDER
    assert all(len(row) == GROUP_ORDER for row in MULTIPLY)
    assert all(MULTIPLY[IDENTITY][i] == i for i in range(GROUP_ORDER))
    assert CENTRAL == {IDENTITY, MINUS_IDENTITY}


def test_empty_qbp_is_identity_for_all_inputs():
    assert evaluate(()) == (IDENTITY,) * 4096


def test_conjugacy_symmetry_partition_is_valid():
    assert CONJUGACY_REPRESENTATIVES
    assert set(CONJUGACY_REPRESENTATIVES) <= set(range(GROUP_ORDER))
    assert all(reps for reps in CENTRALIZER_ORBIT_REPS.values())


def test_quaternion_representation_is_unitary():
    for element in ELEMENTS[::17]:
        matrix = quaternion_matrix(element)
        assert np.allclose(matrix.conj().T @ matrix, np.eye(2), atol=1e-12)


def test_mitm_trajectory_matches_empty_identity_convention():
    assert np.array_equal(trajectory(()), np.full(4096, IDENTITY, dtype=np.uint8))


def test_batched_mitm_trajectory_matches_scalar():
    choices = np.asarray([[[IDENTITY, 3], [5, IDENTITY]]], dtype=np.uint8)
    order = (0, 1)
    scalar = trajectory(((0, IDENTITY, 3), (1, 5, IDENTITY)))
    assert np.array_equal(_batch_trajectories(choices, order)[0], scalar)


def test_continuous_qbp_target_has_expected_shape():
    from qbp.continuous import target_signs
    assert target_signs().shape == (4096,)
    assert set(target_signs()) == {-1.0, 1.0}


def test_continuous_checkpoint_is_explicitly_non_exact():
    import json
    from pathlib import Path
    report = json.loads(Path("artifacts/unitary_state_space/qbp/continuous_l12_s0.json").read_text())
    assert report["status"] == "numerical_only"
    assert report["loss"] > 1e-6


def test_continuous_schedule_reuse_is_deterministic():
    from qbp.continuous import optimize
    first = optimize(4, 2, 0, 0.01, schedule_seed=7)
    second = optimize(4, 2, 0, 0.01, schedule_seed=7)
    assert first["order"] == second["order"]


def test_width4_unitary_parameterization_has_expected_shape():
    import jax.numpy as jnp
    from qbp.continuous_width4 import unitary4
    matrices = unitary4(jnp.zeros((2, 16)))
    assert matrices.shape == (2, 4, 4)
