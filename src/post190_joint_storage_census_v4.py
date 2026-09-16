"""Exact five-stage schedule census for the joint x14+y13 storage model.

This counts topological schedules by ordered batch-width pattern without
building affine SAT models.  The rank column is a necessary quotient-rank
filter only; it is not a storage satisfiability result.
"""
from __future__ import annotations
import argparse, itertools, json, time
from functools import lru_cache
from pathlib import Path
from post190_joint_18wire_storage_sat import combined_data
from post190_joint_18wire_feasibility import dependencies, rank_directions

ROOT = Path(__file__).resolve().parents[1]

def width_patterns():
    return [p for p in itertools.product(range(1, 7), repeat=5) if sum(p) == 27]

def _next_ranks(ranks, k, c, width=18):
    out=set()
    for d in ranks:
        if 2*k-c > width-d:
            continue
        lo=max(d, c+k)
        hi=min(d+k, c+width-2*k)
        out.update(range(lo, hi+1))
    return tuple(sorted(out))

def census_pattern(deps, operands, pattern, width=18, include_rank=True):
    n=len(deps)
    @lru_cache(None)
    def control_rank(batch):
        return rank_directions([v for i in batch for v in operands[i]])

    @lru_cache(None)
    def total(done, stage):
        if stage == len(pattern):
            return int(done.bit_count() == n)
        k=pattern[stage]
        available=[i for i,d in enumerate(deps) if not (done >> i & 1) and all(done >> j & 1 for j in d)]
        ans=0
        for batch in itertools.combinations(available, k):
            mask=sum(1 << i for i in batch)
            ans += total(done | mask, stage + 1)
        return ans

    @lru_cache(None)
    def rank_pass(done, stage, ranks):
        if stage == len(pattern):
            return int(done.bit_count() == n and bool(ranks))
        k=pattern[stage]
        available=[i for i,d in enumerate(deps) if not (done >> i & 1) and all(done >> j & 1 for j in d)]
        ans=0
        for batch in itertools.combinations(available, k):
            mask=sum(1 << i for i in batch)
            nxt=_next_ranks(ranks, k, control_rank(batch), width)
            if nxt:
                ans += rank_pass(done | mask, stage + 1, nxt)
        return ans

    if not include_rank:
        return {'pattern':list(pattern), 'schedules':total(0,0),
                'rank_survivors':None, 'total_states':total.cache_info().currsize,
                'rank_states':None}
    initial=(12,)
    return {'pattern':list(pattern), 'schedules':total(0,0),
            'rank_survivors':rank_pass(0,0,initial),
            'total_states':total.cache_info().currsize,
            'rank_states':rank_pass.cache_info().currsize}

def run():
    p=argparse.ArgumentParser(); p.add_argument('--outdir', type=Path, required=True); p.add_argument('--skip-rank', action='store_true')
    a=p.parse_args(); a.outdir.mkdir(parents=True, exist_ok=True)
    operands,_,_,gates=combined_data(); deps=dependencies(gates)
    started=time.monotonic(); rows=[census_pattern(deps, operands, p, include_rank=not a.skip_rank) for p in width_patterns()]
    result={'status':'EXACT_CENSUS_COMPLETE','node_count':len(deps),'stage_count':5,
            'capacity':6,'width_patterns':len(rows),'rows':rows,
            'rank_definition':'GF(2) rank after removing semantic constant coordinate bit 0',
            'rank_filter':'necessary only; survivors are not storage SAT witnesses',
            'seconds':time.monotonic()-started}
    (a.outdir/'census.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
    for r in rows: print(r)

if __name__=='__main__': run()
