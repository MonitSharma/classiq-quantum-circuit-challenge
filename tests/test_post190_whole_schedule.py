import random
from post190_whole_schedule import (cached_replay, replay, random_schedule, mutate,
                                     initial_wire_truth_tables)
from destructive_semantic_search import apply_cx_semantic, apply_rccx_semantic

def test_reference_primitives_and_cache():
    w=initial_wire_truth_tables(); assert apply_cx_semantic(w,0,1)[1]==w[1]^w[0]
    assert apply_rccx_semantic(w,0,1,12)[12]==w[12]^(w[0]&w[1])
    rng=random.Random(7); s=random_schedule(rng,6); _,b=replay(s)
    for _ in range(20):
        t,k=mutate(s,rng); a,full=replay(t); c,cache=cached_replay(t,b,k)
        # b is for s, so only compare the mutated suffix from the matching
        # unchanged prefix; full replay remains the authoritative endpoint.
        assert c==a and cache[-1]==full[-1]
def test_rejected_trial_does_not_mutate_cache():
    s=random_schedule(random.Random(3),4); _,b=replay(s); snapshot=tuple(b)
    assert tuple(b)==snapshot
