"""Bounded exact shared-XAG screen for the four structured side outputs."""
import argparse, json, time
from pathlib import Path
import z3
from post190_structured_audit import Y_LABEL,X_LABEL,ROWCLS,COLCLS,table

FULL=(1<<64)-1
def targets(side):
 labels,classes=(Y_LABEL,ROWCLS) if side=='y' else (X_LABEL,COLCLS)
 return tuple(table([(labels[c]>>b)&1 for c in classes]) for b in range(4))
def affine(sel,sources):
 out=z3.BitVecVal(0,64)
 for b,v in zip(sel,sources): out ^= z3.If(b,z3.BitVecVal(v,64) if isinstance(v,int) else v,z3.BitVecVal(0,64))
 return out
def solve(side,pattern,seconds=20):
 start=time.monotonic(); s=z3.Solver();s.set(timeout=int(seconds*1000)); basis=(FULL,)+tuple(table([(t>>i)&1 for t in range(64)]) for i in range(6)); gates=[];products=[]
 for si,w in enumerate(pattern):
  src=basis+tuple(products); layer=[]
  for gi in range(w):
   a=[z3.Bool(f'{side}_{pattern}_{si}_{gi}_a{i}') for i in range(len(src))]; b=[z3.Bool(f'{side}_{pattern}_{si}_{gi}_b{i}') for i in range(len(src))]
   av,bv=affine(a,src),affine(b,src); p=av&bv; s.add(av!=0,bv!=0,av!=z3.BitVecVal(FULL,64),bv!=z3.BitVecVal(FULL,64)); layer.append((a,b,av,bv,p)); products.append(p)
  gates.append(layer)
 final=basis+tuple(products); outs=[]
 for oi,g in enumerate(targets(side)):
  bits=[z3.Bool(f'{side}_{pattern}_out{oi}_{i}') for i in range(len(final))]; s.add(affine(bits,final)==z3.BitVecVal(g,64)); outs.append(bits)
 st=s.check(); r={'side':side,'pattern':list(pattern),'and_count':sum(pattern),'status':str(st).upper(),'seconds':time.monotonic()-start}
 if st==z3.sat:
  m=s.model(); gm=[]
  for layer in gates: gm.append([{'a_mask':sum(1<<i for i,b in enumerate(g[0]) if z3.is_true(m.eval(b,model_completion=True))),'b_mask':sum(1<<i for i,b in enumerate(g[1]) if z3.is_true(m.eval(b,model_completion=True)))} for g in layer])
  om=[sum(1<<i for i,b in enumerate(bits) if z3.is_true(m.eval(b,model_completion=True))) for bits in outs]; r.update(gates=gm,output_masks=om)
 return r
def run(out,seconds=20):
 out.mkdir(parents=True,exist_ok=True); rows=[]
 for side in ('y','x'):
  for pat in ((1,3,3),(2,2,3),(2,3,2),(3,1,3),(3,2,2),(3,3,1)):
   row=solve(side,pat,seconds); rows.append(row); print(row,flush=True)
 (out/'report.json').write_text(json.dumps(rows,indent=2)); return rows
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,default=Path('artifacts/post190_structured_shared_xag'));p.add_argument('--seconds',type=float,default=20);run(p.parse_args().outdir,p.parse_args().seconds)
