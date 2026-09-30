"""Feasibility sweep: given the 118 loaders, is a kernel schedule possible at target T?"""
import pickle, sys, os, subprocess, time
sys.path.insert(0, '.')
from kgen2 import build_kg_perm
from kdrv import assemble, KTERMS, full_gates, profile, code_vectors

R = '../../artifacts/118/recipes/'
DX = pickle.load(open(R + 'x_loader_d44.pkl', 'rb'))
DY = pickle.load(open(R + 'y_loader_d46_blkw.pkl', 'rb'))
pl, _old = pickle.load(open(R + 'kernel_plan_and_gates_118.pkl', 'rb'))
seq, W, ST, rdy, unl = pl

print('W   ', W)
print('ST  ', ST)
print('rdy ', rdy)
print('unl ', unl)
print('seq len', len(seq), 'nterms', len(KTERMS), flush=True)

T = int(sys.argv[1])
ndl = int(sys.argv[2]) if len(sys.argv) > 2 else 0
configs = []
for Wb in (4000, 12000, 40000):
    for wdl in (0, 2.0, 4.0):
        for mu in (0.02, 0.05):
            for kch in (40, 150):
                configs.append((Wb, wdl, mu, kch))
seeds = [1, 2, 3, 4]
bins = ['./c/kbeamP8', './c/kbeamQ8']
for Wb, wdl, mu, kch in configs:
    got = False
    for binary in bins:
        for seed in seeds:
            out = f'runs/t{T}_W{Wb}_w{wdl}_m{mu}_k{kch}_s{seed}.txt'
            env = dict(os.environ); env['SINGLES_PENDING'] = '1'; env['KCH'] = str(kch)
            if wdl: env['WDL'] = str(wdl)
            if ndl: env['TOUCHBAD'] = '1'
            md = max(T - 2 * min(rdy), 1)
            t0 = time.time()
            p = subprocess.run([binary, str(Wb), str(md), str(seed), str(mu), out, '4', '0'],
                               input='\n'.join([str(len(KTERMS)), ' '.join(map(str, KTERMS))] +
                               [f"{s} {r} {T-u}" for s, r, u in zip(ST, rdy, unl)]) + '\n',
                               capture_output=True, text=True, env=env)
            dt = time.time() - t0
            if p.returncode == 0:
                kg = build_kg_perm(pl, out)
                r = assemble(DX, DY, kg, out.replace('.txt', '.qasm'))
                print(f'FEASIBLE T={T} {binary} W={Wb} wdl={wdl} mu={mu} kch={kch} seed={seed} {dt:.0f}s -> {r}', flush=True)
                pickle.dump((pl, kg), open(out.replace('.txt', '.pkl'), 'wb'))
                got = True
                break
            elif dt > 120:
                print(f'  slow-fail {binary} W={Wb} wdl={wdl} mu={mu} k={kch} s={seed} {dt:.0f}s', flush=True)
        if got: break
    if not got:
        print(f'fail T={T} W={Wb} wdl={wdl} mu={mu} kch={kch}', flush=True)
print('DONE T=', T, flush=True)
