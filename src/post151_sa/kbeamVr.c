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
typedef struct { uint16_t r[N]; uint16_t pend; uint64_t done; int par; int16_t mv; uint8_t last[N]; uint8_t cnt[N]; uint16_t ncx; } S;
double CXPEN=0, NOISE=0, LAW=0.3; unsigned NOTGT=0; int NOTGT_AFTER=0; int PFK=0; int PFN[128]; int PFC[128][5], PFT[128][5]; int PFTAU0=0;
int TCAP[16]; int HAVECAP=0; int TYPED=0, ZS[16],XS[16],ZD[16],XD[16], HAVECTRL=0, HAVETB=0;
static void rdlist(const char*nm,int*a){ const char*p=getenv(nm); for(int i=0;i<N;i++){ a[i]=atoi(p); while(*p && *p!=44) p++; if(*p) p++; } }
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
int MODE=0, TBIT=6; int RDY[16], DDL[16], SRDY[16], CRDY[16], TAU0=0; uint16_t ST[16]; unsigned PERMA=0; int LA=0; int DDLE[16];
static inline int inSTA(uint16_t v){ for(int j=0;j<16;j++) if((PERMA>>j&1) && ST[j]==v) return 1; return 0; }
int RDIST=0;
static int rdist(const uint16_t*r){
  // representation weight of home vectors ST_i in the basis of current rows: popcount of off-diagonal of M=ST*A^{-1}
  uint32_t a[N]; for(int i=0;i<N;i++) a[i]=((uint32_t)r[i]&0xFF)|(1u<<(8+i));
  for(int c=0;c<8;c++){ int p=-1; for(int i=c;i<N;i++) if(a[i]>>c&1){p=i;break;} if(p<0) return 64; uint32_t t=a[p]; a[p]=a[c]; a[c]=t; for(int i=0;i<N;i++) if(i!=c && (a[i]>>c&1)) a[i]^=a[c]; }
  // now a[c] has bit c set in low part and high part = combination of original rows giving unit vector e_c: e_c = sum_{j in hi(a[c])} r_j
  int w=0;
  for(int i=0;i<N;i++){ uint32_t comb=0; uint16_t v=ST[i]; for(int c=0;c<8;c++) if(v>>c&1) comb^=a[c]>>8; comb&=~(1u<<i); w+=__builtin_popcount(comb); if(!((ST[i]==r[i]))&&comb==0) w+=0; }
  return w; }
int dist(const uint16_t*r){ int d=0; if(RDIST && MODE==4 && !PERMA) return rdist(r); if(MODE==4){ for(int i=0;i<N;i++){ if(PERMA>>i&1){ int b=99; for(int j=0;j<N;j++) if(PERMA>>j&1){ int x=__builtin_popcount(r[i]^ST[j]); if(x<b) b=x; } d+=b; } else d+=__builtin_popcount(r[i]^ST[i]); } return d; } if(MODE==2||MODE==3){ for(int i=0;i<N;i++) d+=__builtin_popcount(r[i]^(1u<<i)); return d; } for(int i=0;i<N;i++) d+=__builtin_popcount(r[i])-1; return d; }
uint64_t LATESET=0; double LATEW=0; double WDL=0;
double score(const S*s, int depth){
  int dn=popc64(s->done);
  // lookahead: undone terms reachable by one CX (distinct)
  uint64_t reach=0;
  for(int i=0;i<N;i++) for(int j=0;j<N;j++) if(i!=j){ int v=s->r[i]^s->r[j]; int k=tidx[v]; if(k>=0 && !(s->done>>k&1)) reach|=1ull<<k; }
  int h=popc64(reach); if(h>6) h=6;
  double sc=dn*1.0 + LAW*h + LATEW*popc64(s->done & LATESET);
  if(WDL>0 && (MODE==3||MODE==4)){ int tau=TAU0+depth; for(int i=0;i<N;i++){ uint16_t home=(MODE==4)?ST[i]:(1u<<i); int slack=DDL[i]-tau; int need=__builtin_popcount(s->r[i]^home); if(need>0 && slack<4*need) sc-=WDL*(4*need-slack); } }
  sc -= MU*dist(s->r)*(dn/(double)P)*(dn/(double)P);
  sc -= CXPEN*s->ncx;
  return sc + (xr()&1023)/1e6 + (NOISE>0 ? NOISE*((xr()&0xFFFF)/65536.0) : 0);
}
typedef struct { uint64_t key; double sc; int idx; } HE;
#define HSZ (1<<22)
uint64_t *hkeys; 
uint64_t hstate(const S*s){ uint16_t v[N]; for(int i=0;i<N;i++) v[i]=s->r[i]; // canonical: sort rows with pend
  uint32_t w[N]; for(int i=0;i<N;i++) w[i]=((uint32_t)v[i]<<1)|(s->pend>>i&1);
  for(int i=1;i<N;i++){ uint32_t x=w[i]; int j=i-1; while(j>=0&&w[j]>x){w[j+1]=w[j];j--;} w[j+1]=x; }
  uint64_t h=s->done*0x9E3779B97F4A7C15ull; for(int i=0;i<N;i++){ h^=w[i]; h*=0x100000001B3ull; h^=h>>29; } return h|1; }
