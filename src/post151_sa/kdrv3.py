"""Kernel pipeline driven by the exact-timing sequence beam (kseq).

plan  -> kseq input -> kseq -> gate emission (mirror of sa4's lazy-rotation rules)
     -> kdrv.assemble -> depth / CX.
"""
import os, sys, pickle, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kdrv import KTERMS, CO, assemble
from kgen import plan

def kseq_input(pl, T):
    seq, W, ST, rdy, unl = pl
    lines = [str(len(KTERMS)), ' '.join(map(str, KTERMS))]
    for s, r, u in zip(ST, rdy, unl):
        lines.append(f"{s} {r} {T-u}")
    return "\n".join(lines) + "\n", len(W)

def run_kseq(pl, T, W_beam, seed, out, env=None, binary='./c/kseq', maxstep=400, timeout=3600):
    inp, N = kseq_input(pl, T)
    e = dict(os.environ)
    if env: e.update({k: str(v) for k, v in env.items()})
    p = subprocess.run([binary, str(W_beam), str(maxstep), str(seed), str(N), out],
                       input=inp, capture_output=True, text=True, env=e, timeout=timeout)
    return p.returncode, p.stderr

def emit_kg(pl, T, seqpath):
    """Replay the CX sequence with sa4's exact timing/emission rules and build the
    kernel gate list in kdrv.assemble's format."""
    fix, W, ST, rdy, unl = pl
    N = len(W)
    lines = open(seqpath).read().split()
    n = int(lines[0])
    cxs = [(int(lines[1+2*i]), int(lines[2+2*i])) for i in range(n)]
    Tset = set(KTERMS)
    rows = list(ST); pend = [None]*N; done = set()
    wt = list(rdy); lu = [False]*N
    ops = []
    def settle():
        for i in range(N):
            if pend[i] is None and rows[i] in Tset and rows[i] not in done:
                pend[i] = rows[i]; done.add(rows[i])
    settle()
    for (c, t) in cxs:
        if pend[t] is not None:
            if not lu[t]: wt[t] += 1; lu[t] = True
            ops.append(('R', t, pend[t])); pend[t] = None
        tau = max(wt[c], wt[t]) + 1
        if pend[c] is not None:
            if lu[c]:
                ops.append(('R', c, pend[c])); pend[c] = None
            elif wt[c] + 1 < tau:
                wt[c] += 1; lu[c] = True
                ops.append(('R', c, pend[c])); pend[c] = None
        wt[c] = wt[t] = tau; lu[c] = lu[t] = False
        rows[t] ^= rows[c]; ops.append(('C', c, t))
        settle()
    for i in range(N):
        if pend[i] is not None:
            if not lu[i]: wt[i] += 1; lu[i] = True
            ops.append(('R', i, pend[i])); pend[i] = None
    assert done == Tset, f"missing terms: {len(Tset-done)}"
    assert rows == list(ST), "frame not restored"
    kg = [('S', list(range(18)))] + [('C', c, t) for c, t in fix]
    for o in ops:
        if o[0] == 'C': kg.append(('C', W[o[1]], W[o[2]]))
        else: kg.append(('R', W[o[1]], 2*CO[o[2]]))
    kg += [('C', c, t) for c, t in reversed(fix)]
    return kg, max(wt), len(cxs)

if __name__ == '__main__':
    DX = pickle.load(open(sys.argv[1], 'rb')); DY = pickle.load(open(sys.argv[2], 'rb'))
    T = int(sys.argv[3]); Wb = int(sys.argv[4]); seed = int(sys.argv[5]); tag = sys.argv[6]
    pl = plan(DX, DY)
    print('plan W', pl[1], 'rdy', pl[3], 'unl', pl[4], flush=True)
    out = f'runs/kseq_{tag}.txt'
    env = {k: os.environ[k] for k in
           ('WDONE','WREACH','WREACH2','WSLACK','WRET','WBAL','MAXSKEW','PERMSET','RCAP1','RCAP2')
           if k in os.environ}
    rc, err = run_kseq(pl, T, Wb, seed, out, env=env)
    print('kseq rc', rc, err.strip().split('\n')[-1], flush=True)
    if rc != 0: sys.exit(1)
    kg, mx, ncx = emit_kg(pl, T, out)
    d, cx = assemble(DX, DY, kg, f'runs/cand_{tag}.qasm')
    print(f'ASSEMBLED depth {d} cx {cx}  (kernel ncx {ncx}, model end {mx})', flush=True)
    pickle.dump((pl, kg), open(f'runs/plan_and_gates_{tag}.pkl', 'wb'))
