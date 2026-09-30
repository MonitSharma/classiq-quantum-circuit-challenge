// Layered beam search for an 8-wire phase-polynomial kernel.
// stdin: P then P term masks (8-bit). argv: W(beam) maxdepth seed mu out
// Model: layer = disjoint CXs; target of a CX may not carry a pending rotation;
// new undone term on target -> pending; idle wires clear pending. Start rows identity, singles fired at start.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#ifndef N
#define N 8
#endif
typedef struct { uint16_t r[N]; uint16_t pend; uint64_t done; int par; int16_t mv; } S;
int P; uint16_t term[64]; int16_t tidx[65536];
int M; uint8_t mc[40000][5], mt[40000][5], mk[40000];
void genm(int used, int k, uint8_t *cs, uint8_t *ts){
  int a=-1; for(int i=0;i<N;i++) if(!(used>>i&1)){a=i;break;}
  if(a<0){ memcpy(mc[M],cs,5); memcpy(mt[M],ts,5); mk[M]=k; M++; return; }
  // a unused in matching
  genm(used|1<<a,k,cs,ts);
  for(int b=a+1;b<N;b++) if(!(used>>b&1)){
    cs[k]=a; ts[k]=b; genm(used|1<<a|1<<b,k+1,cs,ts);
    cs[k]=b; ts[k]=a; genm(used|1<<a|1<<b,k+1,cs,ts);
  }
}
static inline int popc64(uint64_t x){ return __builtin_popcountll(x); }
double MU; uint64_t ALLDONE;
static uint64_t rs=88172645463325252ull; static inline uint64_t xr(){ rs^=rs<<13; rs^=rs>>7; rs^=rs<<17; return rs; }
int dist(const uint16_t*r){ int d=0; for(int i=0;i<N;i++) d+=__builtin_popcount(r[i])-1; return d; }
double score(const S*s, int depth){
  int dn=popc64(s->done);
  // lookahead: undone terms reachable by one CX (distinct)
  uint64_t reach=0;
  for(int i=0;i<N;i++) for(int j=0;j<N;j++) if(i!=j){ int v=s->r[i]^s->r[j]; int k=tidx[v]; if(k>=0 && !(s->done>>k&1)) reach|=1ull<<k; }
  int h=popc64(reach); if(h>6) h=6;
  double sc=dn*1.0 + 0.3*h;
  sc -= MU*dist(s->r)*(dn/(double)P)*(dn/(double)P);
  return sc + (xr()&1023)/1e6;
}
typedef struct { uint64_t key; double sc; int idx; } HE;
#define HSZ (1<<22)
uint64_t *hkeys; 
uint64_t hstate(const S*s){ uint16_t v[N]; for(int i=0;i<N;i++) v[i]=s->r[i]; // canonical: sort rows with pend
  uint32_t w[N]; for(int i=0;i<N;i++) w[i]=((uint32_t)v[i]<<1)|(s->pend>>i&1);
  for(int i=1;i<N;i++){ uint32_t x=w[i]; int j=i-1; while(j>=0&&w[j]>x){w[j+1]=w[j];j--;} w[j+1]=x; }
  uint64_t h=s->done*0x9E3779B97F4A7C15ull; for(int i=0;i<N;i++){ h^=w[i]; h*=0x100000001B3ull; h^=h>>29; } return h|1; }
