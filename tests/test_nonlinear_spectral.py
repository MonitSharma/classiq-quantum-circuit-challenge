import numpy as np

from nonlinear_spectral import (
    Mutation,
    SIZE,
    fwht,
    identity_mapping,
    inverse_mapping,
    run,
    spectrum,
    truth_table,
)


def test_fwht_is_self_inverse_up_to_size():
    values = np.array([1, -1, 1, -1, -1, 1, 1, -1], dtype=np.int64)
    assert np.array_equal(fwht(fwht(values)), values * len(values))


def test_triangular_mutation_is_bijective_and_involutive():
    mutation = Mutation(target=7, mask_a=1, const_a=0, mask_b=2, const_b=1)
    mapping = mutation.apply(identity_mapping())
    assert np.unique(mapping).size == SIZE
    assert np.array_equal(mutation.apply(mapping), identity_mapping())
    assert np.array_equal(inverse_mapping(mapping)[mapping], np.arange(SIZE))


def test_baseline_spectrum_and_screen():
    metrics = spectrum(identity_mapping(), truth_table())
    assert metrics["marked_population"] == 1097
    assert metrics["walsh_support"] == SIZE
    assert metrics["weighted_support"] == 24576
    report = run(samples=8, mutations=2, seed=42, max_weight=2)
    assert report["best_sampled_candidate"]["metrics"]["walsh_support"] == SIZE


def test_phase_walsh_coefficients_have_correct_parity():
    bits = truth_table().astype(np.int64)
    coefficients = fwht(1 - 2 * bits)
    assert coefficients[0] == 1902
    assert np.all(np.abs(coefficients[1:]) % 4 == 2)
