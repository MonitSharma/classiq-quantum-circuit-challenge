#!/bin/bash
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
PY=../../.venv/bin/python
: > runs/port9.log
run(){ # side tag binary maxd fzcap nseeds W K wcond wreach wcx env...
  local side=$1 tag=$2 bin=$3 md=$4 fz=$5 ns=$6 W=$7 K=$8 wc_=$9 wr=${10} wcx=${11}
  shift 11
  env "$@" $PY -u lport.py "$side" ./c/$bin $md $fz $ns $W $K $wc_ $wr $wcx $tag 2>&1 \
    | grep --line-buffered -v '^depth' >> runs/port9.log
}
PXLAST="1,28,30,40,42,24,30,27,29,33,31,29,31,31,29"
PXSTRONG="1,40,42,40,24,30,27,40,29,33,31,40,31,31,29"
BASE="WFT=0.2 WFMAX=0.4 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3"
# the goal: a 43-layer x loader (all four ready <= 43 -> worst case 2*43+30 = 116)
run x x43a lbeam4 43 0 22 7000 24 16 0.5 0.02 BLKWX="$PXLAST"   $BASE &
run x x43b lbeam4 43 0 22 7000 24 16 0.5 0.02 NOBLKW=1            $BASE &
run x x43c lbeam4 43 0 22 9000 24 16 0.5 0.02 BLKWX="$PXSTRONG" $BASE &
run x x44p lbeam4 44 0 22 7000 24 16 0.5 0.02 BLKWX="$PXSTRONG" $BASE &
run x x44q lbeam4 44 0 22 7000 24 16 0.5 0.02 BLKWX="$PXLAST"   WFT=0.35 WFMAX=0.9 WREACH2=0.2 NP=20 WSPREAD=0.5 SPCAP=3 &
run x x45p lbeam4 45 0 22 7000 24 16 0.5 0.02 BLKWX="$PXSTRONG" $BASE &
wait
echo PORT9_DONE >> runs/port9.log
