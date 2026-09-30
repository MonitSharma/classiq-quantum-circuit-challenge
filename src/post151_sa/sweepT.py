import pickle, sys, os, subprocess, time, itertools
sys.path.insert(0, '.')
from kgen2 import build_kg_perm
from kdrv import assemble, KTERMS

R = '../../artifacts/124/recipes/'
DX = pickle.load(open(R + 'x_loader_star47_span.pkl', 'rb'))
DY = pickle.load(open(R + 'y_loader_beam47_span.pkl', 'rb'))
pl = pickle.load(open(R + 'kernel_plan.pkl', 'rb'))
seq, W, ST, rdy, unl = pl
inp = [str(len(KTERMS)), ' '.join(map(str, KTERMS))] + [f"{s} {r} {T-u}" for s, r, u in zip(ST, rdy, unl)]

T = int(sys.argv[1])
configs = []
for Wb in (8000, 30000):
    for wdl in (0, 2.0):
        for mu in (0.02, 0.05):
            for kch in (40, 150):
                configs.append((Wb, wdl, mu, kch))
seeds = [1, 2, 3]
for Wb, wdl, mu, kch in configs:
    got = False
    for seed in seeds:
        out = f'runs/sw_T{T}_W{Wb}_wdl{wdl}_mu{mu}_k{kch}_s{seed}.txt'
        env = dict(os.environ); env['SINGLES_PENDING'] = '1'; env['KCH'] = str(kch)
        if wdl: env['WDL'] = str(wdl)
        md = max(T - 74, 1)
        t0 = time.time()
        p = subprocess.run(['./c/kbeamP8', str(Wb), str(md), str(seed), str(mu), out, '4', '0'],
                           input='\n'.join(inp) + '\n', capture_output=True, text=True, env=env)
        dt = time.time() - t0
        if p.returncode == 0:
            kg = build_kg_perm(pl, out)
            r = assemble(DX, DY, kg, out.replace('.txt', '.qasm'))
            print(f'FEASIBLE T={T} W={Wb} wdl={wdl} mu={mu} kch={kch} seed={seed} {dt:.0f}s -> {r}', flush=True)
            pickle.dump((pl, kg), open(out.replace('.txt', '.pkl'), 'wb'))
            got = True
            break
    if not got:
        print(f'fail T={T} W={Wb} wdl={wdl} mu={mu} kch={kch}', flush=True)
