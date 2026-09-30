"""Build a plan from candidate x AND y loader beam outputs; test kernel feasibility at T."""
import pickle, sys, os, subprocess
sys.path.insert(0, '.')
from lbeval2 import load_beam, sa4
from sim import check_loader2
from depth import gate_depth
from kgen import plan
from kgen2 import build_kg_perm
from kdrv import assemble, KTERMS, profile

R = '../../artifacts/118/recipes/'
def rebuild(base, path, tag):
    D0 = pickle.load(open(R + base + '.pkl', 'rb'))
    if path == 'champ': return D0
    bd, seq = load_beam(path)
    d, pen, g = sa4(D0, seq, tag=tag, binary='./c/sa4')
    chk = check_loader2(g, D0['newcode'])
    assert pen == 0 and chk['max_dev'] < 1e-9, (path, pen, chk['max_dev'])
    D = dict(D0); D['gates'] = g; D['fix'] = []; D['depth'] = gate_depth(g)
    e, _ = profile(g); print(' ', path, 'depth', max(e), 'prof', e, flush=True)
    return D

xf, yf, T = sys.argv[1], sys.argv[2], int(sys.argv[3])
DX = rebuild('x_loader_d44', xf, 'tx'); DY = rebuild('y_loader_d46_blkw', yf, 'ty')
pl = plan(DX, DY)
seq_, W, ST, rdy, unl = pl
print('W', W, 'rdy', rdy, 'unl', unl, flush=True)
md = max(T - 2 * min(rdy), 1)
for Wb in (6000, 16000, 40000):
    for mu in (0.02, 0.05):
        for seed in (1, 2, 3, 4, 5, 6):
            out = f'runs/y2_{T}_{os.path.basename(xf)[:-4]}_{os.path.basename(yf)[:-4]}_{Wb}_{mu}_{seed}.txt'
            env = dict(os.environ); env['SINGLES_PENDING'] = '1'; env['TOUCHBAD'] = '1'
            p = subprocess.run(['./c/kbeamQ8', str(Wb), str(md), str(seed), str(mu), out, '4', '0'],
                               input='\n'.join([str(len(KTERMS)), ' '.join(map(str, KTERMS))] +
                               [f"{s} {r} {T-u}" for s, r, u in zip(ST, rdy, unl)]) + '\n',
                               capture_output=True, text=True, env=env)
            print(f'  W={Wb} mu={mu} s={seed} rc={p.returncode}', flush=True)
            if p.returncode == 0:
                kg = build_kg_perm(pl, out)
                r = assemble(DX, DY, kg, out.replace('.txt', '.qasm'))
                print('FEASIBLE', r, out, flush=True)
                pickle.dump((pl, kg), open(out.replace('.txt', '.pkl'), 'wb'))
                sys.exit(0)
print('INFEASIBLE at T =', T, flush=True)
