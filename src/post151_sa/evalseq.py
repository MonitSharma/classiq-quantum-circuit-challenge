"""Turn a CX sequence from lseq into a loader recipe and report what the kernel sees:
depth, per-code-direction ready times, and the resulting lower bound on total depth."""
import pickle, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lbeval import sa4
from sim import check_loader2, symbolic_final
from depth import gate_depth
from kdrv import profile, full_gates

def load_seq(path):
    L = open(path).read().split()
    n = int(L[1])
    return [(int(L[2 + 2 * i]), int(L[3 + 2 * i])) for i in range(n)]

def build(Dsrc, seqpath, outpath=None, seed=1):
    D = pickle.load(open(Dsrc, 'rb'))
    seq = load_seq(seqpath)
    d, pen, g = sa4(D, seq, seed=seed)
    chk = check_loader2(g, D['newcode'])
    if pen != 0 or chk['max_dev'] > 1e-9: return None
    D2 = dict(D); D2['gates'] = g; D2['fix'] = []; D2['depth'] = gate_depth(g); D2['placed'] = False
    if outpath: pickle.dump(D2, open(outpath, 'wb'))
    return D2, chk['max_dev']

def readout(D):
    g = full_gates(D); e, _ = profile(g); rows = symbolic_final(g)
    span = {}
    for b in range(1, 16):
        v = 0
        for k in range(4):
            if b >> k & 1: v ^= D['req'][k]
        span[v] = b
    ins = sorted((e[w], span[rows[w]]) for w in range(9) if rows[w] in span)[:4]
    ncx = sum(1 for x in g if x[0][0] == 'cx')
    return dict(depth=max(e), ncx=ncx, ready=[t for t, _ in ins], coords=[b for _, b in ins],
                sum=sum(t for t, _ in ins))
