// Layer-synchronous beam search for a conditional loader, v3:
//  - bitset scoring (popcount instead of P-loops)
//  - candidate-pair pruning: only the NP most useful directed CX pairs generate matchings
//  - two-step reach in the score
// stdin: P ; P lines "mask target" ; [NREQ ; req...] ; [nfree ; masks...]
// argv: W K maxd seed wcond wreach out [wcx] [w0 w1 w2]
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#define NW 9
#define TB(i) (1u<<(6+(i)))
#define TMASK (7u<<6)
typedef struct { uint16_t r[NW]; uint16_t pend; uint16_t forbid; uint64_t d[2]; uint8_t closed; uint8_t clw[3]; int par; int mv; } S;
int NREQ=0, SPANNEED=0; unsigned reqv[8]; unsigned char inspan[512]; double WSPAN=1.0;
int P; unsigned pm[128]; int pt[128]; short pidx[512]; short fidx[512]; int totcnt[4]; double wt3[3]; double WFREE=1.0; int NFREE=0;
uint64_t tmk[4][2], cmk[3][2];
static inline int pc2(const uint64_t a[2], const uint64_t b[2]){ return __builtin_popcountll(a[0]&b[0])+__builtin_popcountll(a[1]&b[1]); }
static inline int pcn2(const uint64_t a[2], const uint64_t b[2]){ return __builtin_popcountll(~a[0]&b[0])+__builtin_popcountll(~a[1]&b[1]); }
int NP=20; int MAXK=4;
typedef struct { uint8_t c,t; } PR;
static inline int isdone(const S*s,int p){ return s->d[p>>6]>>(p&63)&1; }
static inline void setdone(S*s,int p){ s->d[p>>6]|=1ull<<(p&63); }
static inline int allowed(const S*s,int p){ int i=pt[p];
  if(i==3){ unsigned need=pm[p]&TMASK; return (need & ~((unsigned)s->closed<<6))==0; }
  if(s->closed>>i&1) return 0; unsigned other=pm[p]&TMASK&~TB(i); return (other & ~((unsigned)s->closed<<6))==0; }
