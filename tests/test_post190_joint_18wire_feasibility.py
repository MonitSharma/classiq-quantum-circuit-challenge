from post190_joint_18wire_feasibility import audit, capacity_schedule, portfolio, rank_capacity_profile
from post190_joint_18wire_storage_sat import combined_data

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

def test_rank_capacity_profile_is_necessary_filter_only():
    operands,_,_,_=combined_data()
    r=rank_capacity_profile([[0,1,5,14,16,19],[20,2,3,6,7,10],
                             [8,11,15,21,22,24],[12,17,25,4,9,23],[13,18,26]],operands)
    assert r['feasible']
    assert [x['width'] for x in r['batches']]==[6,6,6,6,3]
