"""Loader beam driver: run lbeam4/lbeam5, evaluate the ready vector of every solution.

usage: lsearch.py side binary maxd fzcap nseeds W K wcond wreach wcx
Prints one line per solution, then the best by (max rdy, sum rdy).
"""
import pickle, sys, os, subprocess, time, json
sys.path.insert(0, '.')
from lbeval2 import load_beam, sa4
from sim import check_loader2
from depth import gate_depth
from kdrv import profile
from kgen import side_plan

def evaluate(D, beampath, tag):
    bd, seq = load_beam(beampath)
    d, pen, g = sa4(D, seq, tag=tag, binary='./c/sa4')
    chk = check_loader2(g, D['newcode'])
    if chk['max_dev'] > 1e-9:
        return None
    D2 = dict(D); D2['gates'] = g; D2['fix'] = []; D2['depth'] = gate_depth(g)
    e, _ = profile(g)
    fx, W, co, rdy = side_plan(g, e, D2, 0)
    return dict(depth=D2['depth'], prof=e, rdy=rdy, W=W, coords=co, gates=g, fix=fx, pen=pen)

def main():
    side, binary, maxd, fzcap, nseeds = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    Wb = int(sys.argv[6]); K = int(sys.argv[7]); wcond = float(sys.argv[8]); wreach = float(sys.argv[9]); wcx = float(sys.argv[10])
    D = pickle.load(open(f'runs/bestfz_{side}.pkl' if os.path.exists(f'runs/bestfz_{side}.pkl') else f'runs/s118{side}.pkl', 'rb'))
    D = pickle.load(open(f'runs/s118{side}.pkl', 'rb'))
    lb = f'runs/s118{side}.lb'
    env0 = dict(os.environ)
    env0['SINGLES_PENDING'] = '1'
    if side == 'y':
        env0['BLKW'] = '32,28,44,24,32,26,34,34,32,30,32,32,30,30,32'
    else:
        env0['BLKW'] = '14,28,30,40,42,24,30,27,29,33,31,29,31,31,29'
    env0.update(dict(WFRZ='0', WFT='0.35', WFMAX='0.7', FZMAX='3', WREACH2='0.15', NP='18', WSPREAD='0.6', SPCAP='3'))
    if fzcap > 0:
        env0['FZCAP'] = str(fzcap)
    best = None; n = 0
    for seed in range(1, nseeds + 1):
        out = f'runs/ls_{side}_{maxd}_{fzcap}_{Wb}_s{seed}.txt'
        t0 = time.time()
        p = subprocess.run([binary, str(Wb), str(K), str(maxd), str(seed), str(wcond), str(wreach), out, str(wcx)],
                           stdin=open(lb), capture_output=True, text=True, env=env0)
        dt = time.time() - t0
        if p.returncode != 0:
            last = [l for l in p.stderr.strip().split('\n') if l.startswith('depth')]
            print(f'  fail s{seed} ({dt:.0f}s) ' + (last[-1][:110] if last else ''), flush=True)
            continue
        n += 1
        r = evaluate(D, out, f'ls{side}{seed}')
        if r is None:
            print(f'  s{seed} INVALID', flush=True); continue
        key = (max(r['rdy']), sum(r['rdy']))
        print(f'OK s{seed} depth {r["depth"]} rdy {r["rdy"]} max {key[0]} sum {key[1]} W {r["W"]} coords {r["coords"]} ({dt:.0f}s)', flush=True)
        if best is None or key < best[0]:
            best = (key, out, r)
    if best is not None:
        pickle.dump(dict(D=D, **{k: best[2][k] for k in ('gates', 'fix', 'depth', 'prof')}),
                    open(f'runs/lbest_{side}_{maxd}_{fzcap}.pkl', 'wb'))
        print(f'BEST {side} maxd={maxd} fzcap={fzcap}: max {best[0][0]} sum {best[0][1]} from {best[1]}  ({n}/{nseeds} solved)', flush=True)
    else:
        print(f'BEST {side} maxd={maxd} fzcap={fzcap}: none ({n}/{nseeds} solved)', flush=True)

main()
