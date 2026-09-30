"""Corrected fixed-schedule portfolio probes; never a family-wide UNSAT claim."""
import json,random,time
from pathlib import Path
from post190_joint_18wire_storage_sat import combined_data,fixed_frame_solver,XPATH,YPATH
from post190_joint_18wire_feasibility import dependencies
from post190_joint_18wire_freeframe_sat import candidate_tables,truth,rank


def run(out,limit=8):
    assert not out.exists();out.mkdir(parents=True)
    portfolio=json.loads(Path('artifacts/post190_joint_18wire_feasibility/report.json').read_text())['portfolio']['pairs']
    chosen=[portfolio[i] for i in [0,7,8,15,16,23,24,31]][:limit]
    rng=random.Random(18516)
    # Also sample distinct precedence-legal five-batch schedules for pair zero.
    _,_,_,gates=combined_data();deps=dependencies(gates);extra=[];seen=set()
    for _ in range(500):
        done=set();schedule=[]
        for stage in range(5):
            ready=[i for i,d in enumerate(deps) if i not in done and d<=done]
            rng.shuffle(ready);batch=ready[:6];done.update(batch);schedule.append(batch)
        key=tuple(tuple(sorted(b)) for b in schedule)
        if len(done)==27 and key not in seen:
            seen.add(key);extra.append(dict(x_source=str(XPATH),y_source=str(YPATH),schedule=schedule))
        if len(extra)==4:break
    rows=[]
    for item in chosen+extra:
        px,py=Path(item['x_source']),Path(item['y_source'])
        xt,_=candidate_tables(json.loads(px.read_text()),'x');yt,_=candidate_tables(json.loads(py.read_text()),'y')
        functions=[(1<<4096)-1]+[truth(lambda z,i=i:bool(z>>i&1)) for i in range(12)]+xt+yt
        assert rank(functions)==40, 'Dependent formal coordinates require a semantic quotient model'
        operands,nodes,endpoints,_=combined_data(px,py)
        r=fixed_frame_solver(item['schedule'],timeout_ms=3000,data=(operands,nodes,endpoints))
        r.update(x_source=str(px),y_source=str(py),semantic_rank=40)
        rows.append(r);(out/'report.json').write_text(json.dumps(rows,indent=2)+'\n')
        print(len(rows),r['status'],r['seconds'],flush=True)
    return rows


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);a=p.parse_args();run(a.outdir)
