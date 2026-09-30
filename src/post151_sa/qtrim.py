"""Loader trimming: loader gates that are not commutation-ancestors of any code-wire gate (set Q) can be
moved to the loader end, where they commute with the kernel and cancel against their mirror. Drop them."""
import sys, pickle
sys.path.insert(0,'.')
from kdrv import full_gates, XW, YW, PHYS
from build import loader_ops
from canc import tag, com
def conv(ops): return [('cx',(o[1],o[2]),None) if o[0]=='cx' else ('u3',(o[1],),o[2]) for o in ops]
def split_PQ(Lops, code):
    F=[tag(o) for o in Lops]; n=len(F)
    succ=[set() for _ in range(n)]; last=[[] for _ in range(18)]
    for j in range(n):
        for w in F[j][1]:
            for i in last[w]:
                if not com(F[i],F[j]): succ[i].add(j)
            last[w].append(j)
    isP=[any(w in code for w in F[i][1]) for i in range(n)]
    for i in reversed(range(n)):
        if not isP[i] and any(isP[j] for j in succ[i]): isP[i]=True
    return isP
if __name__=='__main__':
    DX,DY,pl=pickle.load(open('../../../champ117.pkl','rb'))
    code=set(PHYS[w] for w in pl[1])
    L=conv(loader_ops(full_gates(DX),XW)+loader_ops(full_gates(DY),YW))
    isP=split_PQ(L,code)
    Q=[L[i] for i in range(len(L)) if not isP[i]]
    print('loader gates',len(L),'Q (droppable)',len(Q),'Q cx',sum(1 for o in Q if o[0]=='cx'))
    for o in Q: print('  ',o[0],o[1])
