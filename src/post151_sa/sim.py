import numpy as np
Hm=np.array([[1,1],[1,-1]])/np.sqrt(2)
def apply1(psi,n,w,U):
    psi=psi.reshape([2]*n)
    psi=np.moveaxis(psi,w,0)
    psi=np.tensordot(U,psi,axes=([1],[0]))
    psi=np.moveaxis(psi,0,w)
    return psi.reshape(-1)
def applycx(psi,n,c,t):
    psi=psi.reshape([2]*n).copy()
    idx=[slice(None)]*n; idx[c]=1
    sub=psi[tuple(idx)]
    # t axis index shifts if t>c
    tt=t if t<c else t-1
    sub=np.flip(sub,axis=tt)
    psi[tuple(idx)]=sub
    return psi.reshape(-1)
def run(gates,n,psi):
    for g in gates:
        if g[0][0]=='cx': psi=applycx(psi,n,g[1],g[2])
        elif g[0][0]=='h': psi=apply1(psi,n,g[1],Hm)
        elif g[0][0]=='rz': psi=apply1(psi,n,g[1],np.diag([1,np.exp(1j*g[0][1])]))
    return psi
def basis_index(bits):  # bits list per wire (wire0 = axis0 = most significant in reshape)
    idx=0
    for b in bits: idx=idx*2+b
    return idx
def label_wires(gates):
    lw={}
    rows=[1<<w for w in range(9)]
    for k,g in enumerate(gates):
        if g[0][0]=='cx': rows[g[2]]^=rows[g[1]]
        if g[0][0]=='h' and k>2:
            w=g[1]; tb=[i for i in range(3) if rows[w]>>(6+i)&1 and i not in lw]
            assert len(tb)==1, (k,bin(rows[w]),lw)
            lw[tb[0]]=w; rows[w]=1<<(6+tb[0])
    return lw
def check_loader(gates, code):
    """verify: for each z, output is a basis state with targets = L(z) (wires 6,7,8 = bits 0,1,2),
    z-wires hold an injective function; returns max deviation and the z-wire map"""
    n=9; worst=0; zmap={}
    global LW
    LW=label_wires(gates)
    for z in range(64):
        bits=[(z>>w)&1 for w in range(6)]+[0,0,0]
        psi=np.zeros(2**n,complex); psi[basis_index(bits)]=1
        out=run(gates,n,psi)
        k=int(np.argmax(np.abs(out)))
        dev=1-abs(out[k])
        worst=max(worst,dev)
        ob=[(k>>(n-1-w))&1 for w in range(n)]
        lw=LW
        L=ob[lw[0]]|(ob[lw[1]]<<1)|(ob[lw[2]]<<2)
        if L!=code[z]: return ('label mismatch', z, L, code[z])
        zmap[z]=tuple(ob[w] for w in range(9) if w not in LW.values())
    inj=len(set(zmap.values()))==64
    return dict(max_dev=worst, injective=inj, label_wires=LW)

def symbolic_final(gates):
    has_open=any(len(g[0])>1 and g[0][1]=='open' for g in gates if g[0][0]=='h')
    if has_open:
        rows=[(1<<w) if w<6 else 0 for w in range(9)]; closed=set(); opened=set(); s0={}
        for g in gates:
            if g[0][0]=='cx': rows[g[2]]^=rows[g[1]]
            elif g[0][0]=='h':
                w=g[1]
                if len(g[0])>1 and g[0][1]=='open':
                    i=g[0][2]
                    if len(g[0])>3: s0[i]=rows[w]^g[0][3]     # in-place open (tail115/suffix_sat/ipload.py): row -> TB, s0 kept
                    else: assert rows[w]==0
                    rows[w]=1<<(6+i); opened.add(i)
                else:
                    tb=[i for i in range(3) if rows[w]>>(6+i)&1 and i in opened and i not in closed]
                    assert len(tb)==1, (hex(rows[w]),opened,closed)
                    closed.add(tb[0]); rows[w]=(1<<(6+tb[0]))^s0.get(tb[0],0)
        return rows
    rows=[1<<w for w in range(9)]; closed=set()
    for k,g in enumerate(gates):
        if g[0][0]=='cx': rows[g[2]]^=rows[g[1]]
        if g[0][0]=='h' and k>2:
            w=g[1]; tb=[i for i in range(3) if rows[w]>>(6+i)&1 and i not in closed]
            assert len(tb)==1
            closed.add(tb[0]); rows[w]=1<<(6+tb[0])
    return rows
def check_loader2(gates, code):
    rows=symbolic_final(gates)
    n=9; worst=0
    for z in range(64):
        v=z | (code[z]<<6)
        exp_bits=[bin(rows[w]&v).count('1')%2 for w in range(9)]
        bits=[(z>>w)&1 for w in range(6)]+[0,0,0]
        psi=np.zeros(2**n,complex); psi[basis_index(bits)]=1
        out=run(gates,n,psi)
        k=basis_index(exp_bits)
        worst=max(worst,1-abs(out[k]))
    return dict(max_dev=worst, final_rows=[bin(r) for r in rows])
