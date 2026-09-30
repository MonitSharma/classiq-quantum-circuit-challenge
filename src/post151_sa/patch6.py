src = open('lbeam5.c').read()
src = src.replace('int CLOPT=0; int FZCAP=1000;', 'int CLOPT=0; int FZCAP=1000; int FZCAPS[16]={0};', 1)
old = '    if(c->lt[w]>FZCAP) continue;'
assert src.count(old) == 1
new = ('    { int cap=FZCAP; unsigned cc=spcode[v]; if(cc<16 && FZCAPS[cc]>0) cap=FZCAPS[cc];\n'
       '      if(c->lt[w]>cap) continue; }')
src = src.replace(old, new, 1)
old2 = '  if(getenv("FZCAP")) FZCAP=atoi(getenv("FZCAP"));'
assert src.count(old2) == 1
add = old2 + ('\n  if(getenv("FZCAPS")){ const char*p=getenv("FZCAPS"); for(int i=0;i<16;i++){ FZCAPS[i]=atoi(p);'
              ' while(*p && *p!=44) p++; if(*p) p++; } }')
src = src.replace(old2, add, 1)
open('lbeam6.c','w').write(src)
print('patched -> lbeam6.c')
