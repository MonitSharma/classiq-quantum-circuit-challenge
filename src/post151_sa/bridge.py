import sys, random, time, numpy as np
from postopt import parse_ops, commute, dag, schedule, fuse, depth, write, resched
def slack_critical(ops):
    n=len(ops); est=[0]*n; wt=[0]*18
    for i,op in enumerate(ops):
        l=max(wt[w] for w in op[1])+1
        for w in op[1]: wt[w]=l
        est[i]=l
    D=max(wt); lst=[0]*n; wt2=[D+1]*18
    for i in reversed(range(n)):
        op=ops[i]; l=min(wt2[w] for w in op[1])-1
        for w in op[1]: wt2[w]=l
        lst[i]=l
    return [lst[i]-est[i] for i in range(n)], D
def moves(ops, crit):
    mv=[]
    for i,op in enumerate(ops):
        if op[0]!='cx' or crit[i]>0: continue
        for direction,rng in [('right',range(i+1,len(ops))),('left',range(i-1,-1,-1))]:
            for j in rng:
                o=ops[j]
                if commute(op,o): continue
                if o[0]=='cx' and len(set(op[1]+o[1]))==3: mv.append((min(i,j),max(i,j),direction))
                break
    return list(dict.fromkeys(mv))
def bridge_pair(first, second):
    a,b=first; c,d=second
    if b==c: return (a,d)
    assert d==a; return (c,b)
def rewrite(ops,i,j,direction):
    first,second=ops[i],ops[j]
    if not all(commute(first if direction=='right' else second, ops[k]) for k in range(i+1,j)): return None
    try: mid=bridge_pair(first[1],second[1])
    except AssertionError: return None
    out=[]
    for k,op in enumerate(ops):
        if k==(j if direction=='right' else i):
            out.append(('cx',second[1],None)); out.append(('cx',mid,None)); out.append(('cx',first[1],None))
        if k not in (i,j): out.append(op)
    return out
def search(ops, rounds=5, seeds=4, maxmoves=200, t_budget=1800, verbose=True):
    t0=time.time(); cur=fuse(ops); cd=depth(cur)
    for r in range(rounds):
        crit,D=slack_critical(cur); mv=moves(cur,crit); random.shuffle(mv); mv=mv[:maxmoves]
        best=None
        for (i,j,dr) in mv:
            if time.time()-t0>t_budget: break
            cand=rewrite(cur,i,j,dr)
            if cand is None: continue
            cand=fuse(cand)
            d0=depth(cand); cx0=sum(1 for x in cand if x[0]=='cx')
            if best is None or (d0,cx0)<best[:2]: best=(d0,cx0,cand)
            if d0>cd+1: continue
            succ,pred=dag(cand)
            for s in range(seeds):
                o=schedule(cand,succ,pred,s); c2=fuse([cand[k] for k in o]); d=depth(c2)
                cx=sum(1 for x in c2 if x[0]=='cx')
                if best is None or (d,cx)<best[:2]: best=(d,cx,c2)
        if verbose: print("round",r,"moves",len(mv),"best",best[:2] if best else None,"current",cd,"t %.0f"%(time.time()-t0),flush=True)
        if best is None or best[0]>cd: break
        if best[0]==cd:
            # accept equal-depth move with fewer/equal cx to diversify once
            cur=best[2]; continue
        cur=best[2]; cd=best[0]
        cur,cd=resched(cur,trials=400,rounds=2)
    return cur,cd
if __name__=="__main__":
    ops=parse_ops(sys.argv[1])
    cur,cd=search(ops,rounds=int(sys.argv[3]),maxmoves=int(sys.argv[4]),t_budget=float(sys.argv[5]))
    write(cur,sys.argv[2]); print("final",cd,"cx",sum(1 for x in cur if x[0]=='cx'))
