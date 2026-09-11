from three_sweep.half_arbitrary_angle_screen import screen


def test_half_code_arbitrary_angle_screen():
    result = screen()
    assert len(result["side_features"]) == 2
    assert all(row["controls_checked"] == 32 for row in result["side_features"])
