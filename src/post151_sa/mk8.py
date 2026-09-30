# Build lbeam8.c = lbeam7.c + a control-only parity wire.
# PARITYROW=<row value>: no CX may TARGET a wire that currently holds that row.  For y the row is 32
# (py = y5, held by wire 5 from layer 0, so that wire is never targeted at all).  For x the row is 48
# (px = x4^x5): the wire may be targeted until it acquires 48, and never afterwards.
src = open('lbeam7.c').read()
n = 0
def rep(a, b):
    global src, n
    assert a in src, 'MISSING: ' + a[:70]
    src = src.replace(a, b); n += 1

rep("int WWMODE=0;", "int WWMODE=0; int PARITYROW=0;")
rep("  if(getenv(\"WWMODE\")) WWMODE=atoi(getenv(\"WWMODE\"));",
    "  if(getenv(\"WWMODE\")) WWMODE=atoi(getenv(\"WWMODE\"));\n  if(getenv(\"PARITYROW\")) PARITYROW=atoi(getenv(\"PARITYROW\"));")
rep("      for(int t=0;t<NW;t++){ if((fbd>>t&1)||(ps->pend>>t&1)) continue;\n        for(int c=0;c<NW;c++){ if(c==t||(fbd>>c&1)) continue;",
    "      for(int t=0;t<NW;t++){ if((fbd>>t&1)||(ps->pend>>t&1)) continue;\n        if(PARITYROW && ps->r[t]==(unsigned)PARITYROW) continue;\n        for(int c=0;c<NW;c++){ if(c==t||(fbd>>c&1)) continue;")
open('lbeam8.c', 'w').write(src)
print('patched with', n, 'replacements -> lbeam8.c')
