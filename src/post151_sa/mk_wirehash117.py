from pathlib import Path
p=Path(__file__).parent
s=(p/'kbeamVn.c').read_text()
a=s.index('  for(int i=1;i<N;i++){ uint32_t x=w[i];')
b=s.index('  uint64_t h=s->done',a)
s=s[:a]+'''  // A row on wire i is not interchangeable with a row on wire j:
  // ready times, deadlines, home rows, and pending rotations are wire-specific.
  // Retain the historical quotient only in fully symmetric modes 0/1.
  if(MODE==0 || MODE==1) for(int i=1;i<N;i++){ uint32_t x=w[i]; int j=i-1; while(j>=0&&w[j]>x){w[j+1]=w[j];j--;} w[j+1]=x; }
'''+s[b:]
s=s.replace('h^=w[i]; h*=', 'h^=w[i]; if(HAVECAP) h^=(uint64_t)s->cnt[i]<<24; h*=')
(p/'kbeam_wirehash.c').write_text(s)
