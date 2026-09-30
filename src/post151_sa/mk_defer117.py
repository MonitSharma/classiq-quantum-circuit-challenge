from pathlib import Path
p=Path(__file__).parent;s=(p/'kbeam_wirehash.c').read_text()
s=s.replace('int ok=1; for(int q=0;q<mk[m];q++) if(ps->pend>>mt[m][q]&1){ok=0;break;} if(!ok) continue;', 'int ok=1;')
s=s.replace('S c=*ps; c.par=p; c.mv=m; uint16_t used=0; uint16_t newp=0;', '''S c=*ps; c.par=p; c.mv=m; uint16_t used=0; uint16_t newp=0;
        uint16_t oldpend=ps->pend;
        // Visiting a parity need not commit us to emitting it here. A target
        // can abandon its pending phase and regenerate that parity later.
        for(int q=0;q<mk[m];q++){int t=mt[m][q]; if(oldpend>>t&1){int z=tidx[ps->r[t]]; if(z>=0)c.done&=~(1ull<<z);oldpend&=~(1u<<t);}}
''')
s=s.replace('ps->pend & (uint16_t)~used', 'oldpend & (uint16_t)~used').replace('(ps->pend & (used|', '(oldpend & (used|').replace('(ps->pend & used)|newp','(oldpend & used)|newp')
s=s.replace('return sc + (xr()&1023)', 'sc -= 0.1*__builtin_popcount(s->pend); return sc + (xr()&1023)')
(p/'kbeam_defer.c').write_text(s)
