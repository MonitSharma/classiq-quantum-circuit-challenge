"""pscreen.py T W out xlist ylist : FEM kernel-beam screen over loader pairs (no MILP)"""
import sys, os, time, json
os.environ.update(STRICT='1',ZOCC='1',FUSE='1')
sys.argv_saved=list(sys.argv)
import paireval as P
T=int(sys.argv[1]); W=int(sys.argv[2]); out=sys.argv[3]
X=[l.strip() for l in open(sys.argv[4]) if l.strip()]; Y=[l.strip() for l in open(sys.argv[5]) if l.strip()]
done=set()
if os.path.exists(out):
    for l in open(out):
        try: d=json.loads(l); done.add((d['x'],d['y']))
        except: pass
import io, contextlib
for y in Y:
    for x in X:
        if (x,y) in done: continue
        t0=time.time()
        try:
            DX=P.load(x,0); DY=P.load(y,1)
            with contextlib.redirect_stdout(io.StringIO()):
                r=P.run(DX,DY,T,W,['1'],f'scr{T}',milp=False)
            rec=dict(x=x,y=y,T=T,W=W,rc=r['s1']['rc'],mind=r['s1']['mind'],rdy=list(r['rdy']),srdy=list(r['srdy']),ST=list(r['ST']),t=round(time.time()-t0,1))
        except Exception as ex: rec=dict(x=x,y=y,T=T,err=str(ex)[:200])
        open(out,'a').write(json.dumps(rec)+'\n')
