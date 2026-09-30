src = open('kbeamQ.c').read()
a = 'int MODE=0, TBIT=6; int RDY[16], DDL[16], TAU0=0;'
assert src.count(a) == 1
src = src.replace(a, 'int MODE=0, TBIT=6; int RDY[16], DDL[16], SRDY[16], TAU0=0;', 1)
b = 'if(MODE==4){ TAU0=1<<30; for(int i=0;i<N;i++){ int st; if(scanf("%d %d %d",&st,&RDY[i],&DDL[i])!=3) return 1; ST[i]=st; if(RDY[i]<TAU0) TAU0=RDY[i]; }'
assert src.count(b) == 1
b2 = ('if(MODE==4){ TAU0=1<<30; for(int i=0;i<N;i++){ int st; if(scanf("%d %d %d",&st,&RDY[i],&DDL[i])!=3) return 1; ST[i]=st;'
      ' SRDY[i]=RDY[i]; if(RDY[i]<TAU0) TAU0=RDY[i]; }'
      ' if(getenv("SRDY")){ const char*p=getenv("SRDY"); for(int i=0;i<N;i++){ SRDY[i]=atoi(p); while(*p && *p!=44) p++; if(*p) p++;'
      ' if(SRDY[i]<TAU0) TAU0=SRDY[i]; } }')
src = src.replace(b, b2, 1)
c = 'uint16_t av=0; for(int i=0;i<N;i++) if(RDY[i]<tau && tau<=DDL[i]) av|=1<<i;'
assert src.count(c) == 1
src = src.replace(c, 'uint16_t av=0; for(int i=0;i<N;i++) if(SRDY[i]<tau && tau<=DDL[i]) av|=1<<i;', 1)
open('kbeamS.c','w').write(src)
print('patched -> kbeamS.c')
