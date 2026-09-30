#!/bin/bash
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
PY=../../.venv/bin/python
: > runs/port5.log
run(){ # side tag binary maxd fzcap nseeds W K wcond wreach wcx env...
  local side=$1 tag=$2 bin=$3 md=$4 fz=$5 ns=$6 W=$7 K=$8 wc_=$9 wr=${10} wcx=${11}
  shift 11
  env "$@" $PY -u lport.py "$side" ./c/$bin $md $fz $ns $W $K $wc_ $wr $wcx $tag 2>&1 \
    | grep --line-buffered -v '^depth' >> runs/port5.log
}
run y y45a lbeam4 45 0 20 5000 24 16 0.5 0.02 WFT=0.35 WFMAX=0.7 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
run y y45b lbeam4 45 0 20 5000 24 16 0.5 0.02 WFT=0.15 WFMAX=1.6 WREACH2=0.30 NP=24 WSPREAD=0.3 SPCAP=2 &
run y y45c lbeam4 45 0 20 7000 24 16 0.5 0.02 WFT=0.5  WFMAX=0.4 WREACH2=0.05 NP=14 WSPREAD=1.0 SPCAP=4 &
run y y45d lbeam4 45 0 20 5000 24 16 0.5 0.02 WFT=0.25 WFMAX=1.1 WREACH2=0.22 NP=20 WSPREAD=0.45 SPCAP=3 &
run y y45e lbeam4 45 0 20 9000 24 16 0.5 0.02 WFT=0.60 WFMAX=1.0 WREACH2=0.10 NP=16 WSPREAD=0.8 SPCAP=4 &
run x x44a lbeam4 44 0 20 6000 24 16 0.5 0.02 WFT=0.35 WFMAX=0.7 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
run x x44b lbeam4 44 0 20 5000 24 16 0.5 0.02 WFT=0.15 WFMAX=1.6 WREACH2=0.30 NP=24 WSPREAD=0.3 SPCAP=2 &
wait
echo PORT5_DONE >> runs/port5.log
