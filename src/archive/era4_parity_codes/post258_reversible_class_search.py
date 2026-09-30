"""Depth-bounded destructive local class encoders with free output-wire choice.

All candidate gates are reversible on nine wires. Only three inputs are clean.
Four output wires need distinguish row/column classes; other wires may retain
arbitrary garbage. The whole oracle must use E.inverse() after a diagonal kernel.
"""
import argparse,functools,itertools,json,time
from pathlib import Path
import two_stage_oracle as ts

FULL=(1<<64)-1
INITIAL=tuple([sum(((x>>b)&1)<<x for x in range(64)) for b in range(6)]+[0]*3)
TRIPLES={t:list(itertools.combinations([i for i in range(9) if i!=t],3)) for t in range(9)}
@functools.lru_cache(maxsize=300000)
def separates(table):
    out=0
    for x in range(64):out|=((FULL^table) if table>>x&1 else table)<<(64*x)
    return out


def run(side,outdir,beam_size,steps,max_depth):
    assert not outdir.exists();outdir.mkdir(parents=True)
    cls=ts.ROWCLS if side=='y' else ts.COLCLS
    required=sum(sum((cls[x]!=cls[y])<<y for y in range(64))<<(64*x) for x in range(64))
    def score(regs,seps,old_best=None,changed=None):
        best=(100000,None)
        combos=itertools.combinations(range(9),4) if changed is None else ((changed,)+c for c in TRIPLES[changed])
        if old_best is not None and changed not in old_best[1]:best=old_best
        for wires in combos:
            a,b,c,d=wires
            covered=seps[a]|seps[b]|seps[c]|seps[d]
            errors=(required&~covered).bit_count()//2
            if errors<best[0]:best=(errors,tuple(sorted(wires)))
        return best
    seps=tuple(map(separates,INITIAL));base=score(INITIAL,seps)
    # state: objective, collisions, outputs, regs, seps, times, history
    beam=[(base[0],base[0],base[1],INITIAL,seps,(0,)*9,[])]
    seen={tuple(sorted(INITIAL)):0};checkpoints=[];start=time.monotonic();best_seen=base[0]
    for step in range(steps):
        nexts={}
        for _,err,outputs,regs,seps,times,hist in beam:
            for target in range(9):
                for size in [1,2]:
                    for controls in itertools.combinations([i for i in range(9) if i!=target],size):
                        term=FULL
                        for c in controls:term&=regs[c]
                        if not term:continue
                        new=regs[target]^term
                        if new in regs:continue
                        dep=max(times[c] for c in controls+(target,))+(1 if size==1 else 9)
                        if dep>max_depth:continue
                        nr=list(regs);nr[target]=new;nr=tuple(nr);key=tuple(sorted(nr))
                        nt=list(times)
                        for c in controls+(target,):nt[c]=dep
                        depth=max(nt)
                        if seen.get(key,9999)<=depth:continue
                        ns=list(seps);ns[target]=separates(new);ns=tuple(ns)
                        ne,no=score(nr,ns,(err,outputs),target)
                        obj=ne+0.03*depth+0.001*sum(nt)
                        if key not in nexts or obj<nexts[key][0]:
                            nexts[key]=(obj,ne,no,nr,ns,tuple(nt),hist+[(controls,target)])
        beam=sorted(nexts.values(),key=lambda r:r[0])[:beam_size]
        if not beam:break
        for r in beam:seen[tuple(sorted(r[3]))]=max(r[5])
        best=min(beam,key=lambda r:(r[1],max(r[5])))
        print(side,'step',step+1,'collisions',best[1],'estimated_depth',max(best[5]),'states',len(nexts),flush=True)
        if best[1]<best_seen:
            best_seen=best[1]
            row=dict(side=side,step=step+1,collisions=best[1],outputs=best[2],regs=best[3],times=best[5],history=best[6]);checkpoints.append(row)
            (outdir/f'checkpoint{step+1}.json').write_text(json.dumps(row,indent=2)+'\n')
        if best[1]==0:break
    (outdir/'report.json').write_text(json.dumps(dict(side=side,beam_size=beam_size,steps=steps,max_depth=max_depth,seconds=time.monotonic()-start,checkpoints=checkpoints),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--side',choices=['x','y'],required=True);p.add_argument('--outdir',type=Path,required=True);p.add_argument('--beam',type=int,default=30);p.add_argument('--steps',type=int,default=16);p.add_argument('--max-depth',type=int,default=55);a=p.parse_args();run(a.side,a.outdir,a.beam,a.steps,a.max_depth)
