"""Bounded, reproducible closure experiment for the whole-schedule family."""
from __future__ import annotations
import json, random, statistics, time
from pathlib import Path
from post190_whole_schedule import (cached_replay, exact_metrics, native_metrics,
    replay, anneal, schedule_from_gates, initial_wire_truth_tables)

ROOT=Path(__file__).resolve().parents[1]
HIST=[
 ('depth59',ROOT/'artifacts/destructive_semantic/double_seed42_b16x6_p4_depth59.json'),
 ('depth84',ROOT/'artifacts/destructive_semantic/double_seed1_b64x9_p4_depth84.json'),
]

def cache_benchmark(schedule,repetitions=80):
    initial=initial_wire_truth_tables()
    _,boundaries=replay(schedule, initial)
    rows=[]
    for k in [0,len(schedule)//4,len(schedule)//2,3*len(schedule)//4,len(schedule)]:
        full=[]; suffix=[]
        for _ in range(3):
            t=time.perf_counter()
            for _ in range(repetitions): replay(schedule, initial)
            full.append(time.perf_counter()-t)
            t=time.perf_counter()
            for _ in range(repetitions): cached_replay(schedule,boundaries,k)
            suffix.append(time.perf_counter()-t)
        fm=statistics.median(full); sm=statistics.median(suffix)
        rows.append({'first_changed':k,'full_seconds_median':fm,
                     'cached_seconds_median':sm,'speedup':fm/sm if sm else None,
                     'full_spread':max(full)-min(full),'cached_spread':max(suffix)-min(suffix)})
    return rows

def run():
    out=ROOT/'artifacts/post190_whole_schedule_closure'; out.mkdir(parents=True,exist_ok=True)
    report={'experiment':'POST190 whole-schedule closure','cache':{},'basins':{},'controls':{}}
    for name,path in HIST:
        d=json.loads(path.read_text()); schedule=schedule_from_gates(d['gates'])
        report['cache'][name]=cache_benchmark(schedule)
        report['basins'][name]={'source':str(path.relative_to(ROOT)),
            'layers':len(schedule),'gates':sum(len(x['gates']) for x in schedule),
            'recorded_depth':d['compiled_forward_depth'],
            'recorded_exact_residual':d['exact_affine_distance'],
            'runs':{}}
        for mode in ('tail','single_global','full'):
            vals=[]
            elites=[]
            for seed in range(8):
                r=anneal(schedule,seconds=0.45,iterations=3000,temperature=1000.,
                         cooling=.999,seed=1000+seed,mode=mode)
                em=exact_metrics(r['best_schedule'])
                nm=native_metrics(r['best_schedule'])
                vals.append({'seed':seed,'proxy':r['best_metrics']['proxy_residual'],
                    'exact':em['exact_residual'],'iterations':r['iterations'],
                    'elapsed':r['elapsed'],'uphill_accepted':r['accepted_uphill'],
                    'uphill_rejected':r['rejected_uphill'],
                    'early_accepted':r['accepted_early'],'block_accepted':r['accepted_blocks']})
                elites.append((em['exact_residual'],seed,r,nm,em))
            report['basins'][name]['runs'][mode]=vals
            _,elite_seed,elite,elite_native,elite_exact=min(elites,key=lambda x:x[0])
            report['basins'][name].setdefault('elites',{})[mode]={
                'seed':elite_seed,'proxy':elite['best_metrics']['proxy_residual'],
                **elite_exact,**elite_native,
                'schedule':elite['best_schedule']}
        # Compile only the strongest exact result from the matched runs.
        allruns=[x for mode in report['basins'][name]['runs'].values() for x in mode]
        best=min(allruns,key=lambda x:x['exact'])
        report['basins'][name]['best_exact_across_modes']=best
    # Positive controls: the exact starting hidden schedule is a semantic
    # positive control for the classifier and compiler, not an optimizer claim.
    for name,path in HIST:
        d=json.loads(path.read_text()); s=schedule_from_gates(d['gates'])
        report['controls'][name]={'exact_start':exact_metrics(s), 'native':native_metrics(s)}
    (out/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__': run()
