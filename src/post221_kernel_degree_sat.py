"""Joint class labels and bounded-degree kernel, with exact reachable constraints."""
import argparse,json,time
from functools import reduce
from pathlib import Path
import z3
from post258_raw_parity_codes import cells
from post258_two_stage_anf import decode,encode
import two_stage_oracle as ts

def run(degree,fixed,timeout):
 out=Path(f'artifacts/post221_kernel_degree{degree}_{fixed}_v1');assert not out.exists();out.mkdir();base=json.loads(Path('artifacts/221/class_codes.json').read_text());yc,xc=cells(ts.ROWCLS,32),cells(ts.COLCLS,48);s=z3.Solver();s.set(timeout=timeout);labs=[]
 for side,cc in [('y',yc),('x',xc)]:
  lab={k:z3.BitVec(f'{side}_{i}',3) for i,k in enumerate(cc)};labs.append(lab)
  for bit in [0,1]:
   keys=[k for k in cc if k[0]==bit];s.add(z3.Distinct(*[lab[k] for k in keys]))
  if fixed==side:
   known=decode(base[f'{side}lab']);s.add([lab[k]==known[k] for k in cc])
  else:
   # Conditional XOR by raw bit is affine, preserving kernel degree.
   for bit in [0,1]:s.add(lab[next(k for k in cc if k[0]==bit)]==0)
 pairs=[(y,x) for y in yc for x in xc];n=len(pairs);zero=z3.BitVecVal(0,n)
 wires=[]
 for side in [0,1]:
  wires.append(z3.BitVecVal(sum(k[side][0]<<i for i,k in enumerate(pairs)),n))
  for bit in range(3):
   parts=[]
   for key,value in labs[side].items():
    mask=sum(1<<i for i,pair in enumerate(pairs) if pair[side]==key);parts.append(z3.If(z3.Extract(bit,bit,value)==1,z3.BitVecVal(mask,n),zero))
   wires.append(reduce(lambda a,b:a|b,parts))
 terms=[m for m in range(256) if m.bit_count()<=degree];coeff=[z3.Bool(f'coef{m}') for m in terms];expr=zero
 for m,on in zip(terms,coeff):
  product=reduce(lambda a,b:a&b,[wires[b] for b in range(8) if m>>b&1],z3.BitVecVal((1<<n)-1,n));expr=expr^z3.If(on,product,zero)
 want=sum(int(ts.logo(xc[x][0],yc[y][0]))<<i for i,(y,x) in enumerate(pairs));s.add(expr==z3.BitVecVal(want,n))
 start=time.monotonic();status=s.check();row=dict(degree=degree,fixed=fixed,status=str(status),seconds=time.monotonic()-start);print(row,flush=True)
 if status==z3.sat:
  model=s.model();labels=[{k:model.eval(v).as_long() for k,v in lab.items()} for lab in labs];selected=[m for m,c in zip(terms,coeff) if z3.is_true(model.eval(c,model_completion=True))]
  for y,x in pairs:
   w=y[0]|labels[0][y]<<1|x[0]<<4|labels[1][x]<<5;assert sum(m&~w==0 for m in selected)%2==ts.logo(xc[x][0],yc[y][0])
  row.update(ymask=32,xmask=48,ylab=encode(labels[0]),xlab=encode(labels[1]),terms=selected)
 (out/'report.json').write_text(json.dumps(row,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--degree',type=int,default=3);p.add_argument('--fixed',choices=['x','y','none'],default='none');p.add_argument('--timeout-ms',type=int,default=55000);a=p.parse_args();run(a.degree,a.fixed,a.timeout_ms)
