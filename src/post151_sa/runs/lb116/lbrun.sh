#!/bin/bash
# usage: lbrun.sh side tag maxd W seed WFT WFMAX WREACH2 NP [more env...]
side=$1; tag=$2; md=$3; W=$4; sd=$5; wft=$6; wfm=$7; wr2=$8; np=$9; shift 9
if [ "$side" = y ]; then B=32,28,44,24,32,26,34,34,32,30,32,32,30,30,32; TG=${TGTY:-41,34,99,46,99,99,99,39,99,99,99,99,99,99,99}; else B=14,28,30,40,42,24,30,27,29,33,31,29,31,31,29; TG=${TGTX:-43,35,99,43,99,99,99,43,99,99,99,43,99,99,99}; fi
env SINGLES_PENDING=1 BLKW=$B WFRZ=0 FZMAX=3 NP=$np WSPREAD=0.5 SPCAP=3 CONT=1 TGT=$TG WFT=$wft WFMAX=$wfm WREACH2=$wr2 "$@" timeout ${TL:-160} $HOME/lbeam4c $W 24 $md $sd 16 0.5 ${tag}.txt 0.02 < ../s118${side}.lb 2> ${tag}.err
echo "$tag rc=$? $(grep CONT ${tag}.err | tail -1)"
