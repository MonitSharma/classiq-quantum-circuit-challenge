#!/bin/bash
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
PY=../../.venv/bin/python
: > runs/liftbig.log
for tgt in 1 2; do
  for seed in 3 5 7 11 13 17 19 23; do
    ( $PY -u liftc.py runs/s118x.pkl $tgt 6000 $seed 2>&1 | grep -E 'support|best' | sed "s|^|[x t$tgt s$seed] |" >> runs/liftbig.log ) &
  done
  wait
done
echo LIFTBIG_DONE >> runs/liftbig.log
