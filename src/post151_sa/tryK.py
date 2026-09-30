"""Build a plan from a candidate loader beam output and test kernel feasibility at target T."""
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
yfile = sys.argv[1]; T = int(sys.argv[2])
DY = pickle.load(open(R + 'y_loader_d46_blkw.pkl', 'rb'))
if yfile != 'champ':
    bd, seq = load_beam(yfile)
    d, pen, g = sa4(DY, seq, tag='tT', binary='./c/sa4')
    chk = check_loader2(g, DY['newcode'])
    assert pen == 0 and chk['max_dev'] < 1e-9, (pen, chk['max_dev'])
    DY = dict(DY); DY['gates'] = g; DY['fix'] = []; DY['depth'] = gate_depth(g)

pl = plan(DX, DY)
seq_, W, ST, rdy, unl = pl
print('W', W, 'ST', ST, 'rdy', rdy, 'unl', unl, 'seq', seq_, flush=True)
found = []
tag = os.path.basename(yfile).replace('.txt', '')
for Wb in (6000, 20000, 40000):
    for mu in (0.02, 0.05):
        for seed in (1, 2, 3, 4, 5, 6):
            out = f'runs/tK{T}_{tag}_{Wb}_{mu}_{seed}.txt'
            env = dict(os.environ); env['SINGLES_PENDING'] = '1'; env['TOUCHBAD'] = '1'
            md = max(T - 2 * min(rdy), 1)
            p = subprocess.run(['./c/kbeamQ8', str(Wb), str(md), str(seed), str(mu), out, '4', '0'],
                               input='\n'.join([str(len(KTERMS)), ' '.join(map(str, KTERMS))] +
                               [f"{s} {r} {T-u}" for s, r, u in zip(ST, rdy, unl)]) + '\n',
                               capture_output=True, text=True, env=env)
            if p.returncode == 0:
                kg = build_kg_perm(pl, out)
                r = assemble(DX, DY, kg, out.replace('.txt', '.qasm'))
                print(f'FEASIBLE T={T} W={Wb} mu={mu} s={seed} -> {r}  {out}', flush=True)
                pickle.dump((pl, kg), open(out.replace('.txt', '.pkl'), 'wb'))
                found.append((out, r))
                break
        if found: break
    if found: break
print('RESULT T=', T, found, flush=True)
