from three_sweep.arbitrary_angle_screen import screen


def test_arbitrary_angle_screen_checks_natural_feature_sets():
    result = screen()
    assert len(result["side_features"]) == 4
    assert all(row["controls_checked"] == 32 for row in result["side_features"])
    assert all(not row["all_control_slices_feasible"] for row in result["side_features"])
