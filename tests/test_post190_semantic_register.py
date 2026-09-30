from post190_semantic_register import INPUTS,bank,step,search,closure,verify,compile_ops


def test_dirty_overwrite_preserves_actual_truth_not_a_clean_node():
    initial=INPUTS+(0,0,0)
    result=step(initial,[('ccx',(0,1,2))])
    assert result[2]==INPUTS[2]^(INPUTS[0]&INPUTS[1])
    assert result[2] != INPUTS[0]&INPUTS[1]
    # The seeded closure must not magically recover an input that was lost.
    assert not closure(result,(),(INPUTS[2],))


def test_mutable_coordinate_output_and_free_placement():
    goals=(INPUTS[2]^(INPUTS[0]&INPUTS[1]),INPUTS[3],INPUTS[4],INPUTS[5])
    ops=[('ccx',(0,1,2))]
    q=compile_ops(ops);r=verify(q,[2,3,4,5],goals)
    assert r['depth']==7


def test_seeded_compiler_finds_complete_positive_control():
    w={'k':1,'gates':[{'a':([0],False),'b':([1],False)}],
       'outs':[([2,6],False),([3],False),([4],False)]}
    result,best=search(w,'y',seconds=8,beam=8,steps=3)
    assert best is not None
    assert best[0]['checked_inputs']==64
    assert best[0]['depth']<20


def test_affine_variant_x14_is_exact_for_all_inputs():
    import json
    from pathlib import Path
    from post190_degree_rank_bound import targets
    from post190_xag_inplace_lower import outputs
    p=Path('artifacts/post190_nist_variants/x_candidate_0.json')
    w=json.loads(p.read_text());assert w['k']==14
    assert all(outputs(w,x)==[t[x] for t in targets()['x']] for x in range(64))


def test_span_key_ignores_reversible_linear_frame_changes():
    from post190_semantic_register import span_key
    values=INPUTS+(0,0,0)
    assert span_key(values)==span_key(step(values,[('cx',(0,1)),('x',(2,))]))


def test_wider_affine_search_y13_is_exact_for_all_inputs():
    import json
    from pathlib import Path
    from post190_degree_rank_bound import targets
    from post190_xag_inplace_lower import outputs
    w=json.loads(Path('artifacts/post190_nist_variants_wide/y_candidate_0.json').read_text())
    assert w['k']==13
    assert all(outputs(w,x)==[t[x] for t in targets()['y']] for x in range(64))
