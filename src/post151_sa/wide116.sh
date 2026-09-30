#!/bin/bash
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
PY=../../.venv/bin/python
: > runs/wide116.log
for spec in "po_y46_s8.txt 116 s8" "po_yF1_s6.txt 116 s8" "po_y46_s8.txt 115 s8" "po_y46_s8.txt 116 t8"; do
  set -- $spec; YF=$1; T=$2; BIN=$3
  ( $PY -u try6.py champ runs/$YF $T 2>&1 | grep -E 'BUILT|INFEAS|Error' | sed "s|^|[T=$T $YF $BIN] |" >> runs/wide116.log ) &
done
wait
echo WIDE116_DONE >> runs/wide116.log
