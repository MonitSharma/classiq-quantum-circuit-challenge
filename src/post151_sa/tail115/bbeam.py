"""Bridge by beam: for pairs (P,Q) run kbeam_t3 from A*S_P to home (=A*S_Q) over the remaining terms."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)).split('/tail115')[0] + '/tail115'); from localpaths import ROOT, PS, WK, KISSAT, MARCH, CADICAL  # local paths
import sys, os, json, time, subprocess, tempfile
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from drive import read_dump, load_terms, ST, TAU0
from bridge import basis_change, apply, fired_of
KB=os.environ.get('KB',f'{WK}/kbeam_t3')
def bridge_beam(P,Q,terms,T,predone,W=4000,seed=1,tmp='/tmp',tag='b'):
    fP,_=fired_of(P,terms); fQ,_=fired_of(Q,terms); fQ=fQ-set(predone)
    if fP & fQ: return 'CLASH',None
    rem=[t for t in terms if t not in fP and t not in fQ]
    tau_a=TAU0+P['d']; end=(T+1-TAU0)-1-Q['d']; L=end-tau_a
    if L<1: return 'SHORT',None
    A=basis_change(Q['rows']); rows0=[apply(A,r) for r in P['rows']]; remA=[apply(A,t) for t in rem]
    inp=os.path.join(tmp,tag+'.in'); out=os.path.join(tmp,tag+'.out')
    open(inp,'w').write('\n'.join([str(len(remA)),' '.join(map(str,remA))]+[f'{st} {tau_a} {end}' for st in ST])+'\n')
    j=lambda v:','.join(map(str,v)); a=[tau_a]*8; e=[end]*8
    env=dict(os.environ,SINGLES_PENDING='1',TOUCHBAD='1',LAW='0.3',ZS=j(a),XS=j(a),CS=j(a),ZD=j(e),XD=j(e),CD=j(e),START=j(rows0))
    for k in ('DUMPD','PREDONE','DUMPSTOP'): env.pop(k,None)
    if os.path.exists(out): os.remove(out)
    r=subprocess.run([KB,str(W),str(L),str(seed),'0.02',out,'4','0'],stdin=open(inp),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
    best=None
    for line in r.stderr.split('\n'):
        if line.startswith('depth'):
            f=line.split(); best=(int(f[1]),int(f[6]),int(f[-1]))
    if r.returncode==0:
        return 'OK',dict(rem=len(rem),L=L,A=A,rows0=rows0,remA=remA,out=open(out).read(),tau_a=tau_a,end=end)
    return 'FAIL',dict(rem=len(rem),L=L,last=best)
if __name__=='__main__':
    T=int(sys.argv[1]); pdump=sys.argv[2]; pidx=int(sys.argv[3]); qdump=sys.argv[4]; inp=sys.argv[5]; W=int(sys.argv[6]); lim=int(sys.argv[7])
    terms=load_terms(inp); P=read_dump(pdump)[pidx]; fP,pP=fired_of(P,terms); predone=sorted(fP|pP)
    Qs=read_dump(qdump); t0=time.time(); stats={}
    for jq,Q in enumerate(Qs[:lim]):
        tag,info=bridge_beam(P,Q,terms,T,predone,W=W,tag=f'bb{os.getpid()}')
        stats[tag]=stats.get(tag,0)+1
        if tag=='OK':
            print('OK',jq,info['rem'],info['L'],flush=True)
            json.dump(dict(P=pidx,Q=jq,**{k:v for k,v in info.items()}),open(qdump+f'.bb{pidx}_{jq}.json','w'))
        elif jq<5 or jq%50==0: print(jq,tag,info and info.get('last'),info and info.get('rem'),'%.0fs'%(time.time()-t0),flush=True)
    print('stats',stats)
