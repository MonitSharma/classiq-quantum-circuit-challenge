#!/bin/bash
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
PY=../../.venv/bin/python
: > runs/port8.log
run(){ # side tag binary maxd fzcap nseeds W K wcond wreach wcx env...
  local side=$1 tag=$2 bin=$3 md=$4 fz=$5 ns=$6 W=$7 K=$8 wc_=$9 wr=${10} wcx=${11}
  shift 11
  env "$@" $PY -u lport.py "$side" ./c/$bin $md $fz $ns $W $K $wc_ $wr $wcx $tag 2>&1 \
    | grep --line-buffered -v '^depth' >> runs/port8.log
}
# deeper x loaders: the beam stops at the first depth that works, so maxd 46/48 explores
# ready vectors that a 44-layer loader cannot reach
run x xE1 lbeam4 46 0 20 7000 24 16 0.5 0.02 NOBLKW=1 WFT=0.2  WFMAX=0.4 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
run x xE2 lbeam4 46 0 20 7000 24 16 0.5 0.02 WFT=0.2 WFMAX=0.4 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
run x xE3 lbeam4 48 0 20 7000 24 16 0.5 0.02 WFT=0.3 WFMAX=1.0 WREACH2=0.2 NP=20 WSPREAD=0.5 SPCAP=3 &
run x xE4 lbeam5 54 44 20 6000 24 16 0.5 0.02 WFT=0.3 WFMAX=1.0 WREACH2=0.2 NP=20 WSPREAD=0.5 SPCAP=3 FZCAP=44 &
wait
echo PORT8_DONE >> runs/port8.log
