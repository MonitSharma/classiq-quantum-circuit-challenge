"""Fixed-length non-monotone 18-wire destructive schedules with suffix replay."""
from __future__ import annotations
import argparse, copy, hashlib, json, math, random, time
from pathlib import Path
from destructive_semantic_search import (ALL_ONES, N_WIRES, TARGET,
    affine_distance_proxy, affine_span_solution, apply_cx_semantic,
    apply_rccx_semantic, initial_wire_truth_tables, semantic_hash)

def apply_item(wires,item):
    out=wires
    for gate in item['gates']:
        if gate[0]=='cx': out=apply_cx_semantic(out,gate[1],gate[2])
        elif gate[0]=='rccx': out=apply_rccx_semantic(out,gate[1],gate[2],gate[3])
        else: raise ValueError(gate)
    return out
def legal_layer(gates):
 used=set()
 for g in gates:
  if g[0]=='cx': wires=g[1:]
  else: wires=g[1:]
  if len(set(wires))!=len(wires) or used.intersection(wires): return False
  used.update(wires)
 return True
def replay(schedule, initial=None):
 state=initial or initial_wire_truth_tables(); boundaries=[state]
 for item in schedule:
  state=apply_item(state,item); boundaries.append(state)
 return state,boundaries
def cached_replay(schedule,boundaries,first_changed):
 if not 0<=first_changed<=len(schedule): raise ValueError(first_changed)
 out=list(boundaries[:first_changed+1]); state=out[-1]
 for item in schedule[first_changed:]:
  state=apply_item(state,item); out.append(state)
 return state,out
def schedule_hash(schedule): return hashlib.blake2b(json.dumps(schedule,sort_keys=True).encode(),digest_size=16).hexdigest()
def random_layer(rng,n=18,max_gates=6):
 wires=list(range(n));rng.shuffle(wires); gates=[]
 for _ in range(rng.randint(0,max_gates)):
  if len(wires)<3:break
  a,b,t=wires[:3];wires=wires[3:]
  if rng.random()<.35:gates.append(['cx',a,b])
  else:gates.append(['rccx',a,b,t])
 return {'gates':gates}
def random_schedule(rng,layers=7): return [random_layer(rng) for _ in range(layers)]
def mutate(schedule,rng):
 out=copy.deepcopy(schedule); k=rng.randrange(len(out)); kind=rng.random()
 if kind<.35: out[k]=random_layer(rng)
 elif kind<.7:
  gates=out[k]['gates'][:]
  if gates and rng.random()<.7:
   j=rng.randrange(len(gates)); replacement=random_layer(rng, max_gates=1)['gates']
   gates[j]=replacement[0] if replacement else gates[j]
   gates=[g for g in gates if g];
  else: gates.extend(random_layer(rng,max_gates=1)['gates'])
  # Rebuild the layer if a one-gate replacement collided with another gate.
  out[k]={'gates':gates} if legal_layer(gates) else random_layer(rng)
 elif kind<.85 and len(out)>1:
  j=rng.randrange(len(out)); out[k],out[j]=out[j],out[k]; k=min(k,j)
 else:
  # ruin/recreate a short interior block
  end=min(len(out),k+rng.randint(1,3))
  for j in range(k,end): out[j]=random_layer(rng)
 return out,k
def score(wires,target=TARGET):
 exact=0 if affine_span_solution(wires,target) is not None else 1
 residual,combo=affine_distance_proxy(wires,target,max_order=2)
 return (exact,residual),{'proxy_residual':residual,'combo':combo,'semantic_hash':semantic_hash(wires)}
def anneal(schedule,target=TARGET,seconds=10,iterations=10000,temperature=20.,cooling=.9995,seed=0):
 rng=random.Random(seed); current=copy.deepcopy(schedule); state,boundaries=replay(current); key,metrics=score(state,target); best=(key,metrics,current,state); accepted_uphill=0; rejected_uphill=0; accepted_early=0; accepted_blocks=0; start=time.monotonic(); it=0
 while it<iterations and time.monotonic()-start<seconds:
  trial,first=mutate(current,rng); nstate,nb=cached_replay(trial,boundaries,first); nkey,nmetrics=score(nstate,target); delta=(nkey[0]-key[0])*10000+nkey[1]-key[1]
  accept=delta<=0 or rng.random()<math.exp(-delta/max(.001,temperature))
  if accept:
   if delta>0:accepted_uphill+=1
   current,boundaries,state,key,metrics=trial,nb,nstate,nkey,nmetrics
   if first<len(current)//2:accepted_early+=1
   if len(current)>0 and len(trial[first]['gates'])>1:accepted_blocks+=1
   if (key,metrics['semantic_hash'])<(best[0],best[1]['semantic_hash']): best=(key,metrics,copy.deepcopy(current),state)
  elif delta>0: rejected_uphill+=1
  temperature*=cooling; it+=1
 return {'iterations':it,'elapsed':time.monotonic()-start,'best_key':best[0],'best_metrics':best[1],'accepted_uphill':accepted_uphill,'rejected_uphill':rejected_uphill,'accepted_early':accepted_early,'accepted_blocks':accepted_blocks,'best_schedule':best[2]}
def main():
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,default=Path('artifacts/post190_whole_schedule'));p.add_argument('--seconds',type=float,default=10);p.add_argument('--iterations',type=int,default=10000);p.add_argument('--seed',type=int,default=0);a=p.parse_args();a.outdir.mkdir(parents=True,exist_ok=True); r=anneal(random_schedule(random.Random(a.seed)),seconds=a.seconds,iterations=a.iterations,seed=a.seed);(a.outdir/'pilot.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k!='best_schedule'},indent=2))
if __name__=='__main__': main()
