import sys, os, pickle, json
os.environ.update(STRICT='1',ZOCC='1',FUSE='1')
import paireval as P
X=[l.strip() for l in open(sys.argv[1]) if l.strip()]; Y=[l.strip() for l in open(sys.argv[2]) if l.strip()]
DY0=P.load(Y[0],1); DX0=P.load(X[0],0)
def ncx(D): return sum(1 for g in D['gates'] if g[0][0]=='cx')+len(D.get('fix',[]))
for x in X:
    DX=P.load(x,0); pl,srdy=P.windows(DX,DY0); hz=P.hz_times(DX,DY0,pl[1])
    print('X',os.path.basename(x),'rdy',pl[3][4:],'srdy',srdy[4:],'hz',hz[4:],'ST',pl[2][4:],'cx',ncx(DX))
for y in Y:
    DY=P.load(y,1); pl,srdy=P.windows(DX0,DY); hz=P.hz_times(DX0,DY,pl[1])
    print('Y',os.path.basename(y),'rdy',pl[3][:4],'srdy',srdy[:4],'hz',hz[:4],'ST',pl[2][:4],'cx',ncx(DY))
