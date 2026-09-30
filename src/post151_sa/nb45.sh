#!/bin/bash
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
PY=../../.venv/bin/python
: > runs/nb45.log
one(){ # side maxd seed blkmode W K wcond wreach
  local side=$1 md=$2 sd=$3 blk=$4 W=$5 K=$6 wc_=$7 wr=$8
  local out=runs/nb_${side}_${md}_${blk}_${W}_${sd}
  local ENV="WFRZ=0 WFT=0.35 WFMAX=0.7 FZMAX=3 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3"
  if [ "$blk" = "blk" ]; then
    if [ "$side" = "y" ]; then ENV="$ENV BLKW=32,28,44,24,32,26,34,34,32,30,32,32,30,30,32"
    else ENV="$ENV BLKW=14,28,30,40,42,24,30,27,29,33,31,29,31,31,29"; fi
  fi
  env $ENV ./c/lbeam4 $W $K $md $sd $wc_ $wr $out.txt 0.02 < runs/s118$side.lb 2> $out.err
  local rc=$?
  echo "side=$side maxd=$md blk=$blk W=$W s=$sd rc=$rc $(tail -1 $out.err | cut -c1-110)"
}
export -f one 2>/dev/null
for md in 45; do
  for blk in noblk blk; do
    for W in 5000 9000; do
      for sd in 1 2 3 4 5 6 7 8; do one y $md $sd $blk $W 24 16 0.5 & done
    done
    wait
  done
done
echo NB45_DONE
