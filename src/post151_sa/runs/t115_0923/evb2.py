import pickle, sys, os
os.environ.setdefault('CLASS_CODES',os.path.expanduser('~/mnt/classiq/artifacts/185/class_codes.json'))
os.environ.setdefault('CLASSIQ_ROOT',os.path.expanduser('~/mnt/classiq'))
sys.path.insert(0,'.')
from lbeval2 import load_beam, sa4
from sim import check_loader2, symbolic_final
NV=9
def lay(g):
    wt=[0]*NV; lu=[False]*NV; lt=[0]*NV; lc=[0]*NV; hz=[0]*NV; last=[0]*NV
    for x in g:
        if x[0][0]=='cx':
            c,t=x[1],x[2]; l=max(wt[c],wt[t])+1; wt[c]=wt[t]=l; lu[c]=lu[t]=False; lt[t]=l; lc[c]=l
        else:
            w=x[1]
            if not lu[w]: wt[w]+=1; lu[w]=True
            if x[0][0]=='h': hz[w]=wt[w]
    return wt,lt,lc,hz
def ev(side,path,tag):
    D=pickle.load(open(f'../s118{side}.pkl','rb'))
    bd,seq=load_beam(path)
    d,pen,g=sa4(D,seq,tag=tag,binary='../sa4')
    if pen!=0 or check_loader2(g,D['newcode'])['max_dev']>1e-9: return None
    rows=symbolic_final(g); wt,lt,lc,hz=lay(g)
    out=[]
    for v in D['req']:
        w=[i for i in range(NV) if rows[i] in (v,256 if v==384 else v)][0]
        out.append((v,w,wt[w],lt[w],lc[w],hz[w]))
    return max(wt),out,g,D
if __name__=='__main__':
    side=sys.argv[1]
    for p in sys.argv[2:]:
        try:
            r=ev(side,p,os.path.basename(p))
            if r is None: print(p,'BAD'); continue
            print(os.path.basename(p),'depth',r[0],' (row,wire,lastuse,lasttgt,lastctl,H):',r[1],flush=True)
            pickle.dump(dict(r[3],gates=r[2],fix=[],depth=r[0]),open(p+'.pkl','wb'))
        except Exception as ex: print(p,'ERR',ex)
