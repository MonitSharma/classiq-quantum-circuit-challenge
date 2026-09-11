from three_sweep.reachable_column_phase_poly import coefficients
from three_sweep.column_pair_loader import column_codes


def test_reachable_column_phase_coefficients():
    assert len(coefficients(column_codes())) > 0

