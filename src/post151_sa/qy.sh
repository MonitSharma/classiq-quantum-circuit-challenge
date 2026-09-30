#!/bin/bash
cd "$(dirname "$0")"
BLK="32,28,44,24,32,26,34,34,32,30,32,32,30,30,32"
for spec in "lbeam4 45 0" "lbeam4 46 0" "lbeam5 54 45"; do
  set -- $spec; BIN=$1; MD=$2; FZ=$3
  for s in 1 2 3 4; do
    OUT=runs/q_${BIN}_${MD}_${FZ}_${s}
    if [ "$FZ" = "0" ]; then
      env BLKW="$BLK" WFRZ=0 WFT=0.35 WFMAX=0.7 FZMAX=3 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 \
        ./c/$BIN 6000 24 $MD $s 16 0.5 $OUT.txt 0.02 < runs/s118y.lb 2> $OUT.err
    else
      env BLKW="$BLK" FZCAP=$FZ WFRZ=0 WFT=0.35 WFMAX=0.7 FZMAX=3 WREACH2=0.15 NP=18 WSPREAD=0.6 SPCAP=3 \
        ./c/$BIN 6000 24 $MD $s 16 0.5 $OUT.txt 0.02 < runs/s118y.lb 2> $OUT.err
    fi
    echo "$BIN maxd=$MD fzcap=$FZ s=$s rc=$? : $(tail -1 $OUT.err)"
  done
done
