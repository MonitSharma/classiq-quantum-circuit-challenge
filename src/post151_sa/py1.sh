#!/bin/bash
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
PY=../../.venv/bin/python
: > runs/py1.log
run(){ local tag=$1 md=$2 ns=$3 W=$4; shift 4
  env "$@" $PY -u lport.py y ./c/lbeam4 $md 0 $ns $W 24 16 0.5 0.02 $tag 2>&1 \
    | grep --line-buffered -v '^depth' >> runs/py1.log; }
# BLKW index 1 == coordinate py.  Push it hard so the beam freezes the py wire early.
P200="200,28,44,24,32,26,34,34,32,30,32,32,30,30,32"
P400="400,28,44,24,32,26,34,34,32,30,32,32,30,30,32"
run Py1a 45 24 7000 BLKWX="$P200" WFT=0.2 WFMAX=0.4 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
run Py1b 45 24 7000 BLKWX="$P400" WFT=0.2 WFMAX=0.4 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
run Py1c 46 24 7000 BLKWX="$P200" WFT=0.2 WFMAX=0.4 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
run Py1d 46 24 7000 BLKWX="$P400" WFT=0.3 WFMAX=1.0 WREACH2=0.2 NP=20 WSPREAD=0.5 SPCAP=3 &
wait
echo PY1_DONE >> runs/py1.log
