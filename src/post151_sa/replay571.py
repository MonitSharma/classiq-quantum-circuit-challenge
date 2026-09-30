"""Rebuild the verified 116-depth, 571-CX variant without running a search."""
import argparse
import os
import pickle
import tempfile
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
os.environ.setdefault('CLASSIQ_ROOT',str(ROOT))
import ev116
from kdrv import assemble
from canc import simplify
from postopt import depth, fuse, parse_ops, write

def replay(output):
    recipes=ROOT/'artifacts/116/recipes/cx571'
    dx,dy,pl=pickle.load(open(recipes/'loaders_plan.pkl','rb'))
    ev116.CO=np.load(recipes/'kernel_co.npy')
    ev116.KTERMS=list(map(int,np.flatnonzero(abs(ev116.CO)>1e-10)))
    kg=ev116.build_kg_s(pl,recipes/'kernel_schedule.txt',
                       [26,37,42,43,28,40,42,44],116)
    with tempfile.TemporaryDirectory(prefix='classiq-replay571-') as tmp:
        q=Path(tmp)/'assembled.qasm'
        assemble(dx,dy,kg,str(q))
        ops=fuse(simplify(fuse(parse_ops(q)),verbose=False))
    assert depth(ops)==116
    assert sum(op[0]=='cx' for op in ops)==571
    write(ops,output)
    return dict(depth=116,cx_count=571,width=18,output=str(output))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path)
    print(replay(parser.parse_args().output))
