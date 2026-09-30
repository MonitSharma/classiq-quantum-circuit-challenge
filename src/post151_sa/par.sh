#!/bin/bash
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
PY=../../.venv/bin/python
: > runs/par.log
run(){ local side=$1 tag=$2 md=$3 ns=$4 W=$5; shift 5
  env "$@" $PY -u lport.py $side ./c/lbeam8 $md 0 $ns $W 24 16 0.5 0.02 $tag 2>&1 \
    | grep --line-buffered -v '^depth' >> runs/par.log; }
XW="1,1,1,100,1,1,1,1,1,1,1,1,60,1,1"
YW="32,28,44,24,32,26,34,34,32,30,32,32,30,30,32"
E="WFT=0.35 WFMAX=0.7 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3"
run x Px44 44 16 8000 PARITYROW=48 BLKWX="$XW" $E &
run x Px45 45 16 8000 PARITYROW=48 BLKWX="$XW" $E &
run y Py46 46 16 8000 PARITYROW=32 BLKW="$YW" $E &
run y Py45 45 16 8000 PARITYROW=32 BLKW="$YW" $E &
run y Py47 47 16 8000 PARITYROW=32 BLKW="$YW" $E &
run x Px46 46 16 8000 PARITYROW=48 BLKWX="$XW" $E &
wait
echo PAR_DONE >> runs/par.log