void settle(S*s){
  for(int w=0;w<NW;w++){ if(s->pend>>w&1) continue; int p=pidx[s->r[w]];
    if(p>=0 && !isdone(s,p) && allowed(s,p)){ setdone(s,p); s->pend|=1<<w; continue; }
    int q=fidx[s->r[w]]; if(q>=0 && !isdone(s,q) && allowed(s,q)){ setdone(s,q); s->pend|=1<<w; } }
  s->forbid=0; for(int i=0;i<3;i++){ s->clw[i]=255; if(s->closed>>i&1) continue; if(pcn2(s->d,tmk[i])) continue;
    int cnt=0,ww=-1; for(int w=0;w<NW;w++) if(s->r[w]&TB(i)){cnt++;ww=w;}
    if(cnt!=1) continue; unsigned ob=0; for(int j=0;j<3;j++) if(!(s->closed>>j&1)) ob|=TB(j);
    if(s->r[ww]&ob&~TB(i)) continue; s->clw[i]=ww; s->forbid|=1<<ww; }
}
double WREACH, WREACH2=0, WCOND, WCX=0; int CLOPT=0; double WSPREAD=0; int SPCAP=3; double WREADY=0; int RCAP=4, RCAP1=10, RCAP2=24;
int spancnt(const S*s){ int c=0; for(int w=0;w<NW;w++) if(inspan[s->r[w]]) c++; return c; }
static uint64_t rs=88172645463325252ull; static inline uint64_t xr(){ rs^=rs<<13; rs^=rs>>7; rs^=rs<<17; return rs; }
static unsigned char seen[128];
double score(const S*s){
  double sc=0;
  sc+=WFREE*pc2(s->d,tmk[3]);
  for(int i=0;i<3;i++){ int dn=pc2(s->d,tmk[i]); sc+=wt3[i]*dn;
    if(s->closed>>i&1) sc+=WCOND; else if(dn==totcnt[i]){ int cnt=0; for(int w=0;w<NW;w++) if(s->r[w]&TB(i)) cnt++; sc+=WCOND*0.5/cnt; } }
  int reach=0, reach2=0; memset(seen,0,P);
  uint16_t rr[NW]; for(int w=0;w<NW;w++) rr[w]=s->r[w];
  for(int t=0;t<NW;t++){ if(s->pend>>t&1) continue; for(int c=0;c<NW;c++){ if(c==t) continue; unsigned v=rr[t]^rr[c];
      int p=pidx[v]; if(p>=0 && !seen[p] && !isdone(s,p) && allowed(s,p)){ seen[p]=1; reach++; }
      if(WREACH2>0){ for(int c2=0;c2<NW;c2++){ if(c2==t) continue; int q=pidx[v^rr[c2]];
          if(q>=0 && !seen[q] && !isdone(s,q) && allowed(s,q)){ seen[q]=2; reach2++; } } } } }
  if(reach>RCAP1) reach=RCAP1; sc+=WREACH*reach;
  if(reach2>RCAP2) reach2=RCAP2; sc+=WREACH2*reach2;
  if(WREADY>0){ unsigned clab=0, opent=0;
    for(int j=0;j<3;j++){ if(s->closed>>j&1) clab|=TB(j); else opent|=TB(j); }
    if(clab && opent){ int c=0; for(int w=0;w<NW;w++) if((s->r[w]&clab) && (s->r[w]&opent)) c++; if(c>RCAP) c=RCAP; sc+=WREADY*c; } }
  if(WSPREAD>0){ for(int j=0;j<3;j++){ if(!(s->closed>>j&1)) continue; if(!pcn2(s->d,cmk[j])) continue;
      int cnt=0; for(int w=0;w<NW;w++) if(s->r[w]&TB(j)) cnt++; if(cnt>SPCAP) cnt=SPCAP; sc+=WSPREAD*cnt; } }
  if(NREQ && s->closed==7){ int need = SPANNEED? SPANNEED : NREQ; int c=spancnt(s); sc+=WSPAN*(c<need?c:need); }
  return sc+(xr()&1023)/1e7;
}
uint64_t hstate(const S*s){ uint64_t h=s->d[0]*0x9E3779B97F4A7C15ull ^ s->d[1]*0xC2B2AE3D27D4EB4Full ^ s->closed;
  for(int i=0;i<NW;i++){ h^=((uint64_t)s->r[i]<<1)|(s->pend>>i&1); h*=0x100000001B3ull; h^=h>>31; } return h|1; }
