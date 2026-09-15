"""Replayable finite certificate for the minimum suffix stage bound.

Restricted to distinct products from the specified witness bank and stages of
width1–3. Every allowed full alias, H and ordered quotient basis is enumerated.
For each first successor, the synchronous unlimited-storage relaxation is a
necessary bound. This is not a lower bound for other Boolean constructions.
"""
import argparse,json,hashlib
from pathlib import Path
from collections import Counter
import post190_joint_stage as j
import post190_information_space as i
import post190_semantic_register as s

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--frontier',required=True);p.add_argument('--witness',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    output=Path(a.out);assert not output.exists();output.parent.mkdir(parents=True,exist_ok=True)
    w=json.loads(Path(a.witness).read_text());products,goals=s.bank(w,'y');state=i.restore(json.loads(Path(a.frontier).read_text())[0]);stats=Counter();hist=Counter()
    for values,record in j.joint_stage_successors(state.values,products,(3,2,1),stats):
        clean=tuple(map(i.restrict_clean,values));bound=j.relaxed_stage_bound(i.canonical(clean,s.FULL),products,goals)
        hist[bound]+=1
    result=dict(witness_sha256=hashlib.sha256(Path(a.witness).read_bytes()).hexdigest(),prefix_frontier_sha256=hashlib.sha256(Path(a.frontier).read_bytes()).hexdigest(),prefix_index=0,first_successor_remaining_stage_bound_histogram=dict(hist),minimum_total_suffix_stages=1+min(hist),stats=dict(stats),scope='This saved prefix; distinct fixed witness products; widths1,2,3; arbitrary full affine frames and dirty targets. Not other labels, products, or prefixes.')
    output.write_text(json.dumps(result,indent=2));print(result)
