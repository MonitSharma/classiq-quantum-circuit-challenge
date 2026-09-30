// Layer-synchronous beam search for a conditional loader (9 wires: z0..z5 = 0..5, t0..t2 = 6..8).
// stdin: P ; P lines "mask target"   (same as sa.c, R section ignored if absent)
// argv: W K maxd seed wcond wreach out
// Model (matches sa4 lazy rules, layer-synchronous): layer 1 targets busy (H). A CX target may not carry a pending rotation.
// Pending rotations fire on the first idle layer (Z commutes through controls). Closing H needs the wire idle; forced ASAP.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#define NW 9
#define TB(i) (1u<<(6+(i)))
#define TMASK (7u<<6)
typedef struct { uint16_t r[NW]; uint16_t pend; uint16_t forbid; uint64_t d[2]; uint8_t closed; uint8_t clw[3]; int par; int mv; } S;
int NREQ=0; int SPANNEED=0; unsigned reqv[8]; unsigned char inspan[512]; double WSPAN=1.0;
int P; unsigned pm[256]; int pt[256]; short pidx[512]; short fidx[512]; int totcnt[4]; double wt3[3]; double WFREE=1.0; int NFREE=0;
int M; uint8_t mc[30000][4], mt[30000][4], mk[30000]; uint16_t mused[30000], mtg[30000];
void genm(int used,int k,uint8_t*cs,uint8_t*ts){
  int a=-1; for(int i=0;i<NW;i++) if(!(used>>i&1)){a=i;break;}
  if(a<0){ memcpy(mc[M],cs,4); memcpy(mt[M],ts,4); mk[M]=k; uint16_t u=0,t=0; for(int q=0;q<k;q++){u|=1<<cs[q]|1<<ts[q]; t|=1<<ts[q];} mused[M]=u; mtg[M]=t; M++; return; }
  genm(used|1<<a,k,cs,ts);
  if(k<4) for(int b=a+1;b<NW;b++) if(!(used>>b&1)){ cs[k]=a; ts[k]=b; genm(used|1<<a|1<<b,k+1,cs,ts); cs[k]=b; ts[k]=a; genm(used|1<<a|1<<b,k+1,cs,ts); }
}
static inline int isdone(const S*s,int p){ return s->d[p>>6]>>(p&63)&1; }
static inline void setdone(S*s,int p){ s->d[p>>6]|=1ull<<(p&63); }
static inline int allowed(const S*s,int p){ int i=pt[p];
  if(i==3){ unsigned need=pm[p]&TMASK; return (need & ~((unsigned)s->closed<<6))==0; }
  if(s->closed>>i&1) return 0; unsigned other=pm[p]&TMASK&~TB(i); return (other & ~((unsigned)s->closed<<6))==0; }
