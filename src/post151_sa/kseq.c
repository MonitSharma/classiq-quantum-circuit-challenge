// kseq: CX-sequence beam search for the 8-wire phase kernel, using the exact
// lazy/fused rotation timing model (same as sa4/lseq), per-wire arrival times and
// per-wire deadlines, and a return-to-start-frame requirement.
//
// stdin : P ; P term masks ; then N lines "ST rdy deadline"
// argv  : W maxsteps seed N out
// env   : WDONE WREACH WREACH2 WSLACK WRET WBAL MAXSKEW PERMSET
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#define MAXN 16
#define MAXP 128
typedef struct {
  uint16_t r[MAXN];
  int16_t  wt[MAXN];
  uint16_t lu;
  int16_t  pend[MAXN];
  uint64_t done[2];
  uint8_t  use[MAXN];
  int32_t  par; int8_t cc, tt;
} S;
static int N, P;
static uint16_t term[MAXP]; static int16_t tidx[65536];
static uint16_t ST[MAXN]; static int RDY[MAXN], DDL[MAXN];
static unsigned PERMA=0;
static double WDONE=3.7, WREACH=3.0, WREACH2=0.6, WSLACK=1.0, WRET=1.0, WBAL=0.3;
static int MAXSKEW=99, RCAP1=14, RCAP2=24; static int MAXUSE[MAXN]; static int HASMAXUSE=0; static unsigned NOROAM=0; static double TERMCOST=3.0; static double RETW=0.0, WTIGHT=0.0; static int TIGHT=14;
static double NOISE=0.0, GUMB=0.0; static int CHILDCAP=0;
static uint64_t rs=88172645463325252ull;
static inline uint64_t xr(){ rs^=rs<<13; rs^=rs>>7; rs^=rs<<17; return rs; }
static inline int isdone(const S*s,int p){ return s->done[p>>6]>>(p&63)&1; }
static inline int inSTA(uint16_t v){ for(int j=0;j<N;j++) if((PERMA>>j&1) && ST[j]==v) return 1; return 0; }
static void settle(S*s){
  for(int w=0;w<N;w++){ if(s->pend[w]>=0) continue; int p=tidx[s->r[w]];
    if(p>=0 && !isdone(s,p)){ s->pend[w]=p; s->done[p>>6]|=1ull<<(p&63); } }
}
static int apply_cx(S*s,int c,int t){
  if(s->pend[t]>=0){ if(!(s->lu>>t&1)){ s->wt[t]++; s->use[t]++; s->lu|=1<<t; if(s->wt[t]>DDL[t]) return 0; } s->pend[t]=-1; }
  int tau=(s->wt[c]>s->wt[t]?s->wt[c]:s->wt[t])+1;
  if(s->pend[c]>=0){ if(s->lu>>c&1){ s->pend[c]=-1; }
    else if(s->wt[c]+1<tau){ s->wt[c]++; s->use[c]++; s->lu|=1<<c; s->pend[c]=-1; } }
  if(tau>DDL[c]||tau>DDL[t]) return 0;
  s->wt[c]=s->wt[t]=tau; s->lu&=~((1u<<c)|(1u<<t));
  s->use[c]++; s->use[t]++;
  s->r[t]^=s->r[c];
  if(HASMAXUSE && (s->use[c]>MAXUSE[c] || s->use[t]>MAXUSE[t])) return 0;
  return 1;
}
static int retcx(const S*s);
static int retcnt(const S*s){ int k=0;
  for(int i=0;i<N;i++){ if(PERMA>>i&1){ if(!inSTA(s->r[i])) k++; } else if(s->r[i]!=ST[i]) k++; }
  return k; }
