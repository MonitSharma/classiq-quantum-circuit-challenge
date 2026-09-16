"""Exact Boolean and relaxed five-batch audit for the x14+y13 witnesses.

This is deliberately a feasibility pre-screen, not an approximate optimizer or
a reversible compiler.  It verifies the fixed witness DAGs, remaps both sides
into one 12-input symbol space, and finds a capacity-optimal precedence batch
schedule.  The affine-frame SAT model is kept separate because a batch count
alone does not prove a <=49-layer native encoder.
"""
from __future__ import annotations
import argparse, json
import itertools
from pathlib import Path
from post190_xag_inplace_lower import outputs

ROOT=Path(__file__).resolve().parents[1]
XPATH=ROOT/'artifacts/post190_nist_variants/x_candidate_0.json'
YPATH=ROOT/'artifacts/post190_nist_variants_wide/y_candidate_0.json'

def rank(vectors):
    piv={}
    for v in vectors:
        while v:
            p=v.bit_length()-1
            if p in piv:v^=piv[p]
            else:piv[p]=v;break
    return len(piv)

def affine_direction(v):
    """Remove the constant coordinate from a semantic coefficient vector.

    Coordinate bit zero is the constant function in the 40-dimensional basis;
    affine translations are therefore quotient directions, not an additional
    linear direction for storage-rank accounting.
    """
    return v & ~1

def rank_directions(vectors):
    """Rank in the affine quotient V/<constant>, over GF(2)."""
    return rank([affine_direction(v) for v in vectors])

def remap(witness, input_offset, node_offset):
    result=[]
    for gate in witness['gates']:
        item={}
        for key in ('a','b'):
            ids,const=gate[key]
            item[key]=([i+input_offset if i<6 else i+node_offset for i in ids],const)
        result.append(item)
    return result

def dependencies(gates):
    return [set(i-12 for key in ('a','b') for i in g[key][0] if i>=12)
            for g in gates]

def capacity_schedule(deps, capacity=6):
    """Find a five-batch schedule by exact bounded backtracking."""
    n=len(deps)
    for batches in range((n+capacity-1)//capacity, n+1):
        chosen=[]
        def search(done, start):
            if len(done)==n:return list(chosen)
            if len(chosen)==batches:return None
            available=[i for i,d in enumerate(deps) if i not in done and d<=done]
            remaining=n-len(done)
            if remaining > (batches-len(chosen))*capacity:return None
            # A deterministic branch order prefers nodes that unlock others.
            available.sort(key=lambda i:(-sum(i in d for d in deps),i))
            need=max(1, remaining-capacity*(batches-len(chosen)-1))
            max_take=min(capacity,len(available))
            from itertools import combinations
            for size in range(max_take,need-1,-1):
                for batch in combinations(available,size):
                    chosen.append(list(batch)); out=search(done|set(batch),0)
                    if out:return out
            return None
        answer=search(set(),0)
        if answer:return answer
    raise AssertionError('no capacity schedule')

def rank_capacity_profile(schedule, operand_vectors, width=18):
    """Necessary rank-capacity DP; never labels physical schedules SAT."""
    ranks={12}
    rows=[]
    for batch in schedule:
        c=rank_directions([v for node in batch for v in operand_vectors[node]])
        incoming=sorted(ranks); outgoing=set()
        k=len(batch)
        for d in ranks:
            if 2*k-c>width-d: continue
            lo=max(d,c+k); hi=min(d+k,c+width-2*k)
            outgoing.update(range(lo,hi+1))
        rows.append({'width':k,'control_rank':c,'incoming_ranks':incoming,
                     'outgoing_ranks':sorted(outgoing),'feasible':bool(outgoing),
                     'spectators':width-3*k})
        ranks=outgoing
    return {'batches':rows,'feasible':bool(ranks),'final_ranks':sorted(ranks)}

def audit(xpath=XPATH,ypath=YPATH):
    x=json.loads(xpath.read_text()); y=json.loads(ypath.read_text())
    assert x['k']==14 and y['k']==13
    # Targets are checked against the repository's exact witness target tables.
    from post190_degree_rank_bound import targets
    assert [outputs(x,v) for v in range(64)]==[[t[v] for t in targets()['x']] for v in range(64)]
    assert [outputs(y,v) for v in range(64)]==[[t[v] for t in targets()['y']] for v in range(64)]
    gates=remap(x,0,6)+remap(y,6,20)
    deps=dependencies(gates)
    batches=capacity_schedule(deps,6)
    # Convert local dependency references to global node references.
    global_deps=[]
    for j,g in enumerate(gates):
        global_deps.append(sorted(i for key in ('a','b') for i in g[key][0] if i>=12))
    for b,batch in enumerate(batches):
        assert all(all(d in sum(batches[:b],[]) for d in deps[i]) for i in batch)
    return {
        'status':'PRESCREEN_PASS', 'x_source':str(xpath.relative_to(ROOT)),
        'y_source':str(ypath.relative_to(ROOT)), 'x_and_nodes':14,
        'y_and_nodes':13, 'total_and_nodes':27, 'batch_capacity':6,
        'nonlinear_batches':len(batches), 'capacity_lower_bound':5,
        'capacity_optimal':len(batches)==5, 'batches':batches,
        'forward_rccx_depth_estimate':len(batches)*7,
        'target_forward_encoder_depth_for_137':49,
        'remaining_affine_budget':14,
        'affine_frame_solver':'NOT_YET_IMPLEMENTED',
        'native_compilation':'NOT_RUN_BY_THIS_PRESCREEN',
        'all_64_side_inputs_verified':True,
    }

def portfolio(xdir=ROOT/'artifacts/post190_nist_variants_wide', ydir=ROOT/'artifacts/post190_nist_variants_wide'):
    """Audit all retained x14/y13 witness pairs for the capacity screen."""
    xp=[]; yp=[]
    for p in sorted(xdir.glob('x_candidate_*.json')):
        w=json.loads(p.read_text())
        if w.get('k')==14: xp.append((p,w))
    for p in sorted(ydir.glob('y_candidate_*.json')):
        w=json.loads(p.read_text())
        if w.get('k')==13: yp.append((p,w))
    rows=[]
    for (px,x),(py,y) in itertools.product(xp,yp):
        gates=remap(x,0,6)+remap(y,6,20)
        ds=dependencies(gates); bs=capacity_schedule(ds,6)
        rows.append({'x_source':str(px.relative_to(ROOT)), 'y_source':str(py.relative_to(ROOT)),
                     'batches':len(bs), 'schedule':bs})
    return {'x_candidates':len(xp),'y_candidates':len(yp),'pairs':rows,
            'all_capacity_optimal':all(r['batches']==5 for r in rows)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,default=ROOT/'artifacts/post190_joint_18wire_feasibility');a=p.parse_args();a.outdir.mkdir(parents=True,exist_ok=True)
    r=audit();r['portfolio']=portfolio();(a.outdir/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':main()
