from post190_joint_18wire_feasibility import audit, capacity_schedule, portfolio

def test_fixed_witness_pair_has_capacity_optimal_schedule():
    r=audit()
    assert r['all_64_side_inputs_verified']
    assert r['nonlinear_batches']==5
    assert r['capacity_optimal']

def test_retained_witness_portfolio_is_not_single_pair_only():
    r=portfolio()
    assert (r['x_candidates'],r['y_candidates'])==(4,8)
    assert len(r['pairs'])==32
    assert r['all_capacity_optimal']
