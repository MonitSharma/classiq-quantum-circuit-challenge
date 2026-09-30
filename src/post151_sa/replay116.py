"""Rebuild depth 116 from its saved loaders, phase coefficients and CX schedule."""
import argparse
import json
import os
import pickle
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault('CLASSIQ_ROOT', str(ROOT))
import ev116
from canc import simplify
from kdrv import assemble
from postopt import depth, fuse, parse_ops, write


def replay(output):
    recipes = ROOT / 'artifacts/116/recipes'
    with (recipes / 'loaders_plan.pkl').open('rb') as handle:
        dx, dy, plan = pickle.load(handle)
    ev116.CO = np.load(recipes / 'kernel_co.npy')
    ev116.KTERMS = list(map(int, np.flatnonzero(abs(ev116.CO) > 1e-10)))
    kernel = ev116.build_kg_s(plan, recipes / 'kernel_schedule.txt',
                            [26, 37, 42, 43, 28, 40, 42, 44], 116)
    with tempfile.TemporaryDirectory(prefix='classiq-replay116-') as tmp:
        intermediate = Path(tmp) / 'assembled.qasm'
        assemble(dx, dy, kernel, str(intermediate))
        ops = fuse(simplify(fuse(parse_ops(intermediate)), verbose=False))
    assert depth(ops) == 116
    assert sum(op[0] == 'cx' for op in ops) == 573
    write(ops, output)
    return {'depth': depth(ops), 'cx_count': 573, 'width': 18,
            'output': str(output)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(json.dumps(replay(args.output)))
