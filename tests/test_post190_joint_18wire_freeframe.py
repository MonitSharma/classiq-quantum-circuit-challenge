from post190_joint_18wire_freeframe_sat import affine_dependency_control, semantic_screen

def test_semantic_dependency_control_distinguishes_formal_symbols():
    r=affine_dependency_control()
    assert r['passes'] and r['semantic_rank']==2 and r['formal_symbol_rank']==3

def test_endpoint_diagnostic_is_not_claimed_as_storage_sat():
    r=semantic_screen()
    assert r['status']=='RELAXED_ENDPOINT_PASS_STORAGE_UNMODELED'
    assert r['relaxed_endpoint_distinct_in_accumulated_span']
    assert r['native_cnot_depth']=='not modeled'
