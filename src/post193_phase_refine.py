"""Warm-start sparse phase search around the new 63-term reachable-state lift."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from post258_two_stage_anf import decode
p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--restarts',type=int,default=48);a=p.parse_args();out=a.outdir;assert not out.exists();out.mkdir(parents=True)
r=json.loads(Path('artifacts/193/kernel_recipe.json').read_text());base=np.array(r['co']);c=r['class_codes'];y,x=decode(c['ylab']),decode(c['xlab'])
care=sorted({a[0]|b<<1|(d[0]|e<<1)<<4 for a,b in y.items() for d,e in x.items()})
H=np.array([[(-1)**((w&m).bit_count()%2) for m in range(256)] for w in care],float);matrix=np.c_[H,-H];target=H@base;rng=np.random.default_rng(193914);best=63;rows=[]
for restart in range(a.restarts):
 co=base.copy();weights=np.exp(rng.normal(0,[.6,1.,1.5,2.][restart%4],256))/(abs(co)+[.015,.03,.06][restart//4%3])
 for step in range(6):
  weights[0]=0
  sol=linprog(np.r_[weights,weights],A_eq=matrix,b_eq=target,bounds=(0,None),method='highs');assert sol.success
  co=sol.x[:256]-sol.x[256:];co[abs(co)<1e-9]=0;err=float(np.max(abs(H@co-target)));assert err<1e-8
  count=int(np.count_nonzero(co[1:]));weights=np.exp(rng.normal(0,.3,256))/(abs(co)+.02)
  if count<best:
   best=count;recipe=dict(r,co=co.tolist());recipe.pop('sha256',None);f=out/f'phase_{count}.json';f.write_text(json.dumps(recipe,indent=2));print('SUPPORT',count,'restart',restart,'step',step,'error',err,flush=True)
 rows.append(dict(restart=restart,support=count,error=err))
 if restart%8==0:print('restart',restart,'best',best,flush=True)
 (out/'report.json').write_text(json.dumps(dict(best_support=best,restarts_completed=restart+1,rows=rows),indent=2))
