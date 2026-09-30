"""pairhelp.py X.pkl Y.pkl T W seeds helpers tag [co.npy]
FEM kernel beam with extra helper wires (garbage wires joining the kernel as scratch registers).
Helpers carry a private variable bit (1<<(8+k)); they may never be rotated with that bit and must be restored."""
import sys, os, json, subprocess, numpy as np
os.environ.update(STRICT='1', ZOCC='1', FUSE='1')
sys.path.insert(0, '/work/k'); import paireval as P
import kgen, ev116, kdrv, smilp
from postopt import parse_ops, fuse, write
from canc import simplify

def build_kg(pl, out, svec, T, co, terms):
    seq, W, ST, rdy, unl = pl; n = len(W)
    L = open(out).read().split('\n'); d, tau0 = map(int, L[0].split())
    Tset = set(terms); rows = list(ST); done = set(); pend = {}; body = []
    for i in range(n):
        if rows[i] in Tset and rows[i] not in done: done.add(rows[i]); pend[i] = rows[i]
    for k in range(1, d + 1):
        t = list(map(int, L[k].split())); layer = [(t[1 + 2 * q], t[2 + 2 * q]) for q in range(t[0])]
        tau = tau0 + k; used = {x for p in layer for x in p}
        for i in list(pend):
            if i not in used and tau > svec[i] and tau <= T - unl[i]:
                body.append(('R', W[i], 2 * co[pend.pop(i)]))
        for c, tt in layer:
            assert tt not in pend
            body.append(('C', W[c], W[tt]))
        for tt, v in [(tt, rows[tt] ^ rows[c]) for c, tt in layer]:
            rows[tt] = v
            if v in Tset and v not in done: done.add(v); pend[tt] = v
    for i, v in pend.items(): body.append(('R', W[i], 2 * co[v]))
    assert done == Tset, (len(done), len(Tset))
    sigma = list(range(18)); used = set()
    for i in range(n):
        cand = [j for j in range(n) if rows[j] == ST[i] and j not in used]
        assert cand, ('not restored', i)
        sigma[W[i]] = W[cand[0]]; used.add(cand[0])
    return [('S', sigma)] + body

def run(DX, DY, T, Wb, seeds, h, tag, co_path='/work/classiq/artifacts/116/recipes/kernel_co.npy'):
    co = np.load(co_path); terms = [int(m) for m in np.flatnonzero(abs(co) > 1e-10) if m]
    kdrv.CO = co; kgen.CO = co; kgen.KTERMS = terms; kdrv.KTERMS = terms; ev116.CO = co; ev116.KTERMS = terms
    pl0, srdy8 = P.windows(DX, DY)
    pl = kgen.plan(DX, DY, helpers=h); seq, W, ST, rdy, unl = pl
    assert not seq and list(W[:8]) == list(pl0[1]) and list(rdy[:8]) == list(pl0[3])
    n = len(W)
    hz = P.hz_times(DX, DY, W[:8]); occ = P.occupancy(DX, DY, W[:8])
    zs = [(hh - 1 if hh > 0 else a) for a, hh in zip(srdy8, hz)] + list(rdy[8:])
    zd = [(T + 1 - hh if hh > 0 else T - a) for a, hh in zip(srdy8, hz)] + [T - r for r in rdy[8:]]
    ddl = [T - r for r in rdy]
    zb = []
    for i in range(8):
        for l in occ[i]:
            if l > zs[i]: zb += [f'{i},{l}', f'{i},{T + 1 - l}']
    j = lambda v: ','.join(map(str, v))
    inp = f'/work/k/pe/h_{tag}.in'
    open(inp, 'w').write('\n'.join([str(len(terms)), ' '.join(map(str, terms))] + [f'{a} {b} {c}' for a, b, c in zip(ST, rdy, ddl)]) + '\n')
    env = dict(os.environ, SINGLES_PENDING='1', TOUCHBAD='1', LAW='0.3', ZS=j(zs), ZD=j(zd), XS=j(rdy), XD=j(ddl), CS=j(rdy), CD=j(ddl), ZBUSY=';'.join(zb))
    print(tag, 'W', W, 'ST', ST, 'rdy', rdy, flush=True)
    KB = f'/work/k/kbeam_t3_n{n}' if n > 8 else P.KB
    res = {}
    for s in seeds:
        out = f'/work/k/pe/h_{tag}_s{s}.out'
        if os.path.exists(out): os.remove(out)
        r = subprocess.run([KB, str(Wb), '100', str(s), '0.02', out, '4', '0'], stdin=open(inp), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, env=env)
        mind = min([int(l.split()[-1]) for l in r.stderr.split('\n') if l.startswith('depth') and l.split()[6] == str(len(terms))] + [99])
        print(tag, 'seed', s, 'rc', r.returncode, 'mind', mind, flush=True)
        res[s] = dict(rc=r.returncode, mind=mind)
        if r.returncode == 0:
            kg = build_kg(pl, out, zs, T, co, terms)
            q = out.replace('.out', '_asm.qasm'); d0, cx0 = kdrv.assemble(DX, DY, kg, q)
            ops = fuse(simplify(fuse(parse_ops(q)), verbose=False))
            for TT in (T, T + 1):
                sol = smilp.solve(ops, TT, tlim=300, verbose=False)
                print(tag, 'seed', s, 'asm', d0, 'cx', sum(1 for o in ops if o[0] == 'cx'), 'MILP', TT, sol is not None, flush=True)
                if sol is not None:
                    path = out.replace('.out', f'_m{TT}.qasm'); write(fuse(sol), path); res[s][f'T{TT}'] = path; break
    return res

if __name__ == '__main__':
    dx, dy = sys.argv[1], sys.argv[2]; T = int(sys.argv[3]); Wb = int(sys.argv[4]); seeds = sys.argv[5].split(','); h = int(sys.argv[6]); tag = sys.argv[7]
    co = sys.argv[8] if len(sys.argv) > 8 else '/work/classiq/artifacts/116/recipes/kernel_co.npy'
    print(json.dumps(run(P.load(dx, 0), P.load(dy, 1), T, Wb, seeds, h, tag, co)))
