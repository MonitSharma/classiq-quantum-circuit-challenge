from three_sweep.reachable_phase_poly import coefficients, half_codes


def test_reachable_phase_coefficients_are_nonempty():
    terms = coefficients(half_codes())
    assert len(terms) > 0
    assert all(mask >= 0 for mask in terms)

