#!/bin/bash
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
PY=../../.venv/bin/python
: > runs/port10.log
run(){ local side=$1 tag=$2 bin=$3 md=$4 fz=$5 ns=$6 W=$7 K=$8 wc_=$9 wr=${10} wcx=${11}; shift 11
  env "$@" $PY -u lport.py "$side" ./c/$bin $md $fz $ns $W $K $wc_ $wr $wcx $tag 2>&1 \
    | grep --line-buffered -v '^depth' >> runs/port10.log; }
# y at 46 with heavy WFMAX: we want ready max <= 45 or a better spread
run y yF1 lbeam4 46 0 22 7000 24 16 0.5 0.02 WFT=0.15 WFMAX=2.2 WREACH2=0.2 NP=20 WSPREAD=0.5 SPCAP=3 &
run y yF2 lbeam4 46 0 22 7000 24 16 0.5 0.02 WFT=0.10 WFMAX=3.0 WREACH2=0.3 NP=24 WSPREAD=0.3 SPCAP=2 &
run y yF3 lbeam4 45 0 22 7000 24 16 0.5 0.02 WFT=0.10 WFMAX=3.0 WREACH2=0.3 NP=24 WSPREAD=0.3 SPCAP=2 &
run y yF4 lbeam4 45 0 22 8000 24 16 0.5 0.02 WFT=0.3  WFMAX=1.4 WREACH2=0.25 NP=22 WSPREAD=0.4 SPCAP=2 &
run y yF5 lbeam4 44 0 22 8000 24 16 0.5 0.02 WFT=0.2  WFMAX=0.4 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
wait
echo PORT10_DONE >> runs/port10.log