int cmpd(const void*a,const void*b){ double x=((HE*)a)->sc, y=((HE*)b)->sc; return x<y?1:x>y?-1:0; }
int endok(const S*s){
  if(MODE==4 && PERMA){ if(s->pend) return 0; uint16_t used=0; for(int i=0;i<N;i++){ if(!(PERMA>>i&1)){ if(s->r[i]!=ST[i]) return 0; continue; } int ok=0; for(int j=0;j<N;j++) if((PERMA>>j&1) && !(used>>j&1) && ST[j]==s->r[i] && TAU0+s->last[i]<=DDL[j]){ used|=1<<j; ok=1; break; } if(!ok) return 0; } return 1; }
  if(MODE==0||MODE==2||MODE==3||MODE==4){
    if(dist(s->r)!=0) return 0;
    if(getenv("TOUCHOK")) for(int i=0;i<N;i++) if(TAU0+(int)s->last[i]>DDL[i]) return 0;
    return 1; } int c=0; for(int i=0;i<N;i++) if(s->r[i]>>TBIT&1) c++; return c==1; }
int main(int argc,char**argv){ if(argc>6){ MODE=atoi(argv[6]); TBIT=atoi(argv[7]); }
  int W=atoi(argv[1]), maxd=atoi(argv[2]); rs^=atoi(argv[3])*0x9E3779B97F4A7C15ull; MU=atof(argv[4]); const char*out=argv[5];
  if(scanf("%d",&P)!=1) return 1; memset(tidx,-1,sizeof tidx);
  for(int i=0;i<P;i++){ int m; scanf("%d",&m); term[i]=m; tidx[m]=i; }
  ALLDONE=(P==64)?~0ull:((1ull<<P)-1);
  if(getenv("LATEMASK")){ unsigned lm=atoi(getenv("LATEMASK")); for(int i=0;i<P;i++) if(term[i]&lm) LATESET|=1ull<<i; LATEW=getenv("LATEW")?atof(getenv("LATEW")):0.5; }
  if(getenv("WDL")) WDL=atof(getenv("WDL")); if(getenv("CXPEN")) CXPEN=atof(getenv("CXPEN")); if(getenv("RDIST")) RDIST=atoi(getenv("RDIST")); if(getenv("NOTGT")) NOTGT=atoi(getenv("NOTGT")); if(getenv("NOTGT_AFTER")) NOTGT_AFTER=atoi(getenv("NOTGT_AFTER")); if(getenv("NOISE")) NOISE=atof(getenv("NOISE")); if(getenv("LAW")) LAW=atof(getenv("LAW"));
  if(MODE==3){ TAU0=1<<30; for(int i=0;i<N;i++){ if(scanf("%d %d",&RDY[i],&DDL[i])!=2) return 1; if(RDY[i]<TAU0) TAU0=RDY[i]; } }
  if(MODE==4){ TAU0=1<<30; for(int i=0;i<N;i++){ int st; if(scanf("%d %d %d",&st,&RDY[i],&DDL[i])!=3) return 1; ST[i]=st; SRDY[i]=RDY[i]; CRDY[i]=RDY[i]; if(RDY[i]<TAU0) TAU0=RDY[i]; } if(getenv("SRDY")){ const char*p=getenv("SRDY"); for(int i=0;i<N;i++){ SRDY[i]=atoi(p); while(*p && *p!=44) p++; if(*p) p++; if(SRDY[i]<TAU0) TAU0=SRDY[i]; } } if(getenv("CTRL_RDY")){ const char*p=getenv("CTRL_RDY"); for(int i=0;i<N;i++){ CRDY[i]=atoi(p); while(*p && *p!=44) p++; if(*p) p++; } } }
  for(int i=0;i<N;i++) DDLE[i]=DDL[i];
  HAVECTRL=getenv("CTRL_RDY")!=0; HAVETB=getenv("TOUCHBAD")!=0;
  if(getenv("ZS")){ TYPED=1; rdlist("ZS",ZS); rdlist("XS",XS); rdlist("ZD",ZD); rdlist("XD",XD); TAU0=1<<30; for(int i=0;i<N;i++){ if(ZS[i]<TAU0) TAU0=ZS[i]; if(XS[i]<TAU0) TAU0=XS[i]; } fprintf(stderr,"typed windows, tau0 %d\n",TAU0); }
  for(int i=0;i<N;i++) TCAP[i]=255; if(getenv("TCAP")){ HAVECAP=1; const char*p=getenv("TCAP"); for(int i=0;i<N;i++){ TCAP[i]=atoi(p); while(*p && *p!=44) p++; if(*p) p++; } }
  if(getenv("PREFIX")){ FILE*pf=fopen(getenv("PREFIX"),"r"); int dd; if(fscanf(pf,"%d %d",&dd,&PFTAU0)!=2) return 3; PFK=atoi(getenv("PREFIXK"));
    for(int k=1;k<=PFK && k<=dd;k++){ if(fscanf(pf,"%d",&PFN[k])!=1) return 3; for(int q=0;q<PFN[k];q++) if(fscanf(pf,"%d %d",&PFC[k][q],&PFT[k][q])!=2) return 3; }
    fclose(pf); fprintf(stderr,"prefix %d layers (tau0 file %d, run %d)\n",PFK,PFTAU0,TAU0); }
  if(getenv("PERMSET")){ PERMA=atoi(getenv("PERMSET")); LA=0; for(int j=0;j<N;j++) if((PERMA>>j&1) && DDL[j]>LA) LA=DDL[j]; for(int i=0;i<N;i++) if(PERMA>>i&1) DDLE[i]=LA; }
  uint8_t cs[5],ts[5]; genm(0,0,cs,ts); fprintf(stderr,"matchings %d\n",M);
  // storage per layer
  S **L=malloc(sizeof(S*)*(maxd+1)); int *Ln=calloc(maxd+1,sizeof(int));
  L[0]=malloc(sizeof(S)); S s0; for(int i=0;i<N;i++) s0.r[i]=(MODE==4)?ST[i]:(1<<i); s0.pend=0; s0.done=0; s0.par=-1; s0.mv=-1; memset(s0.last,0,sizeof s0.last); memset(s0.cnt,0,sizeof s0.cnt); s0.ncx=0;
  for(int i=0;i<N;i++){ int k=tidx[s0.r[i]]; if(k>=0 && !(s0.done>>k&1)){ s0.done|=1ull<<k; if((MODE==3||MODE==4) && getenv("SINGLES_PENDING")) s0.pend|=1<<i; } }
  L[0][0]=s0; Ln[0]=1;
  hkeys=malloc(sizeof(uint64_t)*HSZ);
  int CAP=W*40; S *cand=malloc(sizeof(S)*CAP); HE *he=malloc(sizeof(HE)*CAP);
  int solved=-1, solvedIdx=-1;
  for(int d=1; d<=maxd; d++){
    memset(hkeys,0,sizeof(uint64_t)*HSZ);
    int nc=0; double thr=-1e18; 
    // per-parent keep top K children
    static int K=0; if(!K){ K=getenv("KCH")?atoi(getenv("KCH")):40; if(K>256) K=256; } static S kbuf[256]; static double ksc[256];
    for(int p=0;p<Ln[d-1];p++){
      const S*ps=&L[d-1][p]; int kn=0;
      for(int m=0;m<M;m++){
        int ok=1; for(int q=0;q<mk[m];q++) if(ps->pend>>mt[m][q]&1){ok=0;break;} if(!ok) continue;
        if(NOTGT && TAU0+d>NOTGT_AFTER){ for(int q=0;q<mk[m];q++) if(NOTGT>>mt[m][q]&1){ok=0;break;} if(!ok) continue; }
        if(PFK){ int k=TAU0+d-PFTAU0; if(k>=1 && k<=PFK){ if(mk[m]!=PFN[k]) continue; int allm=1; for(int q=0;q<mk[m]&&allm;q++){ int f=0; for(int r=0;r<PFN[k];r++) if(PFC[k][r]==mc[m][q]&&PFT[k][r]==mt[m][q]) f=1; if(!f) allm=0; } if(!allm) continue; } }
        if(MODE==3||MODE==4){ int tau=TAU0+d; for(int q=0;q<mk[m]&&ok;q++){ int a=mc[m][q], b=mt[m][q]; if(TYPED){ if(!(ZS[a]<tau && tau<=ZD[a] && XS[b]<tau && tau<=XD[b])) ok=0; } else { int ca=HAVECTRL?CRDY[a]:RDY[a]; if(!(ca<tau && tau<=DDLE[a] && RDY[b]<tau && tau<=DDLE[b])) ok=0; } } if(!ok) continue; }
        S c=*ps; c.par=p; c.mv=m; uint16_t used=0; uint16_t newp=0;
        for(int q=0;q<mk[m];q++){ used|=1<<mc[m][q]|1<<mt[m][q]; }
        for(int q=0;q<mk[m];q++){ c.last[mc[m][q]]=d; c.last[mt[m][q]]=d; c.cnt[mc[m][q]]++; c.cnt[mt[m][q]]++; } c.ncx+=mk[m];
        for(int q=0;q<mk[m];q++){ int t=mt[m][q]; uint16_t v=ps->r[t]^ps->r[mc[m][q]]; c.r[t]=v; int k=tidx[v]; if(k>=0 && !(c.done>>k&1)){ c.done|=1ull<<k; newp|=1<<t; } }
        if(MODE==3||MODE==4){ int tau=TAU0+d; uint16_t av=0; for(int i=0;i<N;i++){ if(TYPED){ if(ZS[i]<tau && tau<=ZD[i]) av|=1<<i; } else if(SRDY[i]<tau && tau<=DDL[i]) av|=1<<i; } uint16_t fired=ps->pend & (uint16_t)~used & av; for(int i=0;i<N;i++) if(fired>>i&1){ c.last[i]=d; c.cnt[i]++; } c.pend=(ps->pend & (used|(uint16_t)~av))|newp; } else
        c.pend=(ps->pend & used)|newp;
        if(MODE==3||MODE==4){ int tau=TAU0+d; int bad=0; for(int i=0;i<N;i++){ uint16_t home=(MODE==4)?ST[i]:(1u<<i); if(TYPED){ if((c.pend>>i&1) && ZD[i]<=tau) bad=1; if(XD[i]<=tau && c.r[i]!=home) bad=1; continue; } if(HAVETB && TAU0+(int)c.last[i]>DDL[i]) bad=1; if((c.pend>>i&1) && DDLE[i]<=tau) bad=1; if(PERMA>>i&1){ if(DDLE[i]<=tau && !inSTA(c.r[i])) bad=1; } else if(DDL[i]<=tau && c.r[i]!=home) bad=1; } if(bad) continue; }
        if(HAVECAP){ int badc=0; for(int i=0;i<N;i++) if(c.cnt[i]+((c.pend>>i)&1)>TCAP[i]) badc=1; if(badc) continue; }
        if(mk[m]==0 && MODE!=3 && MODE!=4) continue;
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
  fprintf(f,"%d %d\n",d,TAU0);
  for(int k=1;k<=d;k++){ int m=mvs[k]; fprintf(f,"%d",mk[m]); for(int q=0;q<mk[m];q++) fprintf(f," %d %d",mc[m][q],mt[m][q]); fprintf(f,"\n"); }
  fclose(f); return 0;
}
