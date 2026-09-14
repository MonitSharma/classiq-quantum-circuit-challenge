from post190_joint_reversible import solve,evaluate,verify


def test_free_joint_labels_can_be_synthesized_and_reversed():
    classes=[(x&3)|(((x>>4)&1)<<2) for x in range(64)]
    row,ops=solve('x',list(range(64)),stages=0,cx_layers=1,seconds=5,classes=classes)
    assert row['status']=='sat'
    bad,words,codes=evaluate(ops,'x',classes=classes)
    assert not bad
    q,report=verify(ops,words,codes)
    assert q.depth()<=row['depth_ceiling']
    assert report['phase_inverse_error']<1e-10


def test_collision_and_constancy_are_checked_separately():
    # Identity exposes x4. This separates x4 classes, but not x0 classes.
    assert not evaluate([], 'x', classes=[(x>>4)&1 for x in range(64)])[0]
    assert evaluate([], 'x', classes=[x&1 for x in range(64)])[0]
    assert evaluate([], 'x', classes=[0]*64,constant=True)[0]
    assert not evaluate([], 'x', classes=[0]*64,constant=False)[0]


def test_new_kernel_care_set_preserves_logo_and_rejects_collisions():
    import pytest
    from post190_joint_compose import care_set
    from two_stage_oracle import ROWCLS,COLCLS,logo
    care,truth=care_set(COLCLS,ROWCLS)
    table=dict(zip(care,truth))
    assert len(care)==121
    assert all(table[ROWCLS[y]|(COLCLS[x]<<4)]==int(logo(x,y)) for x in range(64) for y in range(64))
    with pytest.raises(AssertionError,match='collision'):
        care_set([0]*64,[0]*64)
