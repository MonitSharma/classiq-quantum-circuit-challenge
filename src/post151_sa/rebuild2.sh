#!/bin/bash
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
PY=../../.venv/bin/python
: > runs/rebuild.log
SEED=$1
echo "=== fresh x support seed $SEED ===" >> runs/rebuild.log
$PY -u gensup.py x 1,2,6 3 $SEED >> runs/rebuild.log 2>&1
for t in 0 1 2; do
  V=runs/gs_x_${SEED}_${t}.pkl
  [ -f "$V" ] || continue
  TAG=rb_${SEED}_${t}
  $PY -u liftD.py $V lx_$TAG 40 >> runs/rebuild.log 2>&1
  [ -f runs/lx_$TAG.pkl ] || { echo "no liftD for $TAG" >> runs/rebuild.log; continue; }
  $PY -u liftc.py runs/lx_$TAG.pkl 2 1200 $SEED >> runs/rebuild.log 2>&1
  [ -f runs/liftc_x_2_par.pkl ] || { echo "no liftc for $TAG" >> runs/rebuild.log; continue; }
  $PY -u mixD.py runs/lx_$TAG.pkl $TAG 2=runs/liftc_x_2_par.pkl >> runs/rebuild.log 2>&1
  [ -f runs/$TAG.lb ] || { echo "no lb for $TAG" >> runs/rebuild.log; continue; }
  echo "--- scheduling $TAG ---" >> runs/rebuild.log
  for md in 44 46; do
    for sd in 1 2 3; do
      env BLKWX="1,1,1,100,1,1,1,1,1,1,1,1,60,1,1" WFRZ=0 WFT=0.35 WFMAX=0.7 FZMAX=3 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 ./c/lbeam4 7000 24 $md $sd 16 0.5 runs/rb_${TAG}_${md}_${sd}.txt 0.02 < runs/$TAG.lb 2>/dev/null && echo "SOLVED $TAG maxd=$md seed=$sd" >> runs/rebuild.log
    done
  done
done
echo REBUILD_DONE >> runs/rebuild.log
