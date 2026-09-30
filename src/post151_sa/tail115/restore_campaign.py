"""Restoration-aware prefix scoring under actual fused loader occupancy."""
import json,os,argparse
import paireval_local as p
from classiq_synth.core.verify import exhaustive_verify
os.environ.update(STRICT='1',ZOCC='1',FUSE='1')
p.KB=str(p.SA/'c/kbeam_restore')
parser=argparse.ArgumentParser();parser.add_argument('--family',choices=['co24','co47'],default='co47');args=parser.parse_args()
configs=([(.3,40,1),(.7,40,1),(1.5,48,2),(.7,54,2)] if args.family=='co24' else [(.08,48,1),(.15,54,2),(.3,56,3)])
for weight,start,seed in configs:
    os.environ.update(WREST=str(weight),RESTSTART=str(start))
    tag=f'{args.family}_restore_w{weight}_a{start}_s{seed}'
    r=p.run(*p.CH[:2],115,8000 if args.family=='co24' else 6000,[seed],tag,
            co_path=None if args.family=='co24' else str(p.ROOT/'artifacts/phase_network117_20260922/plateau/co_47.npy'))
    for result in r.values():
        if isinstance(result,dict):
            for key,path in list(result.items()):
                if key.startswith('T'):result[key+'_verification']=exhaustive_verify(path)
    (p.OUT/(tag+'.json')).write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
