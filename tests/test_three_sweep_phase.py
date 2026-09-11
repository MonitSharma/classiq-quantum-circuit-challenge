from three_sweep.phase_factorization import analyze


def test_pi_angle_phase_track_screen_closes_five_track_model():
    result = analyze()
    assert result["partitions"] == 792
    assert result["minimum_over_all_partitions"] == 10

