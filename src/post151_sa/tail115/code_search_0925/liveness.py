"""liveness.py loader.pkl : find loader ops that are useless (only affect garbage final rows), and when each garbage wire is really free."""
import sys, pickle
sys.path.insert(0,'/work/classiq/src/post151_sa')
from satwin3 import *
from sim import symbolic_final
def analyze(D):
    g=D['gates']+[(('cx',),c,t) for c,t in D.get('fix',[])]
    layers=layerize(g); pl,pidx=plist_of(D); states,recs=replay(layers,len(layers),pidx,pl)
    fin=states[-1][0]; req=set(D['req'])|{256,384}
    code=[w for w in range(9) if fin[w] in req]
    live=set(code)            # wires whose current value matters (backward)
    useful=[[False]*len(r) for r in recs]
    for k in range(len(recs)-1,-1,-1):
        L=recs[k]; newlive=set(live)
        for j,op in enumerate(L):
            if op[0] in ('R','H','O'):
                useful[k][j]=True; newlive.add(op[1])
        for j,op in enumerate(L):
            if op[0]=='C':
                c,t=op[1],op[2]
                if t in live:  # target value matters -> op matters, control matters
                    useful[k][j]=True; newlive.add(c)
        live=newlive
    lastuse=[0]*9
    for k,L in enumerate(recs):
        for j,op in enumerate(L):
            if useful[k][j]:
                for w in (op[1:3] if op[0]=='C' else op[1:2]): lastuse[w]=k+1
    nuseless=sum(1 for k,L in enumerate(recs) for j,op in enumerate(L) if not useful[k][j])
    # row of each wire right after its last useful op
    return code, lastuse, nuseless, recs, useful, states
if __name__=='__main__':
    D=pickle.load(open(sys.argv[1],'rb'))
    code,lastuse,nu,recs,useful,states=analyze(D)
    print('useless ops',nu,'code wires',code)
    for w in range(9):
        k=lastuse[w]; row=states[k][0][w] if k<len(states) else None
        print(' wire',w,'last useful layer',k,'row after',row,'(code)' if w in code else '')