int cmpd(const void*a,const void*b){ double x=((HE*)a)->sc, y=((HE*)b)->sc; return x<y?1:x>y?-1:0; }
int MODE=0, TBIT=6;
int endok(const S*s){ if(MODE==0) return dist(s->r)==0; int c=0; for(int i=0;i<N;i++) if(s->r[i]>>TBIT&1) c++; return c==1; }
int main(int argc,char**argv){ if(argc>6){ MODE=atoi(argv[6]); TBIT=atoi(argv[7]); }
  int W=atoi(argv[1]), maxd=atoi(argv[2]); rs^=atoi(argv[3])*0x9E3779B97F4A7C15ull; MU=atof(argv[4]); const char*out=argv[5];
  if(scanf("%d",&P)!=1) return 1; memset(tidx,-1,sizeof tidx);
  for(int i=0;i<P;i++){ int m; scanf("%d",&m); term[i]=m; tidx[m]=i; }
  ALLDONE=(P==64)?~0ull:((1ull<<P)-1);
  uint8_t cs[5],ts[5]; genm(0,0,cs,ts); fprintf(stderr,"matchings %d\n",M);
  // storage per layer
  S **L=malloc(sizeof(S*)*(maxd+1)); int *Ln=calloc(maxd+1,sizeof(int));
  L[0]=malloc(sizeof(S)); S s0; for(int i=0;i<N;i++) s0.r[i]=1<<i; s0.pend=0; s0.done=0; s0.par=-1; s0.mv=-1;
  for(int i=0;i<N;i++){ int k=tidx[1<<i]; if(k>=0) s0.done|=1ull<<k; }
  L[0][0]=s0; Ln[0]=1;
  hkeys=malloc(sizeof(uint64_t)*HSZ);
  int CAP=W*40; S *cand=malloc(sizeof(S)*CAP); HE *he=malloc(sizeof(HE)*CAP);
  int solved=-1, solvedIdx=-1;
  for(int d=1; d<=maxd; d++){
    memset(hkeys,0,sizeof(uint64_t)*HSZ);
    int nc=0; double thr=-1e18; 
    // per-parent keep top K children
    int K=40; S kbuf[64]; double ksc[64];
    for(int p=0;p<Ln[d-1];p++){
      const S*ps=&L[d-1][p]; int kn=0;
      for(int m=0;m<M;m++){
        int ok=1; for(int q=0;q<mk[m];q++) if(ps->pend>>mt[m][q]&1){ok=0;break;} if(!ok) continue;
        S c=*ps; c.par=p; c.mv=m; uint16_t used=0; uint16_t newp=0;
        for(int q=0;q<mk[m];q++){ used|=1<<mc[m][q]|1<<mt[m][q]; }
        for(int q=0;q<mk[m];q++){ int t=mt[m][q]; uint16_t v=ps->r[t]^ps->r[mc[m][q]]; c.r[t]=v; int k=tidx[v]; if(k>=0 && !(c.done>>k&1)){ c.done|=1ull<<k; newp|=1<<t; } }
        c.pend=(ps->pend & used)|newp;
        if(mk[m]==0) continue;
        double sc=score(&c,d);
        if(kn<K){ kbuf[kn]=c; ksc[kn]=sc; kn++; }
        else { int mi=0; for(int i=1;i<K;i++) if(ksc[i]<ksc[mi]) mi=i; if(sc>ksc[mi]){ kbuf[mi]=c; ksc[mi]=sc; } }
      }
      for(int i=0;i<kn;i++){
        uint64_t h=hstate(&kbuf[i]); uint64_t slot=h&(HSZ-1); int dup=0;
        while(hkeys[slot]){ if(hkeys[slot]==h){dup=1;break;} slot=(slot+1)&(HSZ-1); }
        if(dup) continue; hkeys[slot]=h;
        if(nc<CAP){ cand[nc]=kbuf[i]; he[nc].sc=ksc[i]; he[nc].idx=nc; nc++; }
      }
    }
    qsort(he,nc,sizeof(HE),cmpd);
    int keep=nc<W?nc:W; L[d]=malloc(sizeof(S)*keep); Ln[d]=keep;
    int bestdn=0, bestdist=99;
    for(int i=0;i<keep;i++){ L[d][i]=cand[he[i].idx]; int dn=popc64(L[d][i].done); if(dn>bestdn){bestdn=dn;} }
    for(int i=0;i<keep;i++){ if(popc64(L[d][i].done)==P){ int ds=dist(L[d][i].r); if(ds<bestdist) bestdist=ds; if(endok(&L[d][i]) && solved<0){ solved=d; solvedIdx=i; } } }
    fprintf(stderr,"depth %d cand %d best done %d (of %d) complete-dist %d\n",d,nc,bestdn,P,bestdist);
    if(solved>=0) break;
  }
  if(solved<0) return 2;
  // reconstruct
  FILE*f=fopen(out,"w"); int d=solved, idx=solvedIdx; int *mvs=malloc(sizeof(int)*(d+1));
  for(int k=d;k>=1;k--){ mvs[k]=L[k][idx].mv; idx=L[k][idx].par; }
  fprintf(f,"%d\n",d);
  for(int k=1;k<=d;k++){ int m=mvs[k]; fprintf(f,"%d",mk[m]); for(int q=0;q<mk[m];q++) fprintf(f," %d %d",mc[m][q],mt[m][q]); fprintf(f,"\n"); }
  fclose(f); return 0;
}