typedef struct { double sc; int idx; } HE;
int cmpd(const void*a,const void*b){ double x=((HE*)a)->sc,y=((HE*)b)->sc; return x<y?1:x>y?-1:0; }
#define HSZ (1<<22)
// ---- per-parent pair selection ----
typedef struct { double g; uint8_t c,t; } PG;
int cmpg(const void*a,const void*b){ double x=((PG*)a)->g,y=((PG*)b)->g; return x<y?1:x>y?-1:0; }
int main(int argc,char**argv){
  int W=atoi(argv[1]),K=atoi(argv[2]),maxd=atoi(argv[3]); if(K>128)K=128; rs^=atoi(argv[4])*0x9E3779B97F4A7C15ull;
  WCOND=atof(argv[5]); WREACH=atof(argv[6]); const char*out=argv[7]; if(argc>8) WCX=atof(argv[8]);
  for(int i=0;i<512;i++){ pidx[i]=-1; fidx[i]=-1; }
  if(scanf("%d",&P)!=1) return 1; for(int p=0;p<P;p++){ if(scanf("%u %d",&pm[p],&pt[p])!=2) return 1; pidx[pm[p]]=p; totcnt[pt[p]]++; }
  if(scanf("%d",&NREQ)==1 && NREQ>0){ for(int r=0;r<NREQ;r++) if(scanf("%u",&reqv[r])!=1) return 1;
    for(int b=0;b<(1<<NREQ);b++){ unsigned v=0; for(int r=0;r<NREQ;r++) if(b>>r&1) v^=reqv[r]; if(v) inspan[v]=1; } } else NREQ=0;
  { int nf=0; if(scanf("%d",&nf)==1 && nf>0){ for(int f=0;f<nf;f++){ unsigned mk_; if(scanf("%u",&mk_)!=1) return 1; pm[P]=mk_; pt[P]=3; fidx[mk_]=P; P++; totcnt[3]++; } NFREE=nf; } }
  if(P>128){ fprintf(stderr,"P too large\n"); return 1; }
  for(int p=0;p<P;p++){ tmk[pt[p]][p>>6]|=1ull<<(p&63); for(int j=0;j<3;j++) if(pm[p]&TB(j)) cmk[j][p>>6]|=1ull<<(p&63); }
  if(getenv("WFREE")) WFREE=atof(getenv("WFREE"));
  if(getenv("SPANNEED")) SPANNEED=atoi(getenv("SPANNEED"));
  if(getenv("WSPAN")) WSPAN=atof(getenv("WSPAN"));
  if(getenv("CLOPT")) CLOPT=atoi(getenv("CLOPT"));
  if(getenv("WSPREAD")) WSPREAD=atof(getenv("WSPREAD"));
  if(getenv("WREADY")) WREADY=atof(getenv("WREADY"));
  if(getenv("WREACH2")) WREACH2=atof(getenv("WREACH2"));
  if(getenv("RCAP")) RCAP=atoi(getenv("RCAP")); if(getenv("SPCAP")) SPCAP=atoi(getenv("SPCAP"));
  if(getenv("RCAP1")) RCAP1=atoi(getenv("RCAP1")); if(getenv("RCAP2")) RCAP2=atoi(getenv("RCAP2"));
  if(getenv("NP")) NP=atoi(getenv("NP")); if(getenv("MAXK")) MAXK=atoi(getenv("MAXK"));
  for(int i=0;i<3;i++){ int dep=0; for(int p=0;p<P;p++) if((pm[p]&TB(i)) && pt[p]!=i) dep++; wt3[i]=1.0+(dep>0?0.5:0); }
  if(argc>11){ for(int i=0;i<3;i++) wt3[i]=atof(argv[9+i]); }
  fprintf(stderr,"P %d cnt %d %d %d %d NP %d\n",P,totcnt[0],totcnt[1],totcnt[2],totcnt[3],NP);
  S **L=malloc(sizeof(S*)*(maxd+1)); int *Ln=calloc(maxd+1,sizeof(int));
  S s0; memset(&s0,0,sizeof s0); for(int w=0;w<NW;w++) s0.r[w]=1<<w; s0.par=-1; s0.mv=-1;
  for(int i=0;i<3;i++){ int p=pidx[TB(i)]; if(p>=0) setdone(&s0,p); }
  settle(&s0); s0.forbid|=TMASK;
  L[0]=malloc(sizeof(S)); L[0][0]=s0; Ln[0]=1;
  int d0=1;
  if(getenv("PREFIX")){
    FILE*pf=fopen(getenv("PREFIX"),"r"); int K0=atoi(getenv("PREFIXK")); int dd,pp; if(fscanf(pf,"%d %d",&dd,&pp)!=2) return 3;
    for(int k=1;k<=K0;k++){
      int nk; if(fscanf(pf,"%d",&nk)!=1) return 3; int cc[5],tt[5];
      const S*ps=&L[k-1][0]; S c=*ps; c.par=0; c.mv=-1;
      uint16_t u=0; for(int q=0;q<nk;q++){ if(fscanf(pf,"%d %d",&cc[q],&tt[q])!=2) return 3; u|=1<<cc[q]|1<<tt[q]; }
      for(int i=0;i<3;i++) if(ps->clw[i]!=255){ int ww=ps->clw[i]; c.r[ww]=TB(i); c.closed|=1<<i; c.pend&=~(1<<ww); }
      c.pend&=u;
      for(int q=0;q<nk;q++) c.r[tt[q]]=ps->r[tt[q]]^ps->r[cc[q]];
      settle(&c);
      L[k]=malloc(sizeof(S)); L[k][0]=c; Ln[k]=1;
    }
    fclose(pf); d0=K0+1; fprintf(stderr,"prefix %d layers\n",K0);
  }
  uint64_t *hk=malloc(sizeof(uint64_t)*HSZ); int CAP=W*K+16; S*cand=malloc(sizeof(S)*CAP); HE*he=malloc(sizeof(HE)*CAP);
  S*kb=malloc(sizeof(S)*K); double*ks=malloc(sizeof(double)*K);
  int solved=-1,sidx=-1;
  // move record: list of (c,t) pairs per candidate
  uint8_t (*mvrec)[9]=malloc(9*(size_t)CAP);
  uint8_t (**movetab)=NULL; (void)movetab;
  uint8_t **allmv=malloc(sizeof(uint8_t*)*(maxd+1));
  for(int i=0;i<=maxd;i++) allmv[i]=NULL;
  for(int d=d0;d<=maxd;d++){
    memset(hk,0,sizeof(uint64_t)*HSZ); int nc=0;
    for(int p=0;p<Ln[d-1];p++){
      const S*ps=&L[d-1][p]; int kn=0;
      uint8_t kbmv[128][9];
      int ncl=0, clist[3];
      for(int i=0;i<3;i++) if(ps->clw[i]!=255) clist[ncl++]=i;
      int nsub=(CLOPT&&ncl>0)?(1<<ncl):1;
      for(int sub=0; sub<nsub; sub++){
      uint16_t subforbid=0, dosub=0;
      if(CLOPT&&ncl>0){ for(int q=0;q<ncl;q++) if(sub>>q&1){ dosub|=1<<clist[q]; subforbid|=1<<ps->clw[clist[q]]; } }
      else { dosub=0xFF; subforbid=ps->forbid; }
      // ---- candidate pairs ----
      PG pg[72]; int npg=0;
      for(int t=0;t<NW;t++){ if((subforbid>>t&1)||(ps->pend>>t&1)) continue;
        for(int c=0;c<NW;c++){ if(c==t||(subforbid>>c&1)) continue;
          unsigned v=ps->r[t]^ps->r[c]; double g=0;
          int q=pidx[v]; if(q>=0 && !isdone(ps,q) && allowed(ps,q)) g+=4.0;
          else { int qq=fidx[v]; if(qq>=0 && !isdone(ps,qq) && allowed(ps,qq)) g+=3.0; }
          int n2=0; for(int c2=0;c2<NW;c2++){ if(c2==t) continue; int r2=pidx[v^ps->r[c2]];
            if(r2>=0 && !isdone(ps,r2) && allowed(ps,r2)) n2++; }
          g+=0.35*(n2>6?6:n2);
          if(inspan[v]) g+=0.15;
          g+=(xr()&255)/2000.0;
          pg[npg].g=g; pg[npg].c=c; pg[npg].t=t; npg++; } }
      qsort(pg,npg,sizeof(PG),cmpg);
      int np=npg<NP?npg:NP;
      // ---- enumerate matchings among the top np pairs (<= MAXK edges) ----
      int stack_c[5],stack_t[5];
      int idxs[5];
      for(int kk=0;kk<=MAXK;kk++){
        if(kk==0){
          S c=*ps; c.par=p; c.mv=0;
          for(int i=0;i<3;i++) if(ps->clw[i]!=255 && (dosub>>i&1)){ int ww=ps->clw[i]; c.r[ww]=TB(i); c.closed|=1<<i; c.pend&=~(1<<ww); }
          c.pend&=subforbid;
          settle(&c);
          double sc=score(&c);
          if(kn<K){ kb[kn]=c; ks[kn]=sc; kbmv[kn][0]=0; kn++; }
          else { int mi=0; for(int i=1;i<K;i++) if(ks[i]<ks[mi]) mi=i; if(sc>ks[mi]){ kb[mi]=c; ks[mi]=sc; kbmv[mi][0]=0; } }
          continue;
        }
        for(int i=0;i<kk;i++) idxs[i]=i;
        while(1){
          uint16_t used=0; int ok=1;
          for(int i=0;i<kk;i++){ int a=1<<pg[idxs[i]].c, b=1<<pg[idxs[i]].t; if(used&(a|b)){ok=0;break;} used|=a|b; }
          if(ok){
            S c=*ps; c.par=p; c.mv=kk;
            for(int i=0;i<3;i++) if(ps->clw[i]!=255 && (dosub>>i&1)){ int ww=ps->clw[i]; c.r[ww]=TB(i); c.closed|=1<<i; c.pend&=~(1<<ww); }
            c.pend&=(used|subforbid);
            for(int i=0;i<kk;i++){ stack_c[i]=pg[idxs[i]].c; stack_t[i]=pg[idxs[i]].t; }
            for(int i=0;i<kk;i++) c.r[stack_t[i]]=ps->r[stack_t[i]]^ps->r[stack_c[i]];
            settle(&c);
            double sc=score(&c)-WCX*kk;
            int slot=-1;
            if(kn<K){ slot=kn; kn++; } else { int mi=0; for(int i=1;i<K;i++) if(ks[i]<ks[mi]) mi=i; if(sc>ks[mi]) slot=mi; }
            if(slot>=0){ kb[slot]=c; ks[slot]=sc; kbmv[slot][0]=kk; for(int i=0;i<kk;i++){ kbmv[slot][1+2*i]=stack_c[i]; kbmv[slot][2+2*i]=stack_t[i]; } }
          }
          int i=kk-1; while(i>=0 && idxs[i]==np-kk+i) i--;
          if(i<0) break; idxs[i]++; for(int j=i+1;j<kk;j++) idxs[j]=idxs[j-1]+1;
        }
      }
      }
      for(int i=0;i<kn;i++){ uint64_t h=hstate(&kb[i]); uint64_t sl=h&(HSZ-1); int dup=0;
        while(hk[sl]){ if(hk[sl]==h){dup=1;break;} sl=(sl+1)&(HSZ-1);} if(dup) continue; hk[sl]=h;
        if(nc<CAP){ cand[nc]=kb[i]; memcpy(mvrec[nc],kbmv[i],9); he[nc].sc=ks[i]; he[nc].idx=nc; nc++; } }
    }
    qsort(he,nc,sizeof(HE),cmpd); int keep=nc<W?nc:W; L[d]=malloc(sizeof(S)*keep); Ln[d]=keep;
    allmv[d]=malloc(9*(size_t)keep);
    int bd=0,bcl=0;
    for(int i=0;i<keep;i++){ L[d][i]=cand[he[i].idx]; memcpy(allmv[d]+9*i,mvrec[he[i].idx],9); L[d][i].mv=i;
      S*s=&L[d][i]; int dn=__builtin_popcountll(s->d[0])+__builtin_popcountll(s->d[1]); if(dn>bd) bd=dn;
      int cl=__builtin_popcount(s->closed); if(cl>bcl) bcl=cl;
      int allc=(s->closed==7);
      if(allc && NFREE){ if(pc2(s->d,tmk[3])<NFREE) allc=0; }
      { int need=SPANNEED?SPANNEED:NREQ; if(allc&&NREQ&&spancnt(s)<need) allc=0; }
      if(allc && solved<0){ solved=d; sidx=i; } }
    fprintf(stderr,"depth %d cand %d kept %d best %d/%d closed %d\n",d,nc,keep,bd,P,bcl);
    if(solved>=0) break;
  }
  if(solved<0) return 2;
  FILE*f=fopen(out,"w");
  int idx=sidx; uint8_t (*seq)[9]=malloc(9*(size_t)(solved+1));
  for(int k=solved;k>=1;k--){ memcpy(seq[k],allmv[k]+9*idx,9); idx=L[k][idx].par; }
  fprintf(f,"%d %d\n",solved,L[solved][sidx].pend?1:0);
  for(int k=1;k<=solved;k++){ int nk=seq[k][0]; fprintf(f,"%d",nk); for(int q=0;q<nk;q++) fprintf(f," %d %d",seq[k][1+2*q],seq[k][2+2*q]); fprintf(f,"\n"); }
  fclose(f); return 0;
}
