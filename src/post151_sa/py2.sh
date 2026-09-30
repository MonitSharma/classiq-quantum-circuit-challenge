#!/bin/bash
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
PY=../../.venv/bin/python
: > runs/py2.log
run(){ local side=$1 tag=$2 md=$3 ns=$4 W=$5; shift 5
  env "$@" $PY -u lport.py $side ./c/lbeam4 $md 0 $ns $W 24 16 0.5 0.02 $tag 2>&1 \
    | grep --line-buffered -v '^depth' >> runs/py2.log; }
# BLKTOT = BLKW[1]+BLKW[2]+BLKW[4]+BLKW[8]; use RELATIVE weights (one target high, rest tiny)
YREL="100,1,1,1,1,1,1,1,1,1,1,1,1,1,1"      # py (index 1) dominant
XREL="1,1,1,100,1,1,1,1,1,1,1,1,1,1,1"      # Lx1 (index 4) dominant
XBOTH="1,1,1,100,1,1,1,1,1,1,1,1,60,1,1"    # Lx1 and Lx2
run y Py2a 45 20 7000 BLKWX="$YREL" WFT=0.35 WFMAX=0.7 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
run y Py2b 46 20 7000 BLKWX="$YREL" WFT=0.35 WFMAX=0.7 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
run x Lx2a 45 20 7000 BLKWX="$XREL" WFT=0.35 WFMAX=0.7 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
run x Lx2b 44 20 7000 BLKWX="$XBOTH" WFT=0.35 WFMAX=0.7 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
wait
echo PY2_DONE >> runs/py2.log
