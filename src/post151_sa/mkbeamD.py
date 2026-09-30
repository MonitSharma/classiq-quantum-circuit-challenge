import pickle, sys
from lbeval import load_beam, sa4
from sim import check_loader2
from depth import gate_depth
src,beam,out=sys.argv[1:4]
D=pickle.load(open(src,'rb')); bd,seq=load_beam(beam)
d,pen,g=sa4(D,seq)
chk=check_loader2(g,D['newcode']); assert pen==0 and chk['max_dev']<1e-9
D2=dict(D); D2['gates']=g; D2['fix']=[]; D2['depth']=gate_depth(g); D2['placed']=False
pickle.dump(D2,open(out,'wb')); print(out,'depth',D2['depth'],'dev %.1e'%chk['max_dev'])
