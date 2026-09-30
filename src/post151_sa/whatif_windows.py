import sys,pickle,numpy as np,os
R=os.path.expanduser('~/mnt/classiq')
DX,DY,pl=pickle.load(open(R+'/src/post151_sa/sat116/champ117.pkl','rb')); seq,W,ST,rdy,unl=pl
co=np.load(sys.argv[1] if sys.argv[1]!='champ' else R+'/artifacts/116/recipes/kernel_co.npy'); T=int(sys.argv[2]); r=list(map(int,sys.argv[3].split(','))); out=sys.argv[4]
terms=list(map(int,np.flatnonzero(abs(co)>1e-10)))
lines=[str(len(terms)),' '.join(map(str,terms))]+[f'{st} {a} {T-a}' for st,a in zip(ST,r)]
open(out,'w').write('\n'.join(lines)+'\n')
