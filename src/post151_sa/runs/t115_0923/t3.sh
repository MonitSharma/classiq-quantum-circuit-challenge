#!/bin/bash
# tag T seed W RDY SRDY VFctrl(8)  ; rotations [SRDY, T-rdy], controls [VF, T-VF], targets [rdy, T-rdy]
tag=$1; T=$2; s=$3; W=$4; RDY=$5; SR=$6; VF=$7
python3 - "$T" "$RDY" "$SR" "$VF" "$tag" <<'PY'
import sys,subprocess
T=int(sys.argv[1]); r=list(map(int,sys.argv[2].split(','))); sr=list(map(int,sys.argv[3].split(','))); vf=list(map(int,sys.argv[4].split(','))); tag=sys.argv[5]
zd=[T-x for x in r]; cd=[T-v for v in vf]; xd=[T-x for x in r]
dd=[max(a,b) for a,b in zip(zd,cd)]
subprocess.run(['python3','whatif2.py','champ',','.join(map(str,r)),','.join(map(str,dd)),tag+'.in'])
j=lambda v:','.join(map(str,v))
open(tag+'.env','w').write(f'ZS={j(sr)} ZD={j(zd)} XS={j(r)} XD={j(xd)} CS={j(vf)} CD={j(cd)}')
PY
env SINGLES_PENDING=1 TOUCHBAD=1 LAW=0.3 $(cat $tag.env) timeout 170 ./kbeam_t3 $W 100 $s 0.02 $tag.out 4 0 < $tag.in > /dev/null 2> $tag.err
echo "$tag T=$T s=$s rc=$?"
