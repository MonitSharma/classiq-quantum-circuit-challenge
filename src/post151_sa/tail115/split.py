import sys
sys.path.insert(0,'/work/k/tail')
from drive import *
T=int(sys.argv[1]); dump=sys.argv[2]; inp=sys.argv[3]; tmo=int(sys.argv[4]); part=int(sys.argv[5]); nparts=int(sys.argv[6])
DDL=[T-r for r in RDY]; terms=load_terms(inp); sts=read_dump(dump)
order=sorted(range(len(sts)),key=lambda j: len(remaining_terms(sts[j],terms)))
for j in order[part::nparts]:
    st=sts[j]; rem=remaining_terms(st,terms); t0=time.time()
    res=solve_tail(st['rows'],rem,TAU0+st['d'],ST,RDY,SRDY,DDL,None,timeout=tmo)
    tag='SAT' if res else ('UNSAT' if res is False else 'TIMEOUT')
    print(j,'d',st['d'],'rem',len(rem),tag,'%.1fs'%(time.time()-t0),flush=True)
    if res:
        json.dump(dict(state=j,d=st['d'],moves=st['moves'],tail=res,T=T),open(dump+'.sol%d.json'%j,'w'))
