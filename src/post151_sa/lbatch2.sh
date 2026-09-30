#!/bin/bash
cd src/post151_sa
export CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../.. WSPREAD=0.6 SPCAP=4
run() {
  s=$1; fr=$2; a=$3; b=$4; c=$5; sd=$6
  ./c/lbeam2 2000 30 80 $sd 16 0.5 runs/nb_${s}_${a}_${sd}.txt 0.02 $a $b $c < frames/$fr.lb > /dev/null 2>&1 || return 0
  python3 mkbeamD.py frames/$fr.pkl runs/nb_${s}_${a}_${sd}.txt runs/nf_${s}_${a}_${sd}.pkl > /dev/null 2>&1 || return 0
  echo "$s w3=$a seed=$sd rawdepth=$(head -1 runs/nb_${s}_${a}_${sd}.txt)"
}
for sd in 401 402; do
  run x x_star_47_34_21 1 1 1 $sd &
  run x x_star_47_34_21 4 1 1 $sd &
  run y y_46_30_14 1 1 1 $sd &
  run y y_46_30_14 4 1 1 $sd &
  wait
done
echo LBATCHDONE
