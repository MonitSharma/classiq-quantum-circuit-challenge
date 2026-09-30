#!/bin/bash
# side tag W maxd seed after by [BLKW]
cd $HOME/cw
side=$1; tag=$2; W=$3; md=$4; s=$5; af=$6; by=$7
if [ "$side" = "x" ]; then PR=48; BL=${8:-'14,28,30,40,42,24,30,27,29,33,31,29,31,31,29'}; else PR=32; BL=${8:-'32,28,44,24,32,26,34,34,32,30,32,32,30,30,32'}; fi
PROTECT_TARGET=0 PARITYROW=$PR LOCK_AFTER=$af LOCK_BY=$by WP=${WP:-2} WFRZ=0 WFT=.35 WFMAX=.7 FZMAX=3 WREACH2=.15 NP=18 WSPREAD=.6 SPCAP=3 BLKW=$BL SINGLES_PENDING=1 timeout ${TL:-165} ./lbeam_partial $W 24 $md $s 16 .5 lbo/$tag.txt .02 < s118$side.lb 2> lbo/$tag.err
echo "$tag rc=$?"
