import pickle, sys
from mkD3 import dump
src=sys.argv[1]; tag=sys.argv[2]
D=pickle.load(open(src,'rb'))
D2=dict(D); D2['targets']=dict(D['targets'])
for spec in sys.argv[3:]:
    i,path=spec.split('=')
    D2['targets'][int(i)]=pickle.load(open(path,'rb'))
sz=dump(D2,tag)
print(tag,sz,'total',sum(sz.values()))