/* coordinates of ST in the current row basis -> XOR-count estimate for the return */
static int retcx(const S*s){
  uint32_t m[MAXN]; int n=N;
  for(int i=0;i<n;i++) m[i]=((uint32_t)s->r[i]<<16)|(1u<<i);
  int piv[32]; for(int i=0;i<32;i++) piv[i]=-1;
  int row=0;
  for(int c=31;c>=16 && row<n;c--){
    int sel=-1; for(int i=row;i<n;i++) if(m[i]>>c&1){ sel=i; break; }
    if(sel<0) continue;
    uint32_t tmp=m[row]; m[row]=m[sel]; m[sel]=tmp;
    for(int i=0;i<n;i++) if(i!=row && (m[i]>>c&1)) m[i]^=m[row];
    piv[c-16]=row; row++;
  }
  int tot=0;
  for(int i=0;i<n;i++){
    uint16_t v = (PERMA>>i&1) ? s->r[i] : ST[i];
    if((PERMA>>i&1)){ /* pick the nearest allowed target */
      int best=99; uint16_t bv=ST[i];
      for(int j=0;j<n;j++) if(PERMA>>j&1){ int x=__builtin_popcount((unsigned)(s->r[i]^ST[j])); if(x<best){best=x; bv=ST[j];} }
      v=bv; }
    uint32_t acc=0; uint16_t cur=v;
    for(int c=15;c>=0;c--){ if(!(cur>>c&1)) continue; int r2=piv[c]; if(r2<0){ acc=0xFFFF; break; }
      cur^=(uint16_t)(m[r2]>>16); acc^=(m[r2]&0xFFFFu); }
    if(acc==0xFFFF){ tot+=8; continue; }
    int pc=__builtin_popcount(acc);
    tot += (pc>0? pc-1 : 0);
    if(!(acc&(1u<<i))) tot+=1;
  }
  return tot;
}
static int retham(const S*s){ int d=0;
  for(int i=0;i<N;i++){ if(PERMA>>i&1){ int b=99; for(int j=0;j<N;j++) if(PERMA>>j&1){ int x=__builtin_popcount(s->r[i]^ST[j]); if(x<b) b=x; } d+=b; }
    else d+=__builtin_popcount(s->r[i]^ST[i]); }
  return d; }
static int rem_terms(const S*s){ int k=0; for(int p=0;p<P;p++) if(!isdone(s,p)) k++; return k; }
static int slack(const S*s){
  int avail=0; for(int i=0;i<N;i++) avail+=DDL[i]-s->wt[i];
  int rem=rem_terms(s); int pend=0; for(int i=0;i<N;i++) if(s->pend[i]>=0) pend++;
  int rc=retcnt(s);
  if(RETW>0){ int rx=(int)(RETW*retcx(s)); if(rx>rc) rc=rx; }
  return avail-(3*rem+pend+2*rc);
}
/* scoring version: charge the empirically observed cost per remaining term
   (~4 slots including its share of routing), so progress is not over-valued */
static double slack_h(const S*s){
  int avail=0; for(int i=0;i<N;i++) avail+=DDL[i]-s->wt[i];
  int rem=rem_terms(s); int pend=0; for(int i=0;i<N;i++) if(s->pend[i]>=0) pend++;
  return avail-(TERMCOST*rem+pend+2.0*retcx(s));
}
static int SLCAP=6; static double WCONC=0.0;
/* per-wire feasibility: a wire that still has to move needs at least one free layer */
static int wfeasible(const S*s){
  int free2=0;
  for(int i=0;i<N;i++) if(DDL[i]-s->wt[i]>=1) free2++;
  int rem=rem_terms(s);
  for(int i=0;i<N;i++){
    int off = (PERMA>>i&1) ? !inSTA(s->r[i]) : (s->r[i]!=ST[i]);
    if(off && DDL[i]-s->wt[i]<1) return 0; }
  if((rem>0 || retcnt(s)>0) && free2<2) return 0;
  return 1;
}
static int complete(const S*s){
  if(rem_terms(s)) return 0;
  if(retcnt(s)) return 0;
  for(int i=0;i<N;i++) if(s->pend[i]>=0 && !(s->lu>>i&1) && s->wt[i]+1>DDL[i]) return 0;
  return 1;
}

