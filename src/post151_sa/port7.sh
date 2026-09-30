#!/bin/bash
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
PY=../../.venv/bin/python
: > runs/port7.log
run(){ # side tag binary maxd fzcap nseeds W K wcond wreach wcx env...
  local side=$1 tag=$2 bin=$3 md=$4 fz=$5 ns=$6 W=$7 K=$8 wc_=$9 wr=${10} wcx=${11}
  shift 11
  env "$@" $PY -u lport.py "$side" ./c/$bin $md $fz $ns $W $K $wc_ $wr $wcx $tag 2>&1 \
    | grep --line-buffered -v '^depth' >> runs/port7.log
}
# x: the champion's own recipe (no BLKW, WFT=0.2 WFMAX=0.4) plus variations
run x xD1 lbeam4 44 0 24 7000 24 16 0.5 0.02 NOBLKW=1 WFT=0.2  WFMAX=0.4 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
run x xD2 lbeam4 44 0 24 7000 24 16 0.5 0.02 NOBLKW=1 WFT=0.35 WFMAX=0.9 WREACH2=0.20 NP=20 WSPREAD=0.5 SPCAP=3 &
run x xD3 lbeam4 44 0 24 9000 24 16 0.5 0.02 NOBLKW=1 WFT=0.1  WFMAX=1.4 WREACH2=0.30 NP=24 WSPREAD=0.3 SPCAP=2 &
run x xD4 lbeam4 43 0 24 7000 24 16 0.5 0.02 NOBLKW=1 WFT=0.2  WFMAX=0.4 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
run y yD1 lbeam4 45 0 24 7000 24 16 0.5 0.02 NOBLKW=1 WFT=0.2  WFMAX=0.4 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
run y yD2 lbeam4 45 0 24 7000 24 16 0.5 0.02 WFT=0.2 WFMAX=0.4 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
run y yD3 lbeam4 45 0 24 7000 24 16 0.5 0.02 WFT=0.3 WFMAX=1.2 WREACH2=0.25 NP=22 WSPREAD=0.4 SPCAP=2 &
wait
echo PORT7_DONE >> runs/port7.log
