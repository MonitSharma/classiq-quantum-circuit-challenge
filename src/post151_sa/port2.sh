#!/bin/bash
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
PY=../../.venv/bin/python
# y side: several weight profiles at depth 46, plus depth 47 with FZCAP 46
run(){ # tag binary maxd fzcap nseeds W K wcond wreach wcx env...
  local tag=$1 bin=$2 md=$3 fz=$4 ns=$5 W=$6 K=$7 wc_=$8 wr=$9 wcx=10
  shift 10
  env "$@" $PY -u lport.py "${tag%%_*}" ./c/$bin $md $fz $ns $W $K $wc_ $wr $wcx $tag 2>&1 \
    | grep --line-buffered -v '^depth' >> runs/port2.log
}
: > runs/port2.log
run y46a  lbeam4 46 0  16 5000 24 16 0.5 0.02 WFT=0.35 WFMAX=0.7 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
run y46b  lbeam4 46 0  16 5000 24 16 0.5 0.02 WFT=0.15 WFMAX=1.6 WREACH2=0.30 NP=24 WSPREAD=0.3 SPCAP=2 &
run y46c  lbeam4 46 0  16 8000 24 16 0.5 0.02 WFT=0.5  WFMAX=0.4 WREACH2=0.05 NP=14 WSPREAD=1.0 SPCAP=4 &
run y47   lbeam5 50 46 12 5000 24 16 0.5 0.02 WFT=0.35 WFMAX=0.7 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 FZCAP=46 &
run x44a  lbeam4 44 0  16 5000 24 16 0.5 0.02 WFT=0.35 WFMAX=0.7 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
run x44b  lbeam4 44 0  16 5000 24 16 0.5 0.02 WFT=0.15 WFMAX=1.6 WREACH2=0.30 NP=24 WSPREAD=0.3 SPCAP=2 &
wait
echo PORT2_DONE
