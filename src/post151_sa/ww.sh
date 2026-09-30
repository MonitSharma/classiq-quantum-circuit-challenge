#!/bin/bash
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
PY=../../.venv/bin/python
: > runs/ww.log
run(){ local side=$1 tag=$2 md=$3 ns=$4 W=$5; shift 5
  env "$@" $PY -u lport.py $side ./c/lbeam7 $md 0 $ns $W 24 16 0.5 0.02 $tag 2>&1 \
    | grep --line-buffered -v '^depth' >> runs/ww.log; }
XW="1,1,1,100,1,1,1,1,1,1,1,1,60,1,1"
YW="32,28,44,24,32,26,34,34,32,30,32,32,30,30,32"
E="WFT=0.35 WFMAX=0.7 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3"
# control: identical to lbeam4 (WWMODE=0)
run x ctl_x 44 6 6000 WWMODE=0 BLKWX="$XW" $E &
run y ctl_y 46 6 6000 WWMODE=0 BLKW="$YW" $E &
# treatment: window-width objective
run x ww_x44 44 20 7000 WWMODE=1 BLKWX="$XW" $E &
run x ww_x45 45 20 7000 WWMODE=1 BLKWX="$XW" $E &
run y ww_y45 45 20 7000 WWMODE=1 BLKW="$YW" $E &
run y ww_y46 46 20 7000 WWMODE=1 BLKW="$YW" $E &
wait
echo WW_DONE >> runs/ww.log
