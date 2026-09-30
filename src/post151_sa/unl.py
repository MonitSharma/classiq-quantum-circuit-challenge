import pickle
from kdrv import full_gates
NEG=-10**9
def unload_depths(DX,DY,seq,W):
    gx=full_gates(DX); gy=full_gates(DY)
    ops=[('cx',c,t) for c,t in reversed(seq)]
    def inv(gates,off):
        o=[]
        for g in reversed(gates):
            if g[0][0]=='cx': o.append(('cx',g[1]+off,g[2]+off))
            else: o.append(('1q',g[1]+off))
        return o
    ops+=inv(gx,0)+inv(gy,9)
    res=[]
    for w0 in W:
        t=[NEG]*18; t[w0]=0; lu=[False]*18
        for o in ops:
            if o[0]=='cx':
                c,tt=o[1],o[2]; m=max(t[c],t[tt])
                if m==NEG: continue
                t[c]=t[tt]=m+1; lu[c]=lu[tt]=False
            else:
                w=o[1]
                if t[w]==NEG: continue
                if not lu[w]: t[w]+=1; lu[w]=True
        res.append(max(t))
    return res