/* ---- exact frame-restoration search -------------------------------------
   Once every term is done, what remains is a small CNOT-synthesis problem:
   drive the 8 rows back to ST without passing any wire's deadline.  Each CX
   can retire at most one off-frame wire, so bounding the length by
   retcnt + RETSLACK keeps the branching tiny and the search exhaustive.   */
static int RETSLACK=4; static long RETBUDGET=400000; static long ntry_=0,nelig_=0;
static int retc_[24], rett_[24], retn_=0; static long retnodes_=0;
static int dfs_ret(S s,int depth,int limit){
  if(retnodes_++ > RETBUDGET) return 0;
  if(retcnt(&s)==0){
    for(int i=0;i<N;i++) if(s.pend[i]>=0 && !(s.lu>>i&1) && s.wt[i]+1>DDL[i]) return 0;
    retn_=depth; return 1; }
  if(depth>=limit) return 0;
  if(retcnt(&s) > limit-depth) return 0;
  for(int c=0;c<N;c++) for(int t=0;t<N;t++){
    if(c==t) continue;
    S s2=s;
    if(!apply_cx(&s2,c,t)) continue;
    settle(&s2);
    retc_[depth]=c; rett_[depth]=t;
    if(dfs_ret(s2,depth+1,limit)) return 1; }
  return 0;
}
static int try_return(const S*s){
  int rc=retcnt(s); if(rc==0||rc>6) return 0;
  retnodes_=0;
  for(int lim=rc; lim<=rc+RETSLACK; lim++){ retnodes_=0;
    if(dfs_ret(*s,0,lim)) return 1; }
  return 0;
}
static double score(const S*s){
  int dn=P-rem_terms(s);
  double fr=(double)dn/(double)P;
  double sc=WSLACK*slack_h(s)+WDONE*dn;
  if(fr>0.45) sc-=WRET*2.0*retcx(s); else sc-=WRET*fr*fr*retham(s);
  int r1=0,r2=0; static unsigned char seen[MAXP]; memset(seen,0,P);
  for(int t=0;t<N;t++) for(int c=0;c<N;c++){ if(c==t) continue;
    unsigned v=s->r[t]^s->r[c]; int p=tidx[v];
    if(p>=0 && !seen[p] && !isdone(s,p)){ seen[p]=1; r1++; continue; }
    if(WREACH2>0) for(int c2=0;c2<N;c2++){ if(c2==t) continue; int q=tidx[v^s->r[c2]];
        if(q>=0 && !seen[q] && !isdone(s,q)){ seen[q]=1; r2++; } } }
  if(r1>RCAP1) r1=RCAP1; if(r2>RCAP2) r2=RCAP2;
  sc+=WREACH*r1+WREACH2*r2;
  if(WTIGHT>0){ double q=0;
    for(int i=0;i<N;i++){
      int off = (PERMA>>i&1) ? !inSTA(s->r[i]) : (s->r[i]!=ST[i]);
      if(!off) continue;
      int sl=DDL[i]-s->wt[i];
      if(sl<TIGHT) q += (TIGHT-sl); }
    sc-=WTIGHT*q; }
  if(WCONC>0){ int c=0; for(int i=0;i<N;i++){ int sl=DDL[i]-s->wt[i]; c+= sl<SLCAP?(sl<0?0:sl):SLCAP; } sc+=WCONC*c; }
  if(WBAL>0){ int mx=-30000,sm=0; for(int i=0;i<N;i++){ int sl=DDL[i]-s->wt[i]; sm+=sl; if(-sl>mx) mx=-sl; }
    sc-=WBAL*(mx*N+sm); }
  return sc+NOISE*((xr()&0xFFFFF)/1048576.0)+(xr()&2047)/1e6;
}
static uint64_t hstate(const S*s){
  uint64_t h=s->done[0]*0x9E3779B97F4A7C15ull ^ s->done[1]*0xC2B2AE3D27D4EB4Full;
  for(int i=0;i<N;i++){ h^=((uint64_t)s->r[i]<<8)^((uint64_t)(s->wt[i]+64)<<1)^((s->lu>>i)&1); h*=0x100000001B3ull; h^=h>>29; }
  return h|1;
}
static inline double gumbel(void){ double u=((xr()>>11)+1)/9007199254740994.0; return -log(-log(u)); }
typedef struct { double sc; int idx; } HE;
static int cmpd(const void*a,const void*b){ double x=((HE*)a)->sc,y=((HE*)b)->sc; return x<y?1:x>y?-1:0; }
#define HSZ (1<<23)
int main(int argc,char**argv){
  int W=atoi(argv[1]); int MAXSTEP=atoi(argv[2]); rs^=atoi(argv[3])*0x9E3779B97F4A7C15ull;
  N=atoi(argv[4]); const char*out=argv[5];
  for(int i=0;i<65536;i++) tidx[i]=-1;
  if(scanf("%d",&P)!=1) return 1;
  for(int p=0;p<P;p++){ int m; if(scanf("%d",&m)!=1) return 1; term[p]=m; tidx[m]=p; }
  for(int i=0;i<N;i++){ int st,rd,dl; if(scanf("%d %d %d",&st,&rd,&dl)!=3) return 1; ST[i]=st; RDY[i]=rd; DDL[i]=dl; }
  if(getenv("PERMSET")) PERMA=atoi(getenv("PERMSET"));
  if(getenv("WDONE")) WDONE=atof(getenv("WDONE"));
  if(getenv("WREACH")) WREACH=atof(getenv("WREACH"));
  if(getenv("WREACH2")) WREACH2=atof(getenv("WREACH2"));
  if(getenv("WSLACK")) WSLACK=atof(getenv("WSLACK"));
  if(getenv("WRET")) WRET=atof(getenv("WRET"));
  if(getenv("WBAL")) WBAL=atof(getenv("WBAL"));
  if(getenv("WCONC")) WCONC=atof(getenv("WCONC"));
  if(getenv("RETW")) RETW=atof(getenv("RETW"));
  if(getenv("WTIGHT")) WTIGHT=atof(getenv("WTIGHT"));
  if(getenv("TERMCOST")) TERMCOST=atof(getenv("TERMCOST"));
  if(getenv("NOROAM")) NOROAM=(unsigned)atoi(getenv("NOROAM"));
  if(getenv("RETSLACK")) RETSLACK=atoi(getenv("RETSLACK"));
  if(getenv("MAXUSE")){ const char*q=getenv("MAXUSE"); for(int i=0;i<N;i++){ MAXUSE[i]=atoi(q); while(*q&&*q!=',')q++; if(*q)q++; } HASMAXUSE=1; }
  if(getenv("RETBUDGET")) RETBUDGET=atol(getenv("RETBUDGET"));
  if(getenv("TIGHT")) TIGHT=atoi(getenv("TIGHT"));
  if(getenv("SLCAP")) SLCAP=atoi(getenv("SLCAP"));
  if(getenv("NOISE")) NOISE=atof(getenv("NOISE"));
  if(getenv("GUMB")) GUMB=atof(getenv("GUMB"));
  if(getenv("CHILDCAP")) CHILDCAP=atoi(getenv("CHILDCAP"));
  if(getenv("MAXSKEW")) MAXSKEW=atoi(getenv("MAXSKEW"));
  if(getenv("RCAP1")) RCAP1=atoi(getenv("RCAP1"));
  if(getenv("RCAP2")) RCAP2=atoi(getenv("RCAP2"));
  S s0; memset(&s0,0,sizeof s0);
  for(int i=0;i<N;i++){ s0.r[i]=ST[i]; s0.wt[i]=RDY[i]; s0.pend[i]=-1; }
  s0.par=-1; settle(&s0);
  { int a=0; for(int i=0;i<N;i++) a+=DDL[i]-s0.wt[i];
    fprintf(stderr,"N %d P %d avail %d need>=%d slack %d\n",N,P,a,3*rem_terms(&s0),slack(&s0)); }
  if(slack(&s0)<0){ fprintf(stderr,"INFEASIBLE by slot bound\n"); return 2; }
  S **L=malloc(sizeof(S*)*(MAXSTEP+2)); int *Ln=calloc(MAXSTEP+2,sizeof(int));
  L[0]=malloc(sizeof(S)); L[0][0]=s0; Ln[0]=1;
  int k0=0;
  if(getenv("PREFIX")){
    FILE*pf=fopen(getenv("PREFIX"),"r"); if(!pf) return 3;
    int hd; if(fscanf(pf,"%d",&hd)!=1) return 3;
    int K0=getenv("PREFIXK")?atoi(getenv("PREFIXK")):hd;
    int REPLAY=getenv("REPLAY")?1:0; if(REPLAY) K0=hd;
    if(K0>hd) K0=hd;
    S cur=s0; int c,t;
    for(int k=0;k<K0;k++){ if(fscanf(pf,"%d %d",&c,&t)!=2){ K0=k; break; }
      if(!apply_cx(&cur,c,t)){ fprintf(stderr,"prefix violates deadline at %d\n",k); return 3; }
      settle(&cur); cur.par=0; cur.cc=c; cur.tt=t;
      L[k+1]=malloc(sizeof(S)); L[k+1][0]=cur; Ln[k+1]=1; }
    fclose(pf); k0=K0;
    { int mx=-30000; for(int i=0;i<N;i++) if(cur.wt[i]>mx) mx=cur.wt[i];
      fprintf(stderr,"prefix %d replayed: done %d/%d ret %d slack %d maxwt %d complete %d\n",
        K0,P-rem_terms(&cur),P,retcnt(&cur),slack(&cur),mx,complete(&cur)); }
    if(REPLAY) return 0;
  }
  uint64_t *hk=malloc(sizeof(uint64_t)*HSZ);
  int CAP=W*N*(N-1)+8; S*cand=malloc(sizeof(S)*CAP); HE*he=malloc(sizeof(HE)*CAP);
  int bstep=-1,bidx=-1;
  for(int k=k0;k<MAXSTEP;k++){
    memset(hk,0,sizeof(uint64_t)*HSZ); int nc=0;
    for(int p=0;p<Ln[k];p++){
      const S*ps=&L[k][p]; int pn=0; static S pbuf[64]; static double pscore[64];
      for(int c=0;c<N;c++) for(int t=0;t<N;t++){ if(c==t) continue;
        if(NOROAM>>t&1) continue;          /* this wire may act only as a control */
        int sk=(DDL[c]-ps->wt[c])-(DDL[t]-ps->wt[t]); if(sk<0) sk=-sk; if(sk>MAXSKEW) continue;
        S s=*ps; s.par=p; s.cc=c; s.tt=t;
        if(!apply_cx(&s,c,t)) continue;
        settle(&s);
        if(slack(&s)<0) continue;
        if(!wfeasible(&s)) continue;
        uint64_t h=hstate(&s); uint64_t sl=h&(HSZ-1); int dup=0;
        while(hk[sl]){ if(hk[sl]==h){dup=1;break;} sl=(sl+1)&(HSZ-1);} if(dup) continue; hk[sl]=h;
        double sc2=score(&s); if(GUMB>0) sc2+=GUMB*gumbel();
        if(CHILDCAP>0){
          if(pn<CHILDCAP){ pbuf[pn]=s; pscore[pn]=sc2; pn++; }
          else { int mi=0; for(int q=1;q<CHILDCAP;q++) if(pscore[q]<pscore[mi]) mi=q;
                 if(sc2>pscore[mi]){ pbuf[mi]=s; pscore[mi]=sc2; } } }
        else if(nc<CAP){ cand[nc]=s; he[nc].sc=sc2; he[nc].idx=nc; nc++; } }
      if(CHILDCAP>0) for(int q=0;q<pn;q++) if(nc<CAP){ cand[nc]=pbuf[q]; he[nc].sc=pscore[q]; he[nc].idx=nc; nc++; }
    }
    if(nc==0){ fprintf(stderr,"exhausted at step %d\n",k); break; }
    qsort(he,nc,sizeof(HE),cmpd); int keep=nc<W?nc:W;
    L[k+1]=malloc(sizeof(S)*keep); Ln[k+1]=keep;
    int bdone=0,bsl=-9999,bret=99;
    for(int i=0;i<keep;i++){ L[k+1][i]=cand[he[i].idx]; S*s=&L[k+1][i];
      int dn=P-rem_terms(s); if(dn>bdone) bdone=dn;
      int sl2=slack(s); if(sl2>bsl) bsl=sl2;
      int rc=retcnt(s); if(rc<bret) bret=rc;
      if(bidx<0 && complete(s)){ bstep=k+1; bidx=i; retn_=0; }
      if(bidx<0 && rem_terms(s)==0){ ntry_++; if(retcnt(s)<=6) nelig_++; }
      if(bidx<0 && rem_terms(s)==0 && try_return(s)){ bstep=k+1; bidx=i;
        fprintf(stderr,"exact return found: %d extra CX\n",retn_); } }
    if(k%10==0||bidx>=0) fprintf(stderr,"step %d cand %d kept %d done %d/%d ret %d slack %d | allterms %ld eligible %ld\n",k+1,nc,keep,bdone,P,bret,bsl,ntry_,nelig_);
    if(bidx>=0) break;
  }
  if(bidx<0){
    int lvl=-1; for(int k=MAXSTEP;k>=0;k--) if(Ln[k]>0){ lvl=k; break; }
    if(lvl>=0){ int bi=0,bd=-1;
      for(int i=0;i<Ln[lvl];i++){ int d=P-rem_terms(&L[lvl][i]); int sc=d*100-retcnt(&L[lvl][i]); if(sc>bd){bd=sc;bi=i;} }
      const S*b=&L[lvl][bi];
      fprintf(stderr,"BEST at step %d: done %d/%d ret %d retcx %d slack %d\n",lvl,P-rem_terms(b),P,retcnt(b),retcx(b),slack(b));
      for(int i=0;i<N;i++) fprintf(stderr,"  w%d row %u ST %u wt %d DDL %d slackw %d%s\n",i,b->r[i],ST[i],b->wt[i],DDL[i],DDL[i]-b->wt[i],b->r[i]==ST[i]?"":"  <-- OFF");
      fprintf(stderr,"  undone:"); for(int p2=0;p2<P;p2++) if(!isdone(b,p2)) fprintf(stderr," %u",term[p2]); fprintf(stderr,"\n"); }
    fprintf(stderr,"NOSOL\n"); return 2; }
  int n=bstep; int *cs=malloc(sizeof(int)*n), *ts=malloc(sizeof(int)*n); int idx=bidx;
  for(int k=n;k>=1;k--){ S*s=&L[k][idx]; cs[k-1]=s->cc; ts[k-1]=s->tt; idx=s->par; }
  FILE*f=fopen(out,"w"); fprintf(f,"%d\n",n+retn_);
  for(int i=0;i<n;i++) fprintf(f,"%d %d\n",cs[i],ts[i]);
  for(int i=0;i<retn_;i++) fprintf(f,"%d %d\n",retc_[i],rett_[i]);
  fclose(f);
  { int mx=-30000; for(int i=0;i<N;i++) if(L[bstep][bidx].wt[i]>mx) mx=L[bstep][bidx].wt[i];
    fprintf(stderr,"SOLVED ncx %d maxwt %d\n",n,mx); }
  return 0;
}
