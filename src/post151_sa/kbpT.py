import pickle, subprocess, sys
from kdrv import KTERMS
fix,T,W,mu,seed=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),float(sys.argv[4]),int(sys.argv[5])
fx=pickle.load(open(fix,"rb")); seq,Wr,rdy=fx[:3]; unl=fx[3] if len(fx)>3 else rdy
inp=[str(len(KTERMS)),' '.join(map(str,KTERMS))]+[f"{r} {T-u}" for r,u in zip(rdy,unl)]
out=f"runs/kbpT{T}_W{W}_mu{mu}_s{seed}.txt"
p=subprocess.run(["./c/kbeamP8",str(W),str(max(T-2*min(rdy),1)),str(seed),str(mu),out,"3","0"],input="\n".join(inp)+"\n",capture_output=True,text=True)
L=[l for l in p.stderr.split('\n') if l.startswith('depth')]
print(T,W,mu,seed,'rc',p.returncode,L[-1] if L else '',out if p.returncode==0 else '')
