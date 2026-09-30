# Build lbeam7.c = lbeam4.c + first-touch tracking + a window-width scoring mode (WWMODE=1).
# Rationale: T >= (rdy_w - first_w) + touches_w + D_side + 1, so the loader should minimise the WIDTH of
# each code wire's touch window, not its freeze time.  WWMODE=0 reproduces lbeam4 exactly.
import re, sys
src = open('lbeam4.c').read()
n = 0
def rep(a, b):
    global src, n
    assert a in src, 'MISSING: ' + a[:60]
    src = src.replace(a, b); n += 1

# 1. state: per-wire first-touch layer
rep("uint8_t lt[NW]; uint16_t froz;", "uint8_t lt[NW]; uint8_t ft[NW]; uint16_t froz;")

# 2. global switch + env parsing
rep("double BLKW[16]={0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1}; double BLKTOT=4.0; int USEBLK=0;",
    "double BLKW[16]={0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1}; double BLKTOT=4.0; int USEBLK=0; int WWMODE=0;")

# 3. record the first touch at every touch site
rep("for(int w=0;w<NW;w++) if(touched>>w&1) c.lt[w]=k;",
    "for(int w=0;w<NW;w++) if(touched>>w&1){ if(!c.ft[w]) c.ft[w]=k; c.lt[w]=k; }")
src = src.replace("for(int w=0;w<NW;w++) if(touched>>w&1) c.lt[w]=d;",
                  "for(int w=0;w<NW;w++) if(touched>>w&1){ if(!c.ft[w]) c.ft[w]=d; c.lt[w]=d; }")
n += src.count("if(!c.ft[w]) c.ft[w]=d;")

# 4. score the WINDOW WIDTH instead of the freeze time when WWMODE
rep("    c2.fsum+=c2.lt[w]; if(c2.lt[w]>c2.fmax) c2.fmax=c2.lt[w];\n    c2.fw+=(float)(BLKW[spcode[c->r[w]]]*c2.lt[w]); c2.wused+=(float)BLKW[spcode[c->r[w]]];",
    "    { int fv = WWMODE ? (c2.lt[w]-(c2.ft[w]?c2.ft[w]:c2.lt[w])) : c2.lt[w];\n      c2.fsum+=fv; if(fv>c2.fmax) c2.fmax=fv;\n      c2.fw+=(float)(BLKW[spcode[c->r[w]]]*fv); }\n    c2.wused+=(float)BLKW[spcode[c->r[w]]];")
rep("      c3.fsum+=c3.lt[w2]; if(c3.lt[w2]>c3.fmax) c3.fmax=c3.lt[w2];\n      c3.fw+=(float)(BLKW[spcode[c2.r[w2]]]*c3.lt[w2]); c3.wused+=(float)BLKW[spcode[c2.r[w2]]];",
    "      { int fv = WWMODE ? (c3.lt[w2]-(c3.ft[w2]?c3.ft[w2]:c3.lt[w2])) : c3.lt[w2];\n        c3.fsum+=fv; if(fv>c3.fmax) c3.fmax=fv;\n        c3.fw+=(float)(BLKW[spcode[c2.r[w2]]]*fv); }\n      c3.wused+=(float)BLKW[spcode[c2.r[w2]]];")

# 5. env knob
rep('if(getenv("WFT")) WFT=atof(getenv("WFT"));',
    'if(getenv("WFT")) WFT=atof(getenv("WFT"));\n  if(getenv("WWMODE")) WWMODE=atoi(getenv("WWMODE"));')

open('lbeam7.c', 'w').write(src)
print('patched with', n, 'replacements -> lbeam7.c')
