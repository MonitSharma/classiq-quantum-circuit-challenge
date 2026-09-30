import sys, numpy as np
from postopt import parse_ops, fuse, depth
from canc import tag, com
def build(ops):
    """commutation DAG: edge i->j (i<j) if they share a wire and don't commute; transitively reduced per wire approx"""
    T=[tag(o) for o in ops]; n=len(T)
    succ=[set() for _ in range(n)]; pred=[set() for _ in range(n)]
    last=[[] for _ in range(18)]  # per wire: list of indices seen
    for j in range(n):
        b=T[j]
        for w in b[1]:
            # walk back on wire w; add edge to non-commuting gates; can stop once we hit a gate that doesn't commute AND
            # all earlier ones are ordered before it?  keep simple: full scan (n small)
            for i in reversed(last[w]):
                if i in pred[j]: continue
                if not com(T[i],b): succ[i].add(j); pred[j].add(i)
            last[w].append(j)
    return T,succ,pred
def heads_tails(n,succ,pred):
    h=[1]*n
    for j in range(n):
        if pred[j]: h[j]=1+max(h[i] for i in pred[j])
    t=[1]*n
    for i in reversed(range(n)):
        if succ[i]: t[i]=1+max(t[j] for j in succ[i])
    return h,t
if __name__=='__main__':
    ops=fuse(parse_ops(sys.argv[1])); T,succ,pred=build(ops); n=len(T)
    h,t=heads_tails(n,succ,pred)
    print('n',n,'depth',depth(ops),'LP',max(h),'edges',sum(map(len,succ)))
    cnt=[0]*18
    for o in ops:
        for w in o[1]: cnt[w]+=1
    print('maxcount',max(cnt))
    # per-wire bound: for wire w, gates on w need distinct layers; min over gates head-1 + count + min tail-1
    for w in range(18):
        g=[i for i in range(n) if w in T[i][1]]
        print(w,len(g),'minhead',min(h[i] for i in g)-1,'mintail',min(t[i] for i in g)-1,'bound',len(g)+min(h[i] for i in g)-1+min(t[i] for i in g)-1)
