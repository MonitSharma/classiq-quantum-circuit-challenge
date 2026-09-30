"""wiperm.py X Y T W seeds perm tag [milp]
FEM kernel beam where plan wire i ends in role perm[i] (final row ST[perm[i]], unloader deadlines of that role).
Valid because the unloader can be relabeled among code wires (sigma in build_kg_s / kdrv.assemble)."""
import sys, os, json, subprocess, numpy as np
os.environ.update(STRICT='1', ZOCC='1', FUSE='1')
sys.path.insert(0, '/work/k'); import paireval as P
import ev116, kdrv, smilp
from postopt import parse_ops, fuse, write
from canc import simplify
KBP = '/work/k/kbeam_t3p'

def run(DX, DY, T, Wb, seeds, perm, tag, milp=True, co_path='/work/classiq/artifacts/116/recipes/kernel_co.npy', extra_env=None):
    co = np.load(co_path); terms = [int(m) for m in np.flatnonzero(abs(co) > 1e-10) if m]
    pl, srdy = P.windows(DX, DY); seq, W8, ST, rdy, unl = pl
    hz = P.hz_times(DX, DY, W8); occ = P.occupancy(DX, DY, W8)
    zs = [(h - 1 if h > 0 else a) for a, h in zip(srdy, hz)]
    ze = [(h if h > 0 else a + 1) for a, h in zip(srdy, hz)]          # role end: rotations allowed up to T+1-ze
    xs = list(rdy); xd = [T - rdy[perm[i]] for i in range(8)]
    zd = [T + 1 - ze[perm[i]] for i in range(8)]
    zb = []
    for i in range(8):
        zb += [f'{i},{l}' for l in occ[i] if l > zs[i]]
        j = perm[i]; zb += [f'{i},{T + 1 - l}' for l in occ[j] if l > zs[j]]
    J = lambda v: ','.join(map(str, v))
    HM = [ST[perm[i]] for i in range(8)]
    inp = f'/work/k/pe/p_{tag}.in'
    open(inp, 'w').write('\n'.join([str(len(terms)), ' '.join(map(str, terms))] + [f'{a} {b} {c}' for a, b, c in zip(ST, rdy, xd)]) + '\n')
    env = dict(os.environ, SINGLES_PENDING='1', TOUCHBAD='1', LAW='0.3', ZS=J(zs), ZD=J(zd), XS=J(xs), XD=J(xd), CS=J(xs), CD=J(xd), ZBUSY=';'.join(zb), HOMEV=J(HM))
    if extra_env: env.update(extra_env)
    res = {}
    for s in seeds:
        out = f'/work/k/pe/p_{tag}_s{s}.out'
        if os.path.exists(out): os.remove(out)
        r = subprocess.run([KBP, str(Wb), '100', str(s), '0.02', out, '4', '0'], stdin=open(inp), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, env=env)
        mind = min([int(l.split()[-1]) for l in r.stderr.split('\n') if l.startswith('depth') and l.split()[6] == str(len(terms))] + [99])
        print(tag, 'perm', perm, 'seed', s, 'rc', r.returncode, 'mind', mind, flush=True)
        res[s] = dict(rc=r.returncode, mind=mind)
        if r.returncode == 0 and milp:
            ev116.CO = co; ev116.KTERMS = terms; kdrv.CO = co
            # rotation start: build_kg_s uses svec (start) and T-unl (end); use the role-permuted end
            unl_p = [rdy[perm[i]] for i in range(8)]
            pl2 = (seq, W8, ST, rdy, unl_p)
            kg = ev116.build_kg_s(pl2, out, zs, T)
            q = out.replace('.out', '_asm.qasm'); d0, cx0 = ev116.assemble(DX, DY, kg, q)
            ops = fuse(simplify(fuse(parse_ops(q)), verbose=False))
            for TT in (T, T + 1):
                sol = smilp.solve(ops, TT, tlim=300, verbose=False)
                print(tag, 'seed', s, 'asm', d0, 'cx', sum(1 for o in ops if o[0] == 'cx'), 'MILP', TT, sol is not None, flush=True)
                if sol is not None:
                    path = out.replace('.out', f'_m{TT}.qasm'); write(fuse(sol), path); res[s][f'T{TT}'] = path; break
    return res

if __name__ == '__main__':
    X, Y = sys.argv[1], sys.argv[2]; T = int(sys.argv[3]); Wb = int(sys.argv[4]); seeds = sys.argv[5].split(',')
    perm = json.loads(sys.argv[6]); tag = sys.argv[7]; milp = len(sys.argv) <= 8 or sys.argv[8] != 'nomilp'
    print(json.dumps(run(P.load(X, 0), P.load(Y, 1), T, Wb, seeds, perm, tag, milp)))
