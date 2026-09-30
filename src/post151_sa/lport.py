"""Loader portfolio search: run many beam configs, evaluate each ready vector against the
kernel's per-direction touch counts, keep the best few by the real objective proxy.

usage: lport.py side maxd fzcap nseeds W K wcond wreach wcx tag
"""
import pickle, sys, os, subprocess, time
sys.path.insert(0, '.')
from lbeval2 import load_beam, sa4
from sim import check_loader2
from depth import gate_depth
from kdrv import profile
from kgen import side_plan

# kernel touch count per code coordinate, measured on the 118 champion
TOUCH = {'y': {1: 31, 2: 40, 4: 25, 8: 33}, 'x': {1: 26, 2: 38, 4: 29, 12: 29}}

def evaluate(D, beampath, tag):
    bd, seq = load_beam(beampath)
    d, pen, g = sa4(D, seq, tag=tag, binary='./c/sa4')
    chk = check_loader2(g, D['newcode'])
    if chk['max_dev'] > 1e-9: return None
    D2 = dict(D); D2['gates'] = g; D2['fix'] = []; D2['depth'] = gate_depth(g)
    e, _ = profile(g)
    fx, W, co, rdy = side_plan(g, e, D2, 0)
    return dict(depth=D2['depth'], prof=e, rdy=rdy, W=W, coords=co, gates=g, fix=fx, pen=pen)

def main():
    side, binary, maxd, fzcap, nseeds = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    Wb, K, wcond, wreach, wcx = int(sys.argv[6]), int(sys.argv[7]), float(sys.argv[8]), float(sys.argv[9]), float(sys.argv[10])
    tag = sys.argv[11]
    D = pickle.load(open(f'runs/s118{side}.pkl', 'rb'))
    lb = f'runs/s118{side}.lb'
    env0 = dict(os.environ); env0['SINGLES_PENDING'] = '1'
    if os.environ.get('NOBLKW') == '1':
        pass
    elif os.environ.get('BLKWX'):
        env0['BLKW'] = os.environ['BLKWX']
    else:
        env0['BLKW'] = ('32,28,44,24,32,26,34,34,32,30,32,32,30,30,32' if side == 'y'
                        else '14,28,30,40,42,24,30,27,29,33,31,29,31,31,29')
    env0.update(dict(WFRZ='0', WFT='0.35', WFMAX='0.7', FZMAX='3', WREACH2='0.15', NP='18',
                     WSPREAD='0.6', SPCAP='3'))
    if fzcap > 0: env0['FZCAP'] = str(fzcap)
    port = []
    for seed in range(1, nseeds + 1):
        out = f'runs/po_{tag}_s{seed}.txt'
        t0 = time.time()
        p = subprocess.run([binary, str(Wb), str(K), str(maxd), str(seed), str(wcond), str(wreach), out, str(wcx)],
                           stdin=open(lb), capture_output=True, text=True, env=env0)
        dt = time.time() - t0
        if p.returncode != 0:
            print(f'  fail s{seed} ({dt:.0f}s)', flush=True); continue
        r = evaluate(D, out, f'po{tag}{seed}')
        if r is None:
            print(f'  s{seed} INVALID', flush=True); continue
        tc = TOUCH[side]
        prox = max(rr + tc.get(cc, 99) for rr, cc in zip(r['rdy'], r['coords']))
        print(f'OK s{seed} depth {r["depth"]} rdy {r["rdy"]} coords {r["coords"]} W {r["W"]} '
              f'proxy {prox} ({dt:.0f}s)', flush=True)
        port.append((prox, max(r['rdy']), sum(r['rdy']), out, r))
    port.sort(key=lambda t: (t[0], t[1], t[2]))
    for prox, mx, sm, out, r in port[:4]:
        print(f'  CAND proxy {prox} max {mx} sum {sm} {out} rdy {r["rdy"]} coords {r["coords"]}', flush=True)
    if port:
        prox, mx, sm, out, r = port[0]
        pickle.dump(dict(D=D, **{k: r[k] for k in ('gates', 'fix', 'depth', 'prof')}),
                    open(f'runs/pbest_{tag}.pkl', 'wb'))
        print(f'PBEST {tag} proxy {prox} max {mx} sum {sm} from {out} ({len(port)}/{nseeds} solved)', flush=True)
    else:
        print(f'PBEST {tag} none ({nseeds} tried)', flush=True)

main()