int remcnt(const S*s,int i){ int c=0; for(int p=0;p<P;p++) if(pt[p]==i && !isdone(s,p)) c++; return c; }
// settle after a layer: mark new pending terms, compute closings available next layer
void settle(S*s){
  for(int w=0;w<NW;w++){ if(s->pend>>w&1) continue; int p=pidx[s->r[w]];
    if(p>=0 && !isdone(s,p) && allowed(s,p)){ setdone(s,p); s->pend|=1<<w; continue; }
    int q=fidx[s->r[w]]; if(q>=0 && !isdone(s,q) && allowed(s,q)){ setdone(s,q); s->pend|=1<<w; } }
  s->forbid=0; for(int i=0;i<3;i++){ s->clw[i]=255; if(s->closed>>i&1) continue; if(remcnt(s,i)) continue;
    int cnt=0,ww=-1; for(int w=0;w<NW;w++) if(s->r[w]&TB(i)){cnt++;ww=w;}
    if(cnt!=1) continue; unsigned ob=0; for(int j=0;j<3;j++) if(!(s->closed>>j&1)) ob|=TB(j);
    if(s->r[ww]&ob&~TB(i)) continue; s->clw[i]=ww; s->forbid|=1<<ww; }
}
double WREACH, WCOND, WCX=0; int CLOPT=0; double WSPREAD=0; int SPCAP=3; double WREADY=0; int RCAP=4;
int spancnt(const S*s){ int c=0; for(int w=0;w<NW;w++) if(inspan[s->r[w]]) c++; return c; } static uint64_t rs=88172645463325252ull; static inline uint64_t xr(){ rs^=rs<<13; rs^=rs>>7; rs^=rs<<17; return rs; }
double score(const S*s){
  double sc=0; int dn[4]={0,0,0,0};
  for(int p=0;p<P;p++) if(isdone(s,p)) dn[pt[p]]++;
  sc+=WFREE*dn[3];
  for(int i=0;i<3;i++){ sc+=wt3[i]*dn[i]; if(s->closed>>i&1) sc+=WCOND; else if(dn[i]==totcnt[i]){ int cnt=0; for(int w=0;w<NW;w++) if(s->r[w]&TB(i)) cnt++; sc+=WCOND*0.5/cnt; } }
  // reach: undone allowed terms obtainable by one CX onto a non-pending wire
  int reach=0; static unsigned char seen[256]; memset(seen,0,P);
  for(int t=0;t<NW;t++){ if(s->pend>>t&1) continue; for(int c=0;c<NW;c++) if(c!=t){ int p=pidx[s->r[t]^s->r[c]]; if(p>=0 && !seen[p] && !isdone(s,p) && allowed(s,p)){ seen[p]=1; reach++; } } }
  if(reach>8) reach=8; sc+=WREACH*reach;
  if(WREADY>0){
    // wires that carry a closed label AND an open target bit: ready-made conditional accumulators
    unsigned clab=0, opent=0;
    for(int j=0;j<3;j++){ if(s->closed>>j&1) clab|=TB(j); else opent|=TB(j); }
    if(clab && opent){ int c=0; for(int w=0;w<NW;w++) if((s->r[w]&clab) && (s->r[w]&opent)) c++; if(c>RCAP) c=RCAP; sc+=WREADY*c; }
  }
  if(WSPREAD>0){
    // for each closed label j with remaining conditional terms, reward wires carrying it (cap SPCAP)
    for(int j=0;j<3;j++){ if(!(s->closed>>j&1)) continue; int rem=0; for(int p=0;p<P;p++) if(!isdone(s,p) && (pm[p]&TB(j))) rem++; if(!rem) continue;
      int cnt=0; for(int w=0;w<NW;w++) if(s->r[w]&TB(j)) cnt++; if(cnt>SPCAP) cnt=SPCAP; sc+=WSPREAD*cnt; }
  }
  if(NREQ && s->closed==7){ int need = SPANNEED? SPANNEED : NREQ; int c=spancnt(s); sc+=WSPAN*(c<need?c:need); }
  return sc+(xr()&1023)/1e7;
}
uint64_t hstate(const S*s){ uint64_t h=s->d[0]*0x9E3779B97F4A7C15ull ^ s->d[1]*0xC2B2AE3D27D4EB4Full ^ s->closed;
  for(int i=0;i<NW;i++){ h^=((uint64_t)s->r[i]<<1)|(s->pend>>i&1); h*=0x100000001B3ull; h^=h>>31; } return h|1; }
