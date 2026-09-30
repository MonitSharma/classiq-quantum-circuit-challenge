#!/bin/bash
# y side: py = y5 is the row of wire 5 from layer 0, so PROTECT_TARGET=32 alone makes it control-only
# (no prefix needed).  Search for a loader that keeps Ly0/Ly2 near champion (34/39) and Ly1 <= 46,
# because the typed window only pays off if the OTHER wires stay fast.
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
export PROTECT_TARGET=32 SINGLES_PENDING=1 FZMAX=3 WSPREAD=0.6 SPCAP=3
: > runs/py9.log
job(){ local tag=$1 md=$2 seed=$3 W=$4 blk=$5 wft=$6
  env BLKW="$blk" WFT=$wft WFMAX=0.7 WREACH2=0.15 NP=18 \
    ./c/lbeam_parity $W 24 $md $seed 16 0.5 runs/po_$tag.txt 0.02 < runs/s118y.lb 2>/dev/null \
    && echo "SOLVED $tag md=$md s=$seed" >> runs/py9.log || echo "  fail $tag" >> runs/py9.log
}
# Ly1=code4 wants LOW weight (freeze last), Ly0=2 and Ly2=8 want HIGH (freeze early); py=1 is free.
B1="1,60,60,1,1,1,1,60,1,1,1,1,1,1,1"
B2="1,100,100,1,1,1,1,100,1,1,1,1,1,1,1"
B3="1,40,40,1,20,1,1,40,1,1,1,1,1,1,1"
for md in 45 46 47; do
  job Q${md}a $md 1 8000 "$B1" 0.35 &
  job Q${md}b $md 2 8000 "$B2" 0.35 &
  job Q${md}c $md 3 8000 "$B3" 0.45 &
done
wait
echo PY9_DONE >> runs/py9.log
