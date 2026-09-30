import pickle, sys, glob, heapq
def mst_cost(D):
    masks=[m for i in range(3) for m in D['targets'][i]]
    nodes=list(dict.fromkeys(masks+[1<<i for i in range(9)]))
    n=len(nodes)
    INF=10**9; dist=[INF]*n; inT=[False]*n; dist[len(masks)]=0 if len(nodes)>len(masks) else 0
    # start from any initial row
    start=nodes.index(1<<6) if (1<<6) in nodes else 0
    dist=[INF]*n; dist[start]=0; tot=0
    pq=[(0,start)]
    while pq:
        d,u=heapq.heappop(pq)
        if inT[u]: continue
        inT[u]=True; tot+=d
        for v in range(n):
            if inT[v]: continue
            w=bin(nodes[u]^nodes[v]).count('1')
            if w<dist[v]: dist[v]=w; heapq.heappush(pq,(w,v))
    return tot,len(masks)
if __name__=='__main__':
    rows=[]
    for f in sorted(glob.glob('runs/gs_*.pkl'))+['runs/xst162.pkl','runs/yst124.pkl']:
        try: D=pickle.load(open(f,'rb'))
        except Exception: continue
        if 'targets' not in D: continue
        c,nm=mst_cost(D)
        slots=2*c+nm+6
        rows.append((slots/9.0, f.split('/')[-1], c, nm))
    for r in sorted(rows): print('%6.2f %-22s mst %3d rot %3d'%r)
