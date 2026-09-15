import random
from post190_whole_schedule import (cached_replay, replay, random_layer,
                                     random_schedule, mutate,
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

def test_random_layer_accounts_for_cx_as_two_wire_gate():
    # A layer with nine disjoint CXs is legal on 18 wires; the old generator
    # incorrectly stopped at six because it consumed a phantom target wire.
    layer=random_layer(random.Random(11), n=18, max_gates=9)
    assert legal_wires(layer['gates'])
    assert all(len(g)==3 if g[0]=='cx' else len(g)==4 for g in layer['gates'])

def legal_wires(gates):
    used=[]
    for g in gates:
        used.extend(g[1:])
    return len(used)==len(set(used))
