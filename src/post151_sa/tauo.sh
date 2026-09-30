#!/bin/bash
cd "$(dirname "$0")"
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../..
PY=../../.venv/bin/python
: > runs/tauo.log
# clamp SRDY so TAU0 (=min over RDY and SRDY) sweeps 27..36; the critical wires have s=42/43
for CL in 27 31 33 35 36; do
  ( env SRCLAMP=$CL BEAMBIN=./c/kbeamS8 $PY -u try6.py champ runs/po_y46_s8.txt 116 2>&1 \
      | grep -E 'BUILT|INFEAS|Error' | sed "s|^|[clamp=$CL] |" >> runs/tauo.log ) &
done
wait
echo TAUO_DONE >> runs/tauo.log
