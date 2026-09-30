#!/bin/bash
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
PY=../../.venv/bin/python
: > runs/pullscan.log
for T in 116 115; do
  for pair in "champ runs/po_yF1_s6.txt" "champ runs/po_y46_s8.txt" "champ runs/po_y45a_s17.txt" "champ runs/po_yD1_s17.txt" "runs/po_xE4_s2.txt runs/po_yF1_s6.txt"; do
    set -- $pair
    ( $PY -u try6.py "$1" "$2" $T 2>&1 | grep -E 'BUILT|INFEAS|Error' | sed "s|^|T=$T $1+$2: |" >> runs/pullscan.log ) &
  done
  wait
done
echo PULLSCAN_DONE >> runs/pullscan.log
