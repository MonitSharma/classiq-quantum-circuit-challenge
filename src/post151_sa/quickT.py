import pickle, sys, os, subprocess
sys.path.insert(0, '.')
from lbeval2 import load_beam, sa4
from sim import check_loader2
from depth import gate_depth
from kgen import plan
from kgen2 import build_kg_perm
from kdrv import assemble, KTERMS
R = '../../artifacts/118/recipes/'
DX = pickle.load(open(R + 'x_loader_d44.pkl', 'rb'))
DY0 = pickle.load(open(R + 'y_loader_d46_blkw.pkl', 'rb'))
yfile = sys.argv[1]; T = int(sys.argv[2])
if yfile == 'champ':
    DY = DY0
else:
    bd, seq = load_beam(yfile)
    d, pen, g = sa4(DY0, seq, tag='qT', binary='./c/sa4')
    chk = check_loader2(g, DY0['newcode'])
    assert pen == 0 and chk['max_dev'] < 1e-9
    DY = dict(DY0); DY['gates'] = g; DY['fix'] = []; DY['depth'] = gate_depth(g)
pl = plan(DX, DY)
seq_, W, ST, rdy, unl = pl
print('W', W, 'rdy', rdy, 'unl', unl, flush=True)
md = max(T - 2 * min(rdy), 1)
for Wb in (8000, 20000):
    for seed in (1, 2, 3, 4):
        out = f'runs/q{T}_{os.path.basename(yfile)}_{Wb}_{seed}.txt'
        env = dict(os.environ); env['SINGLES_PENDING'] = '1'; env['TOUCHBAD'] = '1'
        p = subprocess.run(['./c/kbeamQ8', str(Wb), str(md), str(seed), '0.02', out, '4', '0'],
                           input='\n'.join([str(len(KTERMS)), ' '.join(map(str, KTERMS))] +
                           [f"{s} {r} {T-u}" for s, r, u in zip(ST, rdy, unl)]) + '\n',
                           capture_output=True, text=True, env=env)
        print(f'  W={Wb} s={seed} rc={p.returncode}', flush=True)
        if p.returncode == 0:
            kg = build_kg_perm(pl, out)
            r = assemble(DX, DY, kg, out.replace('.txt', '.qasm'))
            print('FEASIBLE', r, out, flush=True)
            pickle.dump((pl, kg), open(out.replace('.txt', '.pkl'), 'wb'))
            sys.exit(0)
print('INFEASIBLE at T =', T, flush=True)
