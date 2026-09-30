import json,time,sys
from pathlib import Path
from postopt import parse_ops,fuse,write,depth
from smilp import solve
p=Path(sys.argv[1]);r=json.loads((p/'report.json').read_text());start=time.monotonic(); rows=[]
for v in sorted(r['retained'],key=lambda a:a['score']):
 ops=fuse(parse_ops(v['path']));s=time.monotonic();o=solve(ops,116,tlim=15,verbose=False)
 row=dict(index=v['index'],seconds=time.monotonic()-s,found=o is not None)
 if o is not None:
  out=p/f"exact_{v['index']}_d116.qasm";write(fuse(o),out);row['qasm']=str(out)
 rows.append(row);print(row,flush=True)
(p/'exact_report.json').write_text(json.dumps(rows,indent=2))
print('DONE',time.monotonic()-start,flush=True)
