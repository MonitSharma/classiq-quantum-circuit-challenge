"""kbeamQ.c + SRDY for rotation firing, but TAU0 stays min(RDY): the beam must start where CX
can begin; rotations with an earlier value-fixed time simply become available at once."""
src = open('kbeamQ.c').read()
a = 'int MODE=0, TBIT=6; int RDY[16], DDL[16], TAU0=0;'
assert src.count(a) == 1
src = src.replace(a, 'int MODE=0, TBIT=6; int RDY[16], DDL[16], SRDY[16], TAU0=0;', 1)
b = 'if(MODE==4){ TAU0=1<<30; for(int i=0;i<N;i++){ int st; if(scanf("%d %d %d",&st,&RDY[i],&DDL[i])!=3) return 1; ST[i]=st; if(RDY[i]<TAU0) TAU0=RDY[i]; }'
assert src.count(b) == 1
b2 = (b + ' if(getenv("SRDY")){ const char*p=getenv("SRDY"); for(int i=0;i<N;i++){ SRDY[i]=atoi(p);'
          ' while(*p && *p!=44) p++; if(*p) p++; } } else for(int i=0;i<N;i++) SRDY[i]=RDY[i];')
src = src.replace(b, b2, 1)
c = 'uint16_t av=0; for(int i=0;i<N;i++) if(RDY[i]<tau && tau<=DDL[i]) av|=1<<i;'
assert src.count(c) == 1
src = src.replace(c, 'uint16_t av=0; for(int i=0;i<N;i++) if(SRDY[i]<tau && tau<=DDL[i]) av|=1<<i;', 1)
open('kbeamT.c','w').write(src)
print('patched -> kbeamT.c')
