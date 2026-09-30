#!/bin/bash
# The prefix+protect construction costs one target wire for the whole loader, so it needs more depth.
# Sweep maxd 46..50 and keep every valid loader so they can be screened on the NON-parity readies.
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
export PROTECT_TARGET=32 SINGLES_PENDING=1 PREFIX=runs/parity_0923/px_prefix.txt PREFIXK=1
export WFRZ=0 WFT=0.35 WFMAX=0.7 FZMAX=3 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3
: > runs/px3.log
PY=../../.venv/bin/python
job(){ local md=$1 seed=$2 W=$3 blk=$4
  local tag=Pz${md}_${seed}
  BLKWX="$blk" ./c/lbeam_parity $W 24 $md $seed 16 0.5 runs/po_$tag.txt 0.02 < runs/s118x.lb 2>/dev/null \
    && echo "SOLVED $tag" >> runs/px3.log || echo "  fail $tag" >> runs/px3.log
}
for md in 46 47 48; do for s in 1 2 3; do
  job $md $s 8000 "1,1,50,1,50,1,1,1,1,1,1,50,1,1,1" &
done; done
for md in 49 50; do for s in 1 2; do
  job $md $s 8000 "1,60,60,1,60,1,1,1,1,1,1,60,1,1,1" &
done; done
wait
echo PX3_DONE >> runs/px3.log
