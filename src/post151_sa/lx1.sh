#!/bin/bash
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
PY=../../.venv/bin/python
: > runs/lx1.log
run(){ local tag=$1 md=$2 ns=$3 W=$4; shift 4
  env "$@" $PY -u lport.py x ./c/lbeam4 $md 0 $ns $W 24 16 0.5 0.02 $tag 2>&1 \
    | grep --line-buffered -v '^depth' >> runs/lx1.log; }
# BLKW index 4 == coordinate Lx1.  Push it hard so the beam freezes it early.
B200="14,28,30,200,42,24,30,27,29,33,31,29,31,31,29"
B400="14,28,30,400,42,24,30,27,29,33,31,29,31,31,29"
run Lx1a 44 24 7000 BLKWX="$B200" WFT=0.2 WFMAX=0.4 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
run Lx1b 44 24 7000 BLKWX="$B400" WFT=0.2 WFMAX=0.4 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
run Lx1c 45 24 7000 BLKWX="$B200" WFT=0.3 WFMAX=1.0 WREACH2=0.2 NP=20 WSPREAD=0.5 SPCAP=3 &
run Lx1d 46 24 7000 BLKWX="$B200" WFT=0.35 WFMAX=0.7 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
wait
echo LX1_DONE >> runs/lx1.log
