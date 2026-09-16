from xag_pebble_exact import solve

def test_exact_clean_pebbling_positive_and_capacity_negative():
    deps={13:[],14:[13],15:[13,14]}
    positive=solve(deps,[15],3,6,3)
    assert positive['status']=='sat' and positive['replay_verified']
    assert solve(deps,[15],2,8,3)['status']=='unsat'

def test_horizon_unsat_is_not_a_storage_lower_bound():
    deps={13:[],14:[13]}
    assert solve(deps,[14],2,2,3)['status']=='unsat'
    assert solve(deps,[14],2,4,3)['status']=='sat'
