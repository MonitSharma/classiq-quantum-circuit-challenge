"""Build a two-stage oracle from arbitrary labels using the 196 pipeline
(beam-scheduled integer-lifted kernel + relative-phase encoders)."""
import sys, json, math, hashlib, itertools
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, qasm2
import two_stage_oracle as ts
from depth_parity_network import walsh
from distributed_frame_search import native
from post218_beam_phase import psynth
from post224_relative_lookup import relative
from post258_two_stage_anf import decode
from post185_qcorr_oracle import kernel_terms

KW = [11, 12, 13, 14, 4, 15, 16, 17]

def code_of(side, lab):
    mask, cls = (32, ts.ROWCLS) if side == 'y' else (48, ts.COLCLS)
    return [lab[((v & mask).bit_count() % 2, c)] for v, c in enumerate(cls)], mask, cls

def kernel_from_terms(terms, beams):
    lifted = np.array([sum(int(m & ~w == 0) for m in terms) for w in range(256)], float)
    phases = math.pi * lifted
    co = walsh(phases)
    targets = {m: float(co[m]) for m in range(1, 256) if abs(co[m]) > 1e-12}
    best = None
    for b in beams:
        k = native(psynth(8, targets, global_phase=float(co[0]), **b))
        if best is None or (k.depth(), k.size()) < (best[0].depth(), best[0].size()):
            best = (k, b)
    return best[0], phases, best[1]

def encoder(side, lab, seed):
    code, mask, cls = code_of(side, lab)
    tab = np.array([[math.pi * (c >> b & 1) for c in code] for b in range(3)])
    e, _ = relative(tab, seed)
    if side == 'x':
        e.cx(5, 4)
    return e

def build(yl, xl, terms, outdir, yseeds=range(12), xseeds=range(12), beams=None, pairs=6):
    beams = beams or [dict(seed=s, beam=64, branch=14, alpha=5.0, timew=0.35) for s in (209, 1, 2)]
    kern, phases, bb = kernel_from_terms(terms, beams)
    ys = sorted(yseeds, key=lambda s: encoder('y', yl, s).depth())[:pairs]
    xs = sorted(xseeds, key=lambda s: encoder('x', xl, s).depth())[:pairs]
    best = None
    for sy, sx in itertools.product(ys, xs):
        enc = QuantumCircuit(18)
        enc.compose(encoder('y', yl, sy), ts.YW + ts.YA, inplace=True)
        enc.compose(encoder('x', xl, sx), ts.XW + ts.XA, inplace=True)
        q = native(enc.compose(kern, KW).compose(enc.inverse()))
        if best is None or (q.depth(), q.count_ops().get('cx', 0)) < best[:2]:
            best = (q.depth(), q.count_ops().get('cx', 0), q, sy, sx)
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    text = qasm2.dumps(best[2]); path = outdir / f'oracle_d{best[0]}.qasm'
    path.write_text(text)
    json.dump(dict(depth=best[0], cx=best[1], kernel_depth=kern.depth(), yseed=best[3], xseed=best[4],
                   beam=bb, terms=terms, sha256=hashlib.sha256(text.encode()).hexdigest()),
              open(outdir / 'manifest.json', 'w'), indent=2)
    print('built depth', best[0], 'cx', best[1], 'kernel', kern.depth(), flush=True)
    return path

if __name__ == '__main__':
    rec = json.load(open(sys.argv[1])); out = sys.argv[2]
    yl, xl = decode(rec['ylab']), decode(rec['xlab'])
    terms = rec['terms']
    p = build(yl, xl, terms, out)
    from exhaustive_verify import exhaustive
    exhaustive(p)
