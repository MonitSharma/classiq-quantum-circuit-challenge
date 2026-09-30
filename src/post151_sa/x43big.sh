#!/bin/bash
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
PY=../../.venv/bin/python
: > runs/x43big.log
run(){ local tag=$1 ns=$2 W=$3; shift 3
  env "$@" $PY -u lport.py x ./c/lbeam4 43 0 $ns $W 24 16 0.5 0.02 $tag 2>&1 \
    | grep --line-buffered -v '^depth' >> runs/x43big.log; }
run x43p 30 8000 BLKWX="1,40,42,40,24,30,27,40,29,33,31,40,31,31,29" WFT=0.2 WFMAX=0.4 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
run x43q 30 8000 BLKWX="1,28,30,40,42,24,30,27,29,33,31,29,31,31,29"   WFT=0.15 WFMAX=1.6 WREACH2=0.3 NP=24 WSPREAD=0.3 SPCAP=2 &
run x43r 30 8000 NOBLKW=1 WFT=0.35 WFMAX=0.7 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
wait
echo X43BIG_DONE >> runs/x43big.log
