"""Semantic-only hyperplane search, followed by physical replay.

With unrestricted free affine changes, each update retains a hyperplane H
containing both controls and replaces its complementary direction v by v+ab.
Enumerate every hyperplane containing a chosen full control pair. Quotienting
by clean span here tests reachability ONLY: it makes no physical dominance or
depth-optimality claim. Every retained representative has a physical prefix.
"""
import argparse,itertools,json,time,random
from pathlib import Path
from qiskit import qasm2
import post190_information_space as i
import post190_semantic_register as s


def transitions(st,products,goals,aliases=8):
    ex=i.preimage_bank(st.values);seen=set()
    for gate,(a,b,g) in enumerate(products):
        if a not in ex or b not in ex:continue
        for (_,am),(_,bm) in itertools.product(ex[a][:aliases],ex[b][:aliases]):
            choices=i.broad_expose(am,bm,st.times,1)
            if not choices:continue
            _,_,pre,p,r=choices[0];base=i.full_step(st.values,pre)
            other=[j for j in range(9) if j not in (p,r)]
            # All nonzero linear functionals vanishing on these two controls.
            for subset in range(1,1<<7):
                support=[other[j] for j in range(7) if subset>>j&1];t=support[0]
                mix=tuple(('cx',(t,j)) for j in support[1:]);tail=pre+mix+(('ccx',(p,r,t)),)
                out=list(base)
                for j in support[1:]:out[j]^=base[t]
                out[t]^=base[p]&base[r];out=tuple(out)
                clean=tuple(map(i.restrict_clean,out));key=i.canonical(clean,s.FULL)
                if key in seen:continue
                seen.add(key)
                yield key,out,tail,gate


def search(w,side,seconds=30,beam=48,steps=24,seed=0,initial=None,aliases=8):
    products,goals=s.bank(w,side);rng=random.Random(seed);start=time.monotonic();frontier=initial or [i.State(i.INITIAL,(0,)*9,())];seen=set();archive={};expanded=0;best=None;history=[];timeout=False
    def score(st):
        m=i.state_metrics(st.clean,products,goals)
        # Primary question is reachability: timing is excluded from ranking.
        return -30*m['rank_deficit']-10*m['remaining']+6*len(m['present'])+.3*len(m['held'])+.05*m['inputs']
    for st in frontier:archive[i.canonical(st.clean,s.FULL)]=st
    for layer in range(steps):
        candidates=[]
        for st in frontier:
            if time.monotonic()-start>=seconds:timeout=True;break
            for key,out,tail,gate in transitions(st,products,goals,aliases):
                expanded+=1
                if time.monotonic()-start>=seconds:timeout=True;break
                if key in seen:continue
                seen.add(key)
                if not i.semantic_closure(key,products,goals):continue
                candidate=i.State(out,s.timing(st.times,tail),st.ops+tail,st.stages+1)
                met=i.state_metrics(candidate.clean,products,goals)
                if met['rank_deficit']==0:
                    done=s.finish(candidate.clean,candidate.times,goals)
                    if done:
                        finish,places,_=done;ops=candidate.ops+tuple(finish);q=s.compile_ops(ops);report=s.verify(q,places,goals);best=dict(report=report,ops=ops,qasm=qasm2.dumps(q));archive[key]=candidate;break
                candidates.append((score(candidate)+rng.random()*.8,candidate,key,gate))
            if timeout or best:break
        candidates.sort(key=lambda row:row[0],reverse=True)
        # Diversity by goal mask AND represented product frontier.
        selected=[];groups={}
        for _,st,key,gate in candidates:
            m=i.state_metrics(st.clean,products,goals);group=(tuple(m['present']),tuple(m['held']),tuple(m['ready']))
            if groups.get(group,0)>=max(2,beam//8):continue
            selected.append(st);groups[group]=groups.get(group,0)+1;archive[key]=st
            if len(selected)>=beam:break
        if len(archive)>256:archive=dict(sorted(archive.items(),key=lambda kv:score(kv[1]),reverse=True)[:128])
        if selected:history.append(dict(step=layer+1,expanded=expanded,**i.state_metrics(selected[0].clean,products,goals)))
        if timeout or best or not selected:break
        frontier=selected
    partials=sorted(archive.values(),key=score,reverse=True)[:24];ms=[i.state_metrics(st.clean,products,goals) for st in archive.values()]
    report=dict(status='complete' if best else 'timeout' if timeout else 'bounded_search_finished',expanded=expanded,unique_semantic_spans=len(seen),elapsed=time.monotonic()-start,maximum_goals=max(len(m['present']) for m in ms),best_rank_deficit=min(m['rank_deficit'] for m in ms),best_suffix_estimate=min(m['remaining'] for m in ms),maximum_held_products=max(len(m['held']) for m in ms),history=history,limitation='Semantic quotient, no depth-optimality claim; bounded beam and aliases.')
    return report,best,[i.snapshot(st,products,goals) for st in partials]

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--witness',required=True);p.add_argument('--side',choices=['x','y'],required=True);p.add_argument('--outdir',required=True);p.add_argument('--seconds',type=float,default=30);p.add_argument('--beam',type=int,default=48);p.add_argument('--steps',type=int,default=24);p.add_argument('--seed',type=int,default=0);p.add_argument('--aliases',type=int,default=8);p.add_argument('--frontier');a=vars(p.parse_args());out=Path(a.pop('outdir'));out.mkdir(parents=True,exist_ok=False);(out/'config.json').write_text(json.dumps(a,indent=2));w=json.loads(Path(a.pop('witness')).read_text());path=a.pop('frontier');initial=[i.restore(d) for d in json.loads(Path(path).read_text())[:4]] if path else None
    report,best,partials=search(w,initial=initial,**a);(out/'frontier.json').write_text(json.dumps(partials,indent=2))
    if best:
        (out/'encoder.qasm').write_text(best['qasm']);report['best']=s.verify(qasm2.loads(best['qasm']),best['report']['outputs'],s.bank(w,a['side'])[1]);(out/'trajectory.json').write_text(json.dumps(best['ops'],indent=2))
    (out/'report.json').write_text(json.dumps(report,indent=2));print({k:v for k,v in report.items() if k!='history'})
