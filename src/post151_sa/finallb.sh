#!/bin/bash
cd src/post151_sa
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../.. WSPREAD=0.6 SPCAP=5
PY=../../.venv/bin/python
one() {  # side frame w3 seed
  s=$1; fr=$2; sd=$3
  ./c/lbeam2 3000 30 80 $sd 16 0.5 runs/fb_${s}_${sd}.txt 0.02 1 1 1 < frames/$fr.lb > /dev/null 2>&1 || return 0
  $PY mkbeamD.py frames/$fr.pkl runs/fb_${s}_${sd}.txt runs/ff_${s}_${sd}.pkl > /dev/null 2>&1 || return 0
  echo "=== $s seed $sd beam $(head -1 runs/fb_${s}_${sd}.txt) ==="
  $PY evalloader.py runs/ff_${s}_${sd}.pkl
  SPANREQ=${3} $PY spanpol2.py runs/ff_${s}_${sd}.pkl runs/fp_${s}_${sd}.pkl $sd 2000000 0.02 0.8 2>&1 | tail -1
  $PY evalloader.py runs/fp_${s}_${sd}.pkl 2>/dev/null
}
export -f one 2>/dev/null
for sd in 501 502; do
  ( ./c/lbeam2 3000 30 80 $sd 16 0.5 runs/fb_x_$sd.txt 0.02 1 1 1 < frames/x_star_47_34_21.lb >/dev/null 2>&1; \
    $PY mkbeamD.py frames/x_star_47_34_21.pkl runs/fb_x_$sd.txt runs/ff_x_$sd.pkl >/dev/null 2>&1; \
    echo "x seed $sd beam $(head -1 runs/fb_x_$sd.txt)"; $PY evalloader.py runs/ff_x_$sd.pkl 2>/dev/null; \
    SPANREQ=48,64,256,384 $PY spanpol2.py runs/ff_x_$sd.pkl runs/fp_x_$sd.pkl $sd 3000000 0.02 0.8 2>&1 | tail -1; \
    $PY evalloader.py runs/fp_x_$sd.pkl 2>/dev/null ) &
  ( ./c/lbeam2 3000 30 80 $sd 16 0.5 runs/fb_y_$sd.txt 0.02 1 1 1 < frames/y_46_30_14.lb >/dev/null 2>&1; \
    $PY mkbeamD.py frames/y_46_30_14.pkl runs/fb_y_$sd.txt runs/ff_y_$sd.pkl >/dev/null 2>&1; \
    echo "y seed $sd beam $(head -1 runs/fb_y_$sd.txt)"; $PY evalloader.py runs/ff_y_$sd.pkl 2>/dev/null; \
    SPANREQ=32,64,128,256 $PY spanpol2.py runs/ff_y_$sd.pkl runs/fp_y_$sd.pkl $sd 3000000 0.02 0.8 2>&1 | tail -1; \
    $PY evalloader.py runs/fp_y_$sd.pkl 2>/dev/null ) &
  wait
done
echo FINALLBDONE
