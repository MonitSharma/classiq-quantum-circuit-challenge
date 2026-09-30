"""Enumerate and solve the fixed x14/y13 five-batch storage model."""
from __future__ import annotations
import argparse,json,time
from pathlib import Path
from itertools import combinations
from post190_joint_18wire_storage_sat import combined_data, fixed_frame_solver
from post190_joint_18wire_feasibility import dependencies, rank_capacity_profile

ROOT=Path(__file__).resolve().parents[1]

def schedules(deps,batches=5,capacity=6):
    n=len(deps)
    def rec(done,parts):
        if len(parts)==batches:
            if done.bit_count()==n: yield tuple(parts)
            return
        available=[i for i,d in enumerate(deps) if not (done>>i&1) and all(done>>j&1 for j in d)]
        left=batches-len(parts)-1
        min_size=max(1,n-done.bit_count()-left*capacity)
        max_size=min(capacity,len(available),n-done.bit_count())
        for size in range(min_size,max_size+1):
            for batch in combinations(available,size):
                mask=sum(1<<i for i in batch)
                yield from rec(done|mask,parts+[tuple(batch)])
    yield from rec(0,[])

def main():
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,default=ROOT/'artifacts/post190_joint_storage_exhaustive_v3/candidate0_0');p.add_argument('--timeout-ms',type=int,default=3000);p.add_argument('--limit',type=int,default=0);a=p.parse_args();a.outdir.mkdir(parents=True,exist_ok=True)
    operands,_,_,g=combined_data(); deps=dependencies(g); start=time.monotonic();counts={'total':0,'sat':0,'unsat':0,'unknown':0,'rank_pruned':0}; first_sat=None; times=[]; rank_rows=[]
    for sch in schedules(deps):
        counts['total']+=1
        if a.limit and counts['total']>a.limit:break
        rp=rank_capacity_profile(sch,operands)
        if not rp['feasible']:
            counts['rank_pruned']+=1; continue
        r=fixed_frame_solver([list(x) for x in sch],timeout_ms=a.timeout_ms)
        counts[r['status'].lower()]=counts.get(r['status'].lower(),0)+1;times.append(r['seconds'])
        if r['status']=='SAT':first_sat=r;break
    result={'status':'SAT_FOUND' if first_sat else 'EXHAUSTED' if not a.limit or counts['total']<=a.limit else 'LIMITED','counts':counts,'timeout_ms':a.timeout_ms,'elapsed':time.monotonic()-start,'solve_seconds_min':min(times) if times else None,'solve_seconds_max':max(times) if times else None,'first_sat':first_sat,'rank_filter':'necessary only; skipped schedules are not UNSAT'}
    (a.outdir/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
