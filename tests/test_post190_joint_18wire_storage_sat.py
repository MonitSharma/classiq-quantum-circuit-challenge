import json
from functools import reduce
from operator import xor
from post190_joint_18wire_storage_sat import combined_data, fixed_frame_solver, initial_rows, replay_model, XPATH, YPATH
from post190_joint_18wire_freeframe_sat import candidate_tables, truth, rank

def test_initial_coordinate_rows_are_not_zero():
    assert initial_rows() == [1 << i for i in range(1, 13)] + [0] * 6

def test_operands_and_endpoints_match_actual_functions_without_double_remapping():
    operands, nodes, endpoints, _ = combined_data()
    xt, xo = candidate_tables(json.loads(XPATH.read_text()), 'x')
    yt, yo = candidate_tables(json.loads(YPATH.read_text()), 'y')
    basis = [(1 << 4096) - 1] + [truth(lambda z, i=i: bool(z >> i & 1)) for i in range(12)] + xt + yt
    assert rank(basis) == 40
    evaluate = lambda mask: reduce(xor, (v for i, v in enumerate(basis) if mask >> i & 1), 0)
    for (a, b), node in zip(operands, nodes):
        assert evaluate(a) & evaluate(b) == evaluate(node)
    assert list(map(evaluate, endpoints)) == xo + [basis[5] ^ basis[6]] + yo + [basis[12]]

def test_known_clean_and_dirty_storage_models_are_sat():
    r = fixed_frame_solver([[0]], timeout_ms=5000, data=([(2,4)], [16], [8^16]), width=3, inputs=3)
    assert r['status'] == 'SAT' and r['replay_verified']
    r = fixed_frame_solver([[0]], timeout_ms=5000, data=([(2,4)], [8], [8]), width=3, inputs=2)
    assert r['status'] == 'SAT' and r['replay_verified']

def test_missing_nonlinear_information_is_unsat():
    r = fixed_frame_solver([], timeout_ms=5000, data=([], [], [8]), width=3, inputs=2)
    assert r['status'] == 'UNSAT'

def test_replay_checks_actual_schedule_and_affine_inverse():
    identity = {'matrix': [[1,0,0],[0,1,0],[0,0,1]], 'inverse': [[1,0,0],[0,1,0],[0,0,1]], 'translation': [0,0,0]}
    m = [[0,1,0],[1,1,1],[0,0,1]]
    inv = [[1,1,1],[1,0,0],[0,0,1]]
    result = {'width':3, 'inputs':3, 'schedule':[[0]], 'frames':[identity, {'matrix':m,'inverse':inv,'translation':[0,0,0]}]}
    assert replay_model(result, [(2,4)], [16], [4, 2^4^8^16])

def test_replay_xor_cancels_overlapping_semantic_row_bits():
    identity = {'matrix': [[1,0,0],[0,1,0],[0,0,1]], 'inverse': [[1,0,0],[0,1,0],[0,0,1]], 'translation': [0,0,0]}
    mixing = {'matrix': [[1,1,0],[0,1,0],[0,0,1]], 'inverse': [[1,1,0],[0,1,0],[0,0,1]], 'translation': [0,0,0]}
    result={'width':3,'inputs':3,'schedule':[[0],[1]],'frames':[identity,mixing,mixing]}
    # Final q0 = (x0 XOR x1) XOR x1, whose coefficient is2, not integer6+4=10.
    assert replay_model(result,[(2,4),(6,4)],[16,32],[2])
