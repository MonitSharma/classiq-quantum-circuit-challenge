"""Verify every clean-ancilla computational-basis input via sparse batched simulation."""
from pathlib import Path
import sys,json,hashlib,time
import numpy as np
from qiskit import qasm2
from search import logo

def exhaustive(path, max_width=18):
 source=Path(path).read_text();q=qasm2.loads(source)
 # Width overrides are explicitly for oversized diagnostic circuits. Default
 # submission verification retains the challenge's strict 18-wire limit.
 assert 12<=q.num_qubits<=max_width<=30 and set(q.count_ops())<={'u3','cx'}
 n=4096;indices=np.arange(n,dtype=np.int32)[:,None];amp=np.ones((n,1),complex)
 dropped=np.zeros(n);peak=1;start=time.time();tol=2e-15
 def compress(idx,a):
  order=np.argsort(idx,axis=1);idx=np.take_along_axis(idx,order,1);a=np.take_along_axis(a,order,1)
  first=np.ones(idx.shape,bool);first[:,1:]=idx[:,1:]!=idx[:,:-1]
  group=np.cumsum(first,axis=1)-1;w=int(group[:,-1].max())+1
  target=(np.arange(n)[:,None]*w+group).ravel()
  sums=(np.bincount(target,weights=a.real.ravel(),minlength=n*w)+1j*np.bincount(target,weights=a.imag.ravel(),minlength=n*w)).reshape(n,w)
  outidx=np.zeros((n,w),np.int32);rr=np.broadcast_to(np.arange(n)[:,None],idx.shape)[first];cc=group[first];outidx[rr,cc]=idx[first]
  keep=np.abs(sums)>tol
  lost=np.sum(np.abs(sums)*~keep,axis=1)
  count=keep.sum(1);width=int(count.max());dest=np.cumsum(keep,axis=1)-1
  rr=np.broadcast_to(np.arange(n)[:,None],sums.shape)[keep];cc=dest[keep]
  oo=np.zeros((n,width),np.int32);aa=np.zeros((n,width),complex);oo[rr,cc]=outidx[keep];aa[rr,cc]=sums[keep]
  return oo,aa,lost
 for step,inst in enumerate(q.data):
  vs=[q.find_bit(v).index for v in inst.qubits]
  if inst.operation.name=='cx':
   indices ^= (((indices>>vs[0])&1)<<vs[1])
  else:
   theta,phi,lam=map(float,inst.operation.params);c=np.cos(theta/2);s=np.sin(theta/2);bit=(indices>>vs[0])&1
   if abs(s)<tol:
    amp*=np.where(bit,np.exp(1j*(phi+lam))*c,c)
    dropped+=abs(s)*np.sqrt(np.sum(np.abs(amp)**2,axis=1))
   elif abs(c)<tol:
    amp*=np.where(bit,-np.exp(1j*lam)*s,np.exp(1j*phi)*s);indices^=1<<vs[0]
    dropped+=abs(c)*np.sqrt(np.sum(np.abs(amp)**2,axis=1))
   else:
    aa=amp*np.where(bit,np.exp(1j*(phi+lam))*c,c)
    bb=amp*np.where(bit,-np.exp(1j*lam)*s,np.exp(1j*phi)*s)
    indices,amp,lost=compress(np.concatenate([indices,indices^(1<<vs[0])],axis=1),np.concatenate([aa,bb],axis=1))
    dropped+=lost
    peak=max(peak,amp.shape[1])
    if peak>2048:raise RuntimeError('Sparse support too large; use blocked dense verifier')
  if step%250==0:print('gate',step,'/',len(q.data),'support',amp.shape[1],flush=True)
 expected=np.array([-1 if logo(x,y) else 1 for y in range(64) for x in range(64)])
 same=indices==np.arange(n)[:,None]
 diagonal=np.sum(amp*same,axis=1);phase=diagonal[0]/expected[0];phase/=abs(phase)
 residual=np.abs(amp*~same);err=max(float(np.max(np.abs(diagonal-phase*expected))),float(np.max(residual,initial=0)))
 leak=float(np.max(np.abs(amp)*(indices>=4096),initial=0));bound=float(dropped.max())
 assert err+bound<1e-10,(err,bound)
 report=dict(qasm=str(Path(path).resolve()),sha256=hashlib.sha256(source.encode()).hexdigest(),basis_inputs_checked=n,width=q.num_qubits,depth=q.depth(),cx_count=q.count_ops().get('cx',0),max_error=err,ancilla_error=leak,discarded_amplitude_bound=bound,peak_sparse_support=peak,elapsed_seconds=time.time()-start,verification='Exhaustive numerical verification of all 4096 clean-ancilla basis inputs, with one shared global phase; by linearity covers arbitrary superpositions')
 report['challenge_width_eligible']=q.num_qubits<=18
 if max_width>18:report['diagnostic_width_limit']=max_width
 Path(path).with_suffix('.exhaustive.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':exhaustive(sys.argv[1])
