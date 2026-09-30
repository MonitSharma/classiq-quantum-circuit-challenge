#!/bin/bash
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
PY=../../.venv/bin/python
: > runs/shape.log
run(){ local side=$1 tag=$2 md=$3 ns=$4 W=$5; shift 5
  env "$@" $PY -u lport.py $side ./c/lbeam4 $md 0 $ns $W 24 16 0.5 0.02 $tag 2>&1 \
    | grep --line-buffered -v '^depth' >> runs/shape.log; }
# y target shape: Ly0(2), py(1), Ly2(8) EARLY; Ly1(4) LATE   (indices 1..15)
YSHAPE="60,60,1,1,1,1,1,60,1,1,1,1,1,1,1"
# x target shape: Lx0(2), Lx1(4), Lx2(12) EARLY; px(1) LATE
XSHAPE="1,60,60,1,1,1,1,1,1,1,1,60,1,1,1"
E="WFT=0.35 WFMAX=0.7 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3"
run y Ys45a 45 24 8000 BLKWX="$YSHAPE" $E &
run y Ys45b 45 24 8000 BLKWX="$YSHAPE" WFT=0.2 WFMAX=1.2 WREACH2=0.25 NP=22 WSPREAD=0.4 SPCAP=2 &
run y Ys46a 46 24 8000 BLKWX="$YSHAPE" $E &
run x Xs44a 44 24 8000 BLKWX="$XSHAPE" $E &
run x Xs44b 44 24 8000 BLKWX="$XSHAPE" WFT=0.2 WFMAX=1.2 WREACH2=0.25 NP=22 WSPREAD=0.4 SPCAP=2 &
run x Xs45a 45 24 8000 BLKWX="$XSHAPE" $E &
wait
echo SHAPE_DONE >> runs/shape.log
