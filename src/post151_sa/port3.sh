#!/bin/bash
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
PY=../../.venv/bin/python
: > runs/port2.log
run(){ # side tag binary maxd fzcap nseeds W K wcond wreach wcx env...
  local side=$1 tag=$2 bin=$3 md=$4 fz=$5 ns=$6 W=$7 K=$8 wc_=$9 wr=${10} wcx=${11}
  shift 11
  env "$@" $PY -u lport.py "$side" ./c/$bin $md $fz $ns $W $K $wc_ $wr $wcx $tag 2>&1 \
    | grep --line-buffered -v '^depth' >> runs/port2.log
}
run y y46a lbeam4 46 0  16 5000 24 16 0.5 0.02 WFT=0.35 WFMAX=0.7 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
run y y46b lbeam4 46 0  16 5000 24 16 0.5 0.02 WFT=0.15 WFMAX=1.6 WREACH2=0.30 NP=24 WSPREAD=0.3 SPCAP=2 &
run y y46c lbeam4 46 0  16 8000 24 16 0.5 0.02 WFT=0.5  WFMAX=0.4 WREACH2=0.05 NP=14 WSPREAD=1.0 SPCAP=4 &
run y y47  lbeam5 50 46 12 5000 24 16 0.5 0.02 WFT=0.35 WFMAX=0.7 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 FZCAP=46 &
run x x44a lbeam4 44 0  16 5000 24 16 0.5 0.02 WFT=0.35 WFMAX=0.7 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
run x x44b lbeam4 44 0  16 5000 24 16 0.5 0.02 WFT=0.15 WFMAX=1.6 WREACH2=0.30 NP=24 WSPREAD=0.3 SPCAP=2 &
wait
echo PORT2_DONE >> runs/port2.log
