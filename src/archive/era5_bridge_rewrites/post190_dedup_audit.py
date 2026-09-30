"""Instrument the legacy search without changing its acceptance decisions."""
import argparse,json,functools
from pathlib import Path
import post190_semantic_register as s

@functools.lru_cache(32768)
def metrics(values,times,products,goals):
    ex=s.expressions(values)
    costs=[]
    for a,b,g in products:
        if g in ex or a not in ex or b not in ex:costs.append(None);continue
        choices=s.expose_pair(ex[a],ex[b],times)
        costs.append(min((r[0] for r in choices),default=100000))
    for g in goals:
        done=s.finish(values,times,(g,))
        costs.append(max(done[2]) if done else None)
    return costs

class Audit:
    def __init__(self):self.counts=dict(collisions=0,different_basis=0,different_times=0,better_wire_time=0,better_operand_exposure=0,better_goal_materialization=0,better_future_metric=0);self.examples=[]
    def __call__(self,old,new,products,goals):
        c=self.counts;c['collisions']+=1
        ov,ot=old;nv,nt=new
        c['different_basis']+=ov!=nv;c['different_times']+=ot!=nt
        a=metrics(ov,ot,products,goals);b=metrics(nv,nt,products,goals)
        better=[i for i,(x,y) in enumerate(zip(a,b)) if x is not None and y is not None and y<x]
        wire=any(y<x for x,y in zip(ot,nt));operand=any(i<len(products) for i in better);goal=any(i>=len(products) for i in better)
        c['better_wire_time']+=wire;c['better_operand_exposure']+=operand;c['better_goal_materialization']+=goal;c['better_future_metric']+=bool(better)
        if better and len(self.examples)<8:self.examples.append(dict(retained_values=ov,rejected_values=nv,retained_times=ot,rejected_times=nt,retained_costs=a,rejected_costs=b,better_indices=better))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seconds',type=float,default=10);a=p.parse_args();a.outdir.mkdir(parents=True,exist_ok=False)
    w=json.loads(Path('artifacts/post190_nist_variants_wide/y_candidate_0.json').read_text());audit=Audit();r,_=s.search(w,'y',seconds=a.seconds,beam=16,steps=12,mix=True,audit=audit)
    r.update(audit.counts);r['examples']=audit.examples;(a.outdir/'report.json').write_text(json.dumps(r,indent=2));print(audit.counts)
