from post190_joint_18wire_storage_sat import fixed_frame_solver

def test_fixed_schedule_solver_returns_bounded_result():
    r=fixed_frame_solver(timeout_ms=5000)
    assert r['status'] in {'SAT','UNSAT','UNKNOWN'}
    assert r['model'].startswith('40-bit semantic rows')

def test_candidate_zero_fixed_schedule_current_result_is_unsat():
    r=fixed_frame_solver(timeout_ms=5000)
    assert r['status']=='UNSAT'
