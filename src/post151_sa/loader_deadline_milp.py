import json,pickle
from pathlib import Path
from loader_milp_preserve import native_blocks
from kdrv import full_gates,profile
from kgen import span_map
from sim import symbolic_final,check_loader2
import smilp_caps
OUT=Path('runs/caps_0924');
paths=[('champ',Path('../../artifacts/118/recipes/x_loader_d44.pkl'))]
for name in ['q26_2','q26_6','r36_1_q2','lk34_1','lk34_2']:
    p=Path('runs/t115_0923/loaders')/(name+'.pkl')
    if p.exists():paths.append((name,p))
for name,path in paths:
    D=pickle.load(open(path,'rb'));g=full_gates(D);e,_=profile(g);rows=symbolic_final(g)
    sm=span_map(D['req']);desired={1:43,2:35,4:43,12:44}
    caps={w:desired[sm[r]] for w,r in enumerate(rows) if r in sm and sm[r] in desired}
    if len(caps)!=4:print('SKIP',name,caps,flush=True);continue
    pairs=native_blocks(g);ops=[o for o,_ in pairs];back={id(o):x for o,x in pairs}
    print('BEGIN',name,e,caps,flush=True)
    sol=smilp_caps.solve(ops,max(e),60,True,wire_caps=caps)
    rec=dict(source=str(path),caps=caps,success=sol is not None)
    if sol is not None:
        gs=[x for o in sol for x in back[id(o)]];chk=check_loader2(gs,D['newcode']);assert chk['max_dev']<1e-9
        prof,_=profile(gs);assert all(prof[w]<=v for w,v in caps.items())
        rec.update(profile=prof,max_dev=chk['max_dev']);pickle.dump(dict(D,gates=gs,fix=[]),open(OUT/(name+'_milp.pkl'),'wb'))
    (OUT/(name+'_milp.json')).write_text(json.dumps(rec,indent=2));print(rec,flush=True)
