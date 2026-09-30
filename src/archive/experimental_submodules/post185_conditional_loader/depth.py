def gate_depth(gates,n=9):
    wt=[0]*n; lastu=[False]*n
    for g in gates:
        if g[0][0]=='cx':
            c,t=g[1],g[2]; tm=max(wt[c],wt[t])+1; wt[c]=wt[t]=tm; lastu[c]=lastu[t]=False
        else:
            w=g[1]
            if not lastu[w]: wt[w]+=1; lastu[w]=True
    return max(wt)
