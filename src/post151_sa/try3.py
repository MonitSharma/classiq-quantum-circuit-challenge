import pickle, sys, os, subprocess
sys.path.insert(0, '.')
exec(open('try2.py').read().split("xf, yf, T =")[0])
xf, yf, T = sys.argv[1], sys.argv[2], int(sys.argv[3])
DX = rebuild('x_loader_d44', xf, 'tx'); DY = rebuild('y_loader_d46_blkw', yf, 'ty')
pl = plan(DX, DY)
seq_, W, ST, rdy, unl = pl
print('W', W, 'rdy', rdy, flush=True)
md = max(T - 2 * min(rdy), 1)
for pm_ in (0b11111111, 0b00001111, 0b11110000, 0b11001100, 0b00110011):
    for Wb in (16000, 40000):
        for mu in (0.02, 0.05):
            for seed in (1, 2, 3):
                out = f'runs/p3_{T}_{pm_}_{Wb}_{mu}_{seed}.txt'
                env = dict(os.environ); env['SINGLES_PENDING'] = '1'; env['TOUCHBAD'] = '1'
                env['PERMSET'] = str(pm_)
                p = subprocess.run(['./c/kbeamP8', str(Wb), str(md), str(seed), str(mu), out, '4', '0'],
                                   input='\n'.join([str(len(KTERMS)), ' '.join(map(str, KTERMS))] +
                                   [f"{s} {r} {T-u}" for s, r, u in zip(ST, rdy, unl)]) + '\n',
                                   capture_output=True, text=True, env=env)
                if p.returncode == 0:
                    kg = build_kg_perm(pl, out)
                    r = assemble(DX, DY, kg, out.replace('.txt', '.qasm'))
                    print(f'FEASIBLE PERMSET={pm_:08b} W={Wb} mu={mu} s={seed} sigma={kg[0][1]} -> {r}', flush=True)
                    pickle.dump((pl, kg), open(out.replace('.txt', '.pkl'), 'wb'))
                    sys.exit(0)
    print(f'  permset {pm_:08b} done', flush=True)
print('INFEASIBLE with PERMSET at T =', T, flush=True)
