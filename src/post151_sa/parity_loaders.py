"""Generate and validate loaders whose parity wire is only read after creation.
Run from src/post151_sa with CLASSIQ_ROOT and CLASS_CODES set.
"""
import argparse, concurrent.futures, json, os, pickle, subprocess, time
from pathlib import Path
from lbeval2 import load_beam, sa4
from sim import check_loader2, symbolic_final
from kdrv import profile
from kgen import side_plan

OUT = Path('runs/parity_0923')

def run(side, seed, width, maxdepth, label, extra):
    tag = f'{label}_{side}_w{width}_d{maxdepth}_s{seed}'
    out = OUT / (tag + '.txt')
    env = dict(os.environ, PROTECT_TARGET='32', SINGLES_PENDING='1',
               WFRZ='0', WFT='0.35', WFMAX='0.7', FZMAX='3',
               WREACH2='0.15', NP='18', WSPREAD='0.6', SPCAP='3')
    # Parity's last control touch does not close its Z window.
    env['BLKW'] = '1,30,30,30,30,30,30,30,30,30,30,30,30,30,30'
    if side == 'x':
        env.update(PREFIX=str(OUT / 'px_prefix.txt'), PREFIXK='1')
    env.update(extra)
    start = time.monotonic()
    with open(f'runs/s118{side}.lb') as inp, open(OUT / (tag + '.log'), 'w') as log:
        p = subprocess.run(['./c/lbeam_parity', str(width), '24', str(maxdepth), str(seed),
                            '16', '0.5', str(out), '0.02'], stdin=inp, stderr=log, env=env)
    rec = dict(tag=tag, side=side, returncode=p.returncode, seconds=time.monotonic()-start)
    if p.returncode == 0:
        D = pickle.load(open(f'runs/s118{side}.pkl', 'rb'))
        _, seq = load_beam(out)
        assert all(t != 5 for c,t in (seq[1:] if side=='x' else seq))
        if side == 'x': assert seq[0] == (4,5)
        d,pen,g = sa4(D,seq,tag=tag,binary='./c/sa4')
        chk = check_loader2(g,D['newcode'])
        assert pen == 0 and chk['max_dev'] < 1e-9, (pen,chk)
        targeting = [i for i,op in enumerate(g) if op[0][0]=='cx' and op[2]==5]
        assert len(targeting)==(1 if side=='x' else 0)
        assert not any(op[0][0]=='h' and op[1]==5 for op in g)
        D = dict(D,gates=g,fix=[],depth=d)
        prof,_ = profile(g)
        fx,w,coords,ready = side_plan(g,prof,D,0,maxlen=0)
        assert not fx
        assert symbolic_final(g)[5] == (48 if side=='x' else 32)
        rec.update(depth=max(prof), ready=ready, wires=w, coords=coords,
                   max_dev=chk['max_dev'], cx=len(seq), pickle=str(OUT / (tag+'.pkl')))
        pickle.dump(D,open(rec['pickle'],'wb'))
    (OUT / (tag+'.json')).write_text(json.dumps(rec,indent=2))
    print(json.dumps(rec),flush=True)
    return rec

if __name__ == '__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--width',type=int,default=2000)
    ap.add_argument('--depth',type=int,default=52); ap.add_argument('--seeds',default='1,2')
    ap.add_argument('--sides',default='x,y'); ap.add_argument('--label',default='protect')
    ap.add_argument('--env',action='append',default=[]); args=ap.parse_args()
    OUT.mkdir(exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(run,side,int(seed),args.width,args.depth,args.label,
                             dict(x.split('=',1) for x in args.env))
                 for side in args.sides.split(',') for seed in args.seeds.split(',')]
        for f in concurrent.futures.as_completed(futures): f.result()