typedef struct { double sc; int idx; } HE;
int cmpd(const void*a,const void*b){ double x=((HE*)a)->sc,y=((HE*)b)->sc; return x<y?1:x>y?-1:0; }
#define HSZ (1<<22)
int main(int argc,char**argv){
  int W=atoi(argv[1]),K=atoi(argv[2]),maxd=atoi(argv[3]); rs^=atoi(argv[4])*0x9E3779B97F4A7C15ull; WCOND=atof(argv[5]); WREACH=atof(argv[6]); const char*out=argv[7]; if(argc>8) WCX=atof(argv[8]);
  for(int i=0;i<512;i++){ pidx[i]=-1; fidx[i]=-1; }
  if(scanf("%d",&P)!=1) return 1; for(int p=0;p<P;p++){ if(scanf("%u %d",&pm[p],&pt[p])!=2) return 1; pidx[pm[p]]=p; totcnt[pt[p]]++; }
  if(scanf("%d",&NREQ)==1 && NREQ>0){ for(int r=0;r<NREQ;r++) if(scanf("%u",&reqv[r])!=1) return 1; for(int b=0;b<(1<<NREQ);b++){ unsigned v=0; for(int r=0;r<NREQ;r++) if(b>>r&1) v^=reqv[r]; if(v) inspan[v]=1; } } else NREQ=0;
  { int nf=0; if(scanf("%d",&nf)==1 && nf>0){ for(int f=0;f<nf;f++){ unsigned mk_; if(scanf("%u",&mk_)!=1) return 1; pm[P]=mk_; pt[P]=3; fidx[mk_]=P; P++; totcnt[3]++; } NFREE=nf; } }
  if(getenv("WFREE")) WFREE=atof(getenv("WFREE"));
  if(getenv("SPANNEED")) SPANNEED=atoi(getenv("SPANNEED"));
  if(getenv("WSPAN")) WSPAN=atof(getenv("WSPAN"));
  if(getenv("CLOPT")) CLOPT=atoi(getenv("CLOPT"));
  if(getenv("WSPREAD")) WSPREAD=atof(getenv("WSPREAD"));
  if(getenv("WREADY")) WREADY=atof(getenv("WREADY"));
  if(getenv("RCAP")) RCAP=atoi(getenv("RCAP")); if(getenv("SPCAP")) SPCAP=atoi(getenv("SPCAP"));
  // weight: targets that others depend on count more
  for(int i=0;i<3;i++){ int dep=0; for(int p=0;p<P;p++) if(pm[p]&TB(i) && pt[p]!=i) dep++; wt3[i]=1.0+ (dep>0?0.5:0); }
  if(argc>11){ for(int i=0;i<3;i++) wt3[i]=atof(argv[9+i]); }
  uint8_t cs[4],ts[4]; genm(0,0,cs,ts); fprintf(stderr,"matchings %d P %d cnt %d %d %d\n",M,P,totcnt[0],totcnt[1],totcnt[2]);
  S **L=malloc(sizeof(S*)*(maxd+1)); int *Ln=calloc(maxd+1,sizeof(int));
  S s0; memset(&s0,0,sizeof s0); for(int w=0;w<NW;w++) s0.r[w]=1<<w; s0.par=-1; s0.mv=-1;
  for(int i=0;i<3;i++){ int p=pidx[TB(i)]; if(p>=0) setdone(&s0,p); }
  settle(&s0); s0.forbid|=TMASK; // layer 1: H on targets
  L[0]=malloc(sizeof(S)); L[0][0]=s0; Ln[0]=1;
  int d0=1;
  if(getenv("PREFIX")){
    FILE*pf=fopen(getenv("PREFIX"),"r"); int K0=atoi(getenv("PREFIXK")); int dd,pp; if(fscanf(pf,"%d %d",&dd,&pp)!=2) return 3;
    for(int k=1;k<=K0;k++){
      int nk; if(fscanf(pf,"%d",&nk)!=1) return 3; int cc[5],tt[5]; uint16_t u=0;
      for(int q=0;q<nk;q++){ if(fscanf(pf,"%d %d",&cc[q],&tt[q])!=2) return 3; u|=1<<cc[q]|1<<tt[q]; }
      int mf=-1; for(int m=0;m<M && mf<0;m++){ if(mk[m]!=nk || mused[m]!=u) continue; int ok=1; for(int q=0;q<nk&&ok;q++){ int f=0; for(int r=0;r<nk;r++) if(mc[m][r]==cc[q]&&mt[m][r]==tt[q]) f=1; if(!f) ok=0; } if(ok) mf=m; }
      if(mf<0) return 4;
      const S*ps=&L[k-1][0]; S c=*ps; c.par=0; c.mv=mf;
      for(int i=0;i<3;i++) if(ps->clw[i]!=255){ int ww=ps->clw[i]; c.r[ww]=TB(i); c.closed|=1<<i; c.pend&=~(1<<ww); }
      c.pend&=mused[mf];
      for(int q=0;q<mk[mf];q++) c.r[mt[mf][q]]=ps->r[mt[mf][q]]^ps->r[mc[mf][q]];
      settle(&c);
      L[k]=malloc(sizeof(S)); L[k][0]=c; Ln[k]=1;
    }
    fclose(pf); d0=K0+1; fprintf(stderr,"prefix %d layers loaded\n",K0);
  }
  uint64_t *hk=malloc(sizeof(uint64_t)*HSZ); int CAP=W*K+16; S*cand=malloc(sizeof(S)*CAP); HE*he=malloc(sizeof(HE)*CAP);
  S*kb=malloc(sizeof(S)*K); double*ks=malloc(sizeof(double)*K);
  int solved=-1,sidx=-1;
  for(int d=d0;d<=maxd;d++){
    memset(hk,0,sizeof(uint64_t)*HSZ); int nc=0;
    for(int p=0;p<Ln[d-1];p++){
      const S*ps=&L[d-1][p]; int kn=0;
      int ncl=0, clist[3];
      for(int i=0;i<3;i++) if(ps->clw[i]!=255) clist[ncl++]=i;
      int nsub = (CLOPT && ncl>0) ? (1<<ncl) : 1;
      for(int sub=0; sub<nsub; sub++){
      uint16_t subforbid=0, dosub=0;
      if(CLOPT && ncl>0){ for(int q=0;q<ncl;q++) if(sub>>q&1){ dosub|=1<<clist[q]; subforbid|=1<<ps->clw[clist[q]]; } }
      else { dosub=0xFF; subforbid=ps->forbid; }
      for(int m=0;m<M;m++){
        if(mused[m]&subforbid) continue; if(mtg[m]&ps->pend) continue;
        S c=*ps; c.par=p; c.mv=m;
        // closings this layer
        for(int i=0;i<3;i++) if(ps->clw[i]!=255 && (dosub>>i&1)){ int ww=ps->clw[i]; c.r[ww]=TB(i); c.closed|=1<<i; c.pend&=~(1<<ww); }
        // idle wires fire pending
        c.pend&=(mused[m]|subforbid);
        for(int q=0;q<mk[m];q++) c.r[mt[m][q]]=ps->r[mt[m][q]]^ps->r[mc[m][q]];
        settle(&c);
        double sc=score(&c)-WCX*mk[m];
        if(kn<K){ kb[kn]=c; ks[kn]=sc; kn++; } else { int mi=0; for(int i=1;i<K;i++) if(ks[i]<ks[mi]) mi=i; if(sc>ks[mi]){ kb[mi]=c; ks[mi]=sc; } }
      }
      }
      for(int i=0;i<kn;i++){ uint64_t h=hstate(&kb[i]); uint64_t sl=h&(HSZ-1); int dup=0; while(hk[sl]){ if(hk[sl]==h){dup=1;break;} sl=(sl+1)&(HSZ-1);} if(dup) continue; hk[sl]=h; if(nc<CAP){ cand[nc]=kb[i]; he[nc].sc=ks[i]; he[nc].idx=nc; nc++; } }
    }
    qsort(he,nc,sizeof(HE),cmpd); int keep=nc<W?nc:W; L[d]=malloc(sizeof(S)*keep); Ln[d]=keep;
    int bd=0, bcl=0;
    for(int i=0;i<keep;i++){ L[d][i]=cand[he[i].idx]; S*s=&L[d][i]; int dn=__builtin_popcountll(s->d[0])+__builtin_popcountll(s->d[1]); if(dn>bd) bd=dn; int cl=__builtin_popcount(s->closed); if(cl>bcl) bcl=cl;
      // finished: all closed after pending closings applied (closings scheduled count as needing this layer)
      int allc=1; for(int j=0;j<3;j++) if(!(s->closed>>j&1)) allc=0;
      if(allc && NFREE){ int fd=0; for(int p=0;p<P;p++) if(pt[p]==3 && isdone(s,p)) fd++; if(fd<NFREE) allc=0; }
      { int need = SPANNEED? SPANNEED : NREQ; if(allc && NREQ && spancnt(s)<need) allc=0; }
      if(allc && solved<0){ solved=d; sidx=i; } }
    { int bf=0; for(int i=0;i<keep;i++){ int f=0; for(int p=0;p<P;p++) if(pt[p]==3 && isdone(&L[d][i],p)) f++; if(f>bf) bf=f; }
      fprintf(stderr,"depth %d cand %d kept %d best done %d/%d closed %d freebest %d/%d\n",d,nc,keep,bd,P,bcl,bf,totcnt[3]); }
    if(getenv("DBGUNDONE") && d==maxd){ const S*s0=&L[d][0]; for(int p=0;p<P;p++) if(!isdone(s0,p)) fprintf(stderr,"undone p=%d mask=%u pt=%d\n",p,pm[p],pt[p]); }
    if(solved>=0) break;
  }
  if(solved<0) return 2;
  FILE*f=fopen(out,"w"); int idx=sidx; int*mv=malloc(sizeof(int)*(solved+1));
  for(int k=solved;k>=1;k--){ mv[k]=L[k][idx].mv; idx=L[k][idx].par; }
  fprintf(f,"%d %d\n",solved, L[solved][sidx].pend?1:0);
  for(int k=1;k<=solved;k++){ int m=mv[k]; fprintf(f,"%d",mk[m]); for(int q=0;q<mk[m];q++) fprintf(f," %d %d",mc[m][q],mt[m][q]); fprintf(f,"\n"); }
  fclose(f); return 0;
}
