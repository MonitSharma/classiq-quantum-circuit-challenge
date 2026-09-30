import re
src=open('lbeam4.c').read()
# 1. new global for the freeze deadline
src=src.replace('double WREACH, WREACH2=0, WCOND, WCX=0; int CLOPT=0;',
                'double WREACH, WREACH2=0, WCOND, WCX=0; int CLOPT=0; int FZCAP=1000;',1)
# 2. refuse to freeze a wire whose last touch is later than FZCAP
old='    unsigned v=c->r[w]; if(!inspan[v]) continue; FZIN++;'
assert src.count(old)==1
src=src.replace(old, old+'\n    if(c->lt[w]>FZCAP) continue;',1)
# 3. env
old2='  if(getenv("FZMINCL")) FZMINCL=atoi(getenv("FZMINCL"));'
assert src.count(old2)==1
src=src.replace(old2, old2+'\n  if(getenv("FZCAP")) FZCAP=atoi(getenv("FZCAP"));',1)
open('lbeam5.c','w').write(src)
print('patched -> lbeam5.c')
