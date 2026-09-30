#!/bin/bash
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
PY=../../.venv/bin/python
: > runs/port11.log
run(){ local side=$1 tag=$2 bin=$3 md=$4 fz=$5 ns=$6 W=$7 K=$8 wc_=$9 wr=${10} wcx=${11}; shift 11
  env "$@" $PY -u lport.py "$side" ./c/$bin $md $fz $ns $W $K $wc_ $wr $wcx $tag 2>&1 \
    | grep --line-buffered -v '^depth' >> runs/port11.log; }
# y: want ready(Ly0=code2)<=38, ready(Ly2=code8)<=41, ready(py=code1)<=42, ready(Ly1=code4)<=45
YCAPS="0,42,38,45,45,45,45,45,41,45,45,45,45,45,45,45"
# x: want ready(Lx0=code2)<=38, ready(Lx1=code4)<=43, ready(px=code1)<=45, ready(Lx2=code12)<=43
XCAPS="0,45,38,45,43,45,45,45,45,45,45,45,43,45,45,45"
run y yG1 lbeam6 52 45 24 7000 24 16 0.5 0.02 FZCAP=45 FZCAPS="$YCAPS" BLKW=32,28,44,24,32,26,34,34,32,30,32,32,30,30,32 WFT=0.35 WFMAX=0.7 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
run y yG2 lbeam6 52 45 24 7000 24 16 0.5 0.02 FZCAP=45 FZCAPS="$YCAPS" NOBLKW=1 WFT=0.35 WFMAX=0.7 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
run y yG3 lbeam6 52 45 24 9000 24 16 0.5 0.02 FZCAP=45 FZCAPS="$YCAPS" BLKW=32,28,44,24,32,26,34,34,32,30,32,32,30,30,32 WFT=0.15 WFMAX=1.6 WREACH2=0.3 NP=24 WSPREAD=0.3 SPCAP=2 &
run x xG1 lbeam6 50 44 24 7000 24 16 0.5 0.02 FZCAP=44 FZCAPS="$XCAPS" BLKWX=14,28,30,40,42,24,30,27,29,33,31,29,31,31,29 WFT=0.2 WFMAX=0.4 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
run x xG2 lbeam6 50 44 24 7000 24 16 0.5 0.02 FZCAP=44 FZCAPS="$XCAPS" NOBLKW=1 WFT=0.2 WFMAX=0.4 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 &
wait
echo PORT11_DONE >> runs/port11.log
