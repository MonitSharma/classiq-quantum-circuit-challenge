#!/bin/bash
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
PY=../../.venv/bin/python
: > runs/maxk.log
run(){ local side=$1 tag=$2 md=$3 ns=$4 W=$5; shift 5
  env "$@" $PY -u lport.py $side ./c/lbeam4 $md 0 $ns $W 24 16 0.5 0.02 $tag 2>&1 \
    | grep --line-buffered -v '^depth' >> runs/maxk.log; }
# MAXK = max number of CX edges applied per loader layer (default 4). Never swept before.
XREL="1,1,1,100,1,1,1,1,1,1,1,1,60,1,1"
E="WFT=0.35 WFMAX=0.7 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 BLKWX=$XREL"
run x Mk5a 44 24 7000 MAXK=5 $E &
run x Mk6a 44 24 7000 MAXK=6 $E &
run x Mk3a 44 24 7000 MAXK=3 $E &
run x Mk2a 44 24 7000 MAXK=2 $E &
run x Mk5b 43 24 7000 MAXK=5 $E &
run x Mk6b 43 24 7000 MAXK=6 $E &
wait
echo MAXK_DONE >> runs/maxk.log
