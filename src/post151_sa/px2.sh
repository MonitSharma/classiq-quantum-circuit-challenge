#!/bin/bash
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
PY=../../.venv/bin/python
OUT=runs/parity_0923
: > runs/px2.log
# px is created at layer 1 (PREFIX) and then never targeted (PROTECT_TARGET = wire 5 = bit 32).
# Its Z-window is therefore ~[1, T-1], so px needs NO early freeze: give it a LOW weight and push
# the three real cost wires (Lx0=code2, Lx1=code4, Lx2=code12) hard.
run(){ local tag=$1 md=$2 ns=$3 W=$4; shift 4
  env PROTECT_TARGET=32 SINGLES_PENDING=1 PREFIX=$OUT/px_prefix.txt PREFIXK=1 "$@" \
      $PY -u - <<'EOF' >> runs/px2.log 2>&1
import os, subprocess, sys, time, pickle
from lbeval2 import load_beam, sa4
from sim import check_loader2
from kdrv import profile
from kgen import side_plan
D = pickle.load(open('runs/s118x.pkl','rb'))
for seed in range(1, int(os.environ['NS'])+1):
    out = 'runs/po_%s_s%d.txt' % (os.environ['TAG'], seed)
    p = subprocess.run(['./c/lbeam_parity', os.environ['WW'], '24', os.environ['MD'], str(seed),
                        '16', '0.5', out, '0.02'], stdin=open('runs/s118x.lb'),
                        capture_output=True, text=True, env=os.environ)
    if p.returncode != 0:
        print('  fail s%d' % seed, flush=True); continue
    bd, seq = load_beam(out)
    d, pen, g = sa4(D, seq, tag='px', binary='./c/sa4')
    chk = check_loader2(g, D['newcode'])
    if pen != 0 or chk['max_dev'] > 1e-9:
        print('  s%d INVALID' % seed, flush=True); continue
    e, _ = profile(g); fx, W, co, rdy = side_plan(g, e, D, 0)
    print('OK s%d depth %d rdy %s coords %s W %s' % (seed, max(e), rdy, co, W), flush=True)
EOF
}
export BLK1="1,1,50,1,50,1,1,1,1,1,1,50,1,1,1"
export BLK2="1,60,60,1,60,1,1,1,1,1,1,60,1,1,1"
for s in 1 2 3 4; do
  ( export TAG=PxA$s MD=44 NS=1 WW=8000 BLKWX="$BLK1"; run A$s 44 1 8000 ) &
done
for s in 1 2 3 4; do
  ( export TAG=PxB$s MD=45 NS=1 WW=8000 BLKWX="$BLK2"; run B$s 45 1 8000 ) &
done
wait
echo PX2_DONE >> runs/px2.log
