// lseq: CX-sequence beam search for the conditional loader, using the EXACT sa4
// timing model (lazy rotations, fusion with a preceding 1q gate, slack placement).
// Instead of committing to layers, it grows the CX sequence one gate at a time and
// keeps the states with the most slack against a hard depth budget DMAX.
//
// stdin : P ; P lines "mask target" ; [NREQ ; req...] ; [NFREE ; free masks...]
// argv  : W maxsteps seed DMAX out
// env   : WDONE WREACH WREACH2 WCLOSED WSPAN NREQNEED SEQOUT
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#define NW 9
#define TB(i) (1u<<(6+(i)))
#define TMASK (7u<<6)
#define MAXP 256
typedef struct {
  uint16_t r[NW];
  uint8_t  wt[NW];
  uint16_t lu;                 /* bit w: last op on wire w was a 1q gate at time wt[w] */
  int16_t  pend[NW];
  uint64_t done[4];
  uint8_t  closed, dn[4];
  int32_t  par; int8_t cc, tt;
} S;
static int P, NREQ=0, NFREE=0, SPANNEED=0;
static unsigned pm[MAXP]; static int pt[MAXP];
static short pidx[512], fidx[512];
static int totcnt[4];
static unsigned reqv[8]; static unsigned char inspan[512]; static unsigned char spanidx[512];
double BLKW[16]; double WBLK=0;
static int DMAX; static int EXTRA=14; static int bestKeyD=9999, bestKeyS=99999;
static double WDONE=0, WREACH=1.2, WREACH2=0.25, WCLOSED=6.0, WSLACK=1.0, WSPANV=2.0;
static int RCAP1=14, RCAP2=24; static int MAXSKEW=99; static double WBAL=0, WCLEAN=6.0, WEARLY=0;
static double NOISE=0.0, GUMB=0.0; static int CHILDCAP=0;
static uint64_t rs=88172645463325252ull;
static inline uint64_t xr(){ rs^=rs<<13; rs^=rs>>7; rs^=rs<<17; return rs; }
static inline int isdone(const S*s,int p){ return s->done[p>>6]>>(p&63)&1; }
static inline void setdone(S*s,int p){ s->done[p>>6]|=1ull<<(p&63); }
static inline int allowedm(unsigned mask,int i,uint8_t closed){
  if(i==3) return ((mask&TMASK) & ~((unsigned)closed<<6))==0;
  if(closed>>i&1) return 0;
  return ((mask&TMASK&~TB(i)) & ~((unsigned)closed<<6))==0;
}
static inline int allowed(const S*s,int p){ return allowedm(pm[p],pt[p],s->closed); }
static inline int remc(const S*s,int i){ return totcnt[i]-s->dn[i]; }
/* mirror of sa4's settle loop */
static int settle(S*s){
  int changed=1;
  while(changed){ changed=0;
    for(int w=0;w<NW;w++){ if(s->pend[w]>=0) continue;
      int p=pidx[s->r[w]];
      if(p>=0 && !isdone(s,p) && allowed(s,p)){ s->pend[w]=p; setdone(s,p); s->dn[pt[p]]++; changed=1; continue; }
      int q=fidx[s->r[w]];
      if(q>=0 && !isdone(s,q) && allowed(s,q)){ s->pend[w]=q; setdone(s,q); s->dn[3]++; changed=1; } }
    for(int i=0;i<3;i++){ if(s->closed>>i&1) continue; if(remc(s,i)) continue;
      int cnt=0, ww=-1; for(int w=0;w<NW;w++) if(s->r[w]&TB(i)){cnt++; ww=w;}
      if(cnt!=1) continue;
      unsigned ob=0; for(int j=0;j<3;j++) if(!(s->closed>>j&1)) ob|=TB(j);
      if(s->r[ww]&ob&~TB(i)) continue;
      if(s->pend[ww]>=0){ if(!(s->lu>>ww&1)){ s->wt[ww]++; s->lu|=1<<ww; if(s->wt[ww]>DMAX) return 0; } s->pend[ww]=-1; }
      if(!(s->lu>>ww&1)){ s->wt[ww]++; s->lu|=1<<ww; if(s->wt[ww]>DMAX) return 0; }
      s->closed|=1<<i; s->r[ww]=TB(i); changed=1; } }
  return 1;
}
static int apply_cx(S*s,int c,int t){
  if(s->pend[t]>=0){ if(!(s->lu>>t&1)){ s->wt[t]++; s->lu|=1<<t; if(s->wt[t]>DMAX) return 0; } s->pend[t]=-1; }
  int tau=(s->wt[c]>s->wt[t]?s->wt[c]:s->wt[t])+1;
  if(s->pend[c]>=0){
    if(s->lu>>c&1){ s->pend[c]=-1; }
    else if(s->wt[c]+1<tau){ s->wt[c]++; s->lu|=1<<c; s->pend[c]=-1; } }
  if(s->wt[c]>DMAX||s->wt[t]>DMAX) return 0;
  if(tau>DMAX) return 0;
  s->wt[c]=s->wt[t]=tau; s->lu&=~((1<<c)|(1<<t));
  s->r[t]^=s->r[c];
  return 1;
}
static int spancnt(const S*s){ int k=0; for(int w=0;w<NW;w++) if(inspan[s->r[w]]) k++; return k; }
/* remaining-work slot bound; returns surplus slots (can be negative -> prune) */
static int slack(const S*s){
  int avail=0; for(int w=0;w<NW;w++) avail+=DMAX-s->wt[w];
  int rem=0; for(int i=0;i<4;i++) rem+=totcnt[i]-s->dn[i];
  int pend=0; for(int w=0;w<NW;w++) if(s->pend[w]>=0) pend++;
  int cl=0, merge=0;
  for(int i=0;i<3;i++){ if(s->closed>>i&1) continue; cl++;
    int cnt=0; for(int w=0;w<NW;w++) if(s->r[w]&TB(i)) cnt++;
    /* to close, the label must end on exactly one wire: cnt-1 merging CXs, of which at
       most remc can double as term-producing moves */
    int ex=cnt-1-remc(s,i); if(ex>0) merge+=2*ex; }
  return avail - (3*rem + pend + cl + merge);
}
static int complete(const S*s){
  if(s->closed!=7) return 0;
  for(int w=0;w<NW;w++) if(s->pend[w]>=0 && !(s->lu>>w&1) && s->wt[w]+1>DMAX) return 0;
  for(int w=0;w<NW;w++) if(s->wt[w]>DMAX) return 0;
  for(int i=0;i<4;i++) if(s->dn[i]!=totcnt[i]) return 0;
  if(NREQ){ int need=SPANNEED?SPANNEED:NREQ; if(spancnt(s)<need) return 0; }
  return 1;
}
static int insum(const S*s){
  int ts[NW],n=0; for(int w=0;w<NW;w++) if(inspan[s->r[w]]) ts[n++]=s->wt[w];
  for(int a=0;a<n;a++) for(int b=a+1;b<n;b++) if(ts[b]<ts[a]){int x=ts[a];ts[a]=ts[b];ts[b]=x;}
  int need=SPANNEED?SPANNEED:NREQ; if(need>n) need=n; int sm=0;
  for(int a=0;a<need;a++) sm+=ts[a]; return sm;
}
static int finaldepth(const S*s){
  int wt[NW]; for(int w=0;w<NW;w++) wt[w]=s->wt[w];
  for(int w=0;w<NW;w++) if(s->pend[w]>=0 && !(s->lu>>w&1)) wt[w]++;
  int d=0; for(int w=0;w<NW;w++) if(wt[w]>d) d=wt[w];
  return d;
}

/* ---- exact endgame: merge label carriers and close, within DMAX ----------
   Merging k carriers of a label needs k-1 CXs, so bounding the search length by
   sum_i (k_i - 1) + CLSLACK keeps it exhaustive and cheap.                       */
static int CLSLACK=3; static long CLBUDGET=300000; static long nalldone_=0, ntried_=0;
static int clc_[24], clt_[24], cln_=0; static long clnodes_=0;
static int all_done(const S*s){ for(int i=0;i<4;i++) if(s->dn[i]!=totcnt[i]) return 0; return 1; }
static int carriers_needed(const S*s){
  int need=0;
  for(int i=0;i<3;i++){ if(s->closed>>i&1) continue; int c=0;
    for(int w=0;w<NW;w++) if(s->r[w]&TB(i)) c++; need+=c-1; }
  return need;
}
static int dfs_close(S s,int depth,int limit){
  if(clnodes_++ > CLBUDGET) return 0;
  if(s.closed==7){
    if(NREQ){ int need=SPANNEED?SPANNEED:NREQ; if(spancnt(&s)<need) return 0; }
    for(int w=0;w<NW;w++) if(s.pend[w]>=0 && !(s.lu>>w&1) && s.wt[w]+1>DMAX) return 0;
    cln_=depth; return 1; }
  if(depth>=limit) return 0;
  if(carriers_needed(&s) > limit-depth) return 0;
  for(int c=0;c<NW;c++) for(int t=0;t<NW;t++){
    if(c==t) continue;
    if(s.pend[t]>=0) continue;
    S s2=s;
    int tau=(s2.wt[c]>s2.wt[t]?s2.wt[c]:s2.wt[t])+1;
    if(tau>DMAX) continue;
    if(s2.pend[c]>=0){ if(s2.lu>>c&1) s2.pend[c]=-1;
      else if(s2.wt[c]+1<tau){ s2.wt[c]++; s2.lu|=1<<c; s2.pend[c]=-1; } }
    s2.wt[c]=s2.wt[t]=tau; s2.lu&=~((1u<<c)|(1u<<t));
    s2.r[t]^=s2.r[c];
    if(!settle(&s2)) continue;
    clc_[depth]=c; clt_[depth]=t;
    if(dfs_close(s2,depth+1,limit)) return 1; }
  return 0;
}
static int try_close(const S*s){
  if(s->closed==7) return 0;
  if(!all_done(s)) return 0;
  int need=carriers_needed(s);
  if(need>10) return 0;
  for(int lim=need; lim<=need+CLSLACK; lim++){ clnodes_=0;
    if(dfs_close(*s,0,lim)) return 1; }
  return 0;
}
static double score(const S*s){
  double sc=WSLACK*slack(s)+WDONE*(s->dn[0]+s->dn[1]+s->dn[2]+s->dn[3])
           +WCLOSED*__builtin_popcount(s->closed);
  int r1=0,r2=0; static unsigned char seen[MAXP]; memset(seen,0,P);
  for(int t=0;t<NW;t++) for(int c=0;c<NW;c++){ if(c==t) continue;
      unsigned v=s->r[t]^s->r[c]; int p=pidx[v];
      if(p>=0 && !seen[p] && !isdone(s,p) && allowed(s,p)){ seen[p]=1; r1++; continue; }
      if(WREACH2>0){ for(int c2=0;c2<NW;c2++){ if(c2==t) continue; int q=pidx[v^s->r[c2]];
          if(q>=0 && !seen[q] && !isdone(s,q) && allowed(s,q)){ seen[q]=1; r2++; } } } }
  if(r1>RCAP1) r1=RCAP1; if(r2>RCAP2) r2=RCAP2;
  sc+=WREACH*r1+WREACH2*r2;
  if(NREQ) sc+=WSPANV*spancnt(s);
  if(WBLK>0 && NREQ){ double q=0; for(int w=0;w<NW;w++) if(inspan[s->r[w]]) q+=BLKW[spanidx[s->r[w]]]*(DMAX-s->wt[w]); sc+=WBLK*q; }
  if(WEARLY>0 && NREQ){ int ts[NW],n=0;
    for(int w=0;w<NW;w++) if(inspan[s->r[w]]) ts[n++]=s->wt[w];
    for(int a=0;a<n;a++) for(int b=a+1;b<n;b++) if(ts[b]<ts[a]){int x=ts[a];ts[a]=ts[b];ts[b]=x;}
    int need=SPANNEED?SPANNEED:NREQ; if(need>n) need=n;
    for(int a=0;a<need;a++) sc+=WEARLY*(DMAX-ts[a]); }
  if(WCLEAN>0) for(int i=0;i<3;i++){ if(s->closed>>i&1) continue;
      if(remc(s,i)>0){ int c2=0; for(int w=0;w<NW;w++) if(s->r[w]&TB(i)) c2++;
        int ex2=c2-1-remc(s,i); if(ex2>0) sc-=WCLEAN*ex2; continue; }
      int cnt=0, bestw=99; unsigned ob=0;
      for(int j=0;j<3;j++) if(!(s->closed>>j&1)) ob|=TB(j);
      for(int w=0;w<NW;w++) if(s->r[w]&TB(i)){ cnt++; if(!(s->r[w]&ob&~TB(i)) && s->wt[w]<bestw) bestw=s->wt[w]; }
      sc-=WCLEAN*(cnt-1); if(bestw<99) sc+=WCLEAN*0.5*(DMAX-bestw); }
  if(WBAL>0){ int mx=0,sm=0; for(int w=0;w<NW;w++){ if(s->wt[w]>mx) mx=s->wt[w]; sm+=s->wt[w]; }
    sc-=WBAL*(mx*NW-sm); }
  return sc+NOISE*((xr()&0xFFFFF)/1048576.0)+(xr()&2047)/1e6;
}
static uint64_t hstate(const S*s){
  uint64_t h=s->done[0]*0x9E3779B97F4A7C15ull ^ s->done[1]*0xC2B2AE3D27D4EB4Full
            ^ s->done[2]*0x165667B19E3779F9ull ^ s->done[3]*0x27D4EB2F165667C5ull ^ s->closed;
  for(int w=0;w<NW;w++){ h^=((uint64_t)s->r[w]<<8)^((uint64_t)s->wt[w]<<1)^((s->lu>>w)&1); h*=0x100000001B3ull; h^=h>>29; }
  return h|1;
}
static inline double gumbel(void){ double u=((xr()>>11)+1)/9007199254740994.0; return -log(-log(u)); }
typedef struct { double sc; int idx; } HE;
static int cmpd(const void*a,const void*b){ double x=((HE*)a)->sc,y=((HE*)b)->sc; return x<y?1:x>y?-1:0; }
#define HSZ (1<<23)
int main(int argc,char**argv){
  int W=atoi(argv[1]); int MAXSTEP=atoi(argv[2]); rs^=atoi(argv[3])*0x9E3779B97F4A7C15ull;
  DMAX=atoi(argv[4]); const char*out=argv[5];
  for(int i=0;i<512;i++){ pidx[i]=-1; fidx[i]=-1; }
  if(scanf("%d",&P)!=1) return 1;
  for(int p=0;p<P;p++){ if(scanf("%u %d",&pm[p],&pt[p])!=2) return 1; pidx[pm[p]]=p; totcnt[pt[p]]++; }
  if(scanf("%d",&NREQ)==1 && NREQ>0){ for(int r=0;r<NREQ;r++) if(scanf("%u",&reqv[r])!=1) return 1;
    for(int b=1;b<(1<<NREQ);b++){ unsigned v=0; for(int r=0;r<NREQ;r++) if(b>>r&1) v^=reqv[r]; if(v) inspan[v]=1; } } else NREQ=0;
  { int nf=0; if(scanf("%d",&nf)==1 && nf>0){ for(int f=0;f<nf;f++){ unsigned mk_; if(scanf("%u",&mk_)!=1) return 1;
        pm[P]=mk_; pt[P]=3; fidx[mk_]=P; P++; totcnt[3]++; } NFREE=nf; } }
  if(getenv("WDONE")) WDONE=atof(getenv("WDONE"));
  if(getenv("WREACH")) WREACH=atof(getenv("WREACH"));
  if(getenv("WREACH2")) WREACH2=atof(getenv("WREACH2"));
  if(getenv("WCLOSED")) WCLOSED=atof(getenv("WCLOSED"));
  if(getenv("WSLACK")) WSLACK=atof(getenv("WSLACK"));
  if(getenv("WSPANV")) WSPANV=atof(getenv("WSPANV"));
  if(getenv("SPANNEED")) SPANNEED=atoi(getenv("SPANNEED"));
  if(getenv("EXTRA")) EXTRA=atoi(getenv("EXTRA"));
  if(getenv("CLSLACK")) CLSLACK=atoi(getenv("CLSLACK"));
  if(getenv("CLBUDGET")) CLBUDGET=atol(getenv("CLBUDGET"));
  if(getenv("WEARLY")) WEARLY=atof(getenv("WEARLY"));
  if(getenv("BLKW")){ const char*q=getenv("BLKW"); for(int b=1;b<16;b++){ BLKW[b]=atof(q); while(*q&&*q!=',')q++; if(*q)q++; } WBLK=1.0; }
  if(getenv("WBLK")) WBLK=atof(getenv("WBLK"));
  if(getenv("WCLEAN")) WCLEAN=atof(getenv("WCLEAN"));
  if(getenv("NOISE")) NOISE=atof(getenv("NOISE"));
  if(getenv("GUMB")) GUMB=atof(getenv("GUMB"));
  if(getenv("CHILDCAP")) CHILDCAP=atoi(getenv("CHILDCAP"));
  if(getenv("MAXSKEW")) MAXSKEW=atoi(getenv("MAXSKEW"));
  if(getenv("WBAL")) WBAL=atof(getenv("WBAL"));
  if(getenv("RCAP1")) RCAP1=atoi(getenv("RCAP1"));
  if(getenv("RCAP2")) RCAP2=atoi(getenv("RCAP2"));
  fprintf(stderr,"P %d cnt %d %d %d %d DMAX %d W %d\n",P,totcnt[0],totcnt[1],totcnt[2],totcnt[3],DMAX,W);
  S **L=malloc(sizeof(S*)*(MAXSTEP+2)); int *Ln=calloc(MAXSTEP+2,sizeof(int));
  S s0; memset(&s0,0,sizeof s0);
  for(int w=0;w<NW;w++){ s0.r[w]=1<<w; s0.wt[w]=0; s0.pend[w]=-1; }
  for(int i=0;i<3;i++){ int w=6+i; s0.wt[w]=1; s0.lu|=1<<w; }
  s0.par=-1; if(!settle(&s0)) return 1;
  L[0]=malloc(sizeof(S)); L[0][0]=s0; Ln[0]=1;
  int k0=0;
  if(getenv("PREFIX")){
    FILE*pf=fopen(getenv("PREFIX"),"r"); if(!pf){ fprintf(stderr,"no prefix file\n"); return 3; }
    int hd1,hd2; if(fscanf(pf,"%d %d",&hd1,&hd2)!=2) return 3;
    int K0=getenv("PREFIXK")?atoi(getenv("PREFIXK")):hd2;
    int REPLAY=getenv("REPLAY")?1:0; if(REPLAY) K0=hd2;
    int c,t; S cur=s0;
    for(int k=0;k<K0;k++){ if(fscanf(pf,"%d %d",&c,&t)!=2){ K0=k; break; }
      if(!apply_cx(&cur,c,t)){ fprintf(stderr,"prefix exceeds DMAX at %d\n",k); return 3; }
      if(!settle(&cur)){ fprintf(stderr,"prefix exceeds DMAX in settle at %d\n",k); return 3; } cur.par=0; cur.cc=c; cur.tt=t;
      L[k+1]=malloc(sizeof(S)); L[k+1][0]=cur; Ln[k+1]=1; }
    fclose(pf); k0=K0;
    fprintf(stderr,"prefix %d gates replayed: done %d/%d closed %d depth %d slack %d complete %d\n",
      K0,cur.dn[0]+cur.dn[1]+cur.dn[2]+cur.dn[3],P,cur.closed,finaldepth(&cur),slack(&cur),complete(&cur));
    if(REPLAY) return 0;
  }
  int ANLEN=0; static int anc_[600], ant_[600]; S anchor; int anchorIdx=-1, anchorOK=0;
  if(getenv("ANCHOR")){
    FILE*af=fopen(getenv("ANCHOR"),"r"); int h1,h2;
    if(af && fscanf(af,"%d %d",&h1,&h2)==2){
      while(ANLEN<600 && fscanf(af,"%d %d",&anc_[ANLEN],&ant_[ANLEN])==2) ANLEN++;
      fclose(af);
      anchor=L[k0][0]; anchorIdx=0; anchorOK=1;
      fprintf(stderr,"anchor loaded %d gates (from step %d)\n",ANLEN,k0);
    }
  }
  uint64_t *hk=malloc(sizeof(uint64_t)*HSZ);
  int CAP=W*72+8; S*cand=malloc(sizeof(S)*CAP); HE*he=malloc(sizeof(HE)*CAP);
  int bestd=999, bstep=-1, bidx=-1;
  for(int k=k0;k<MAXSTEP;k++){
    memset(hk,0,sizeof(uint64_t)*HSZ); int nc=0;
    for(int p=0;p<Ln[k];p++){
      const S*ps=&L[k][p]; int pn=0; static S pbuf[64]; static double pscore[64];
      for(int c=0;c<NW;c++) for(int t=0;t<NW;t++){ if(c==t) continue;
        int sk=ps->wt[c]-ps->wt[t]; if(sk<0) sk=-sk; if(sk>MAXSKEW) continue;
        S s=*ps; s.par=p; s.cc=c; s.tt=t;
        if(!apply_cx(&s,c,t)) continue;
        if(!settle(&s)) continue;
        if(slack(&s)<0) continue;
        { int free2=0, bad=0;
          for(int w=0;w<NW;w++) if(DMAX-s.wt[w]>=1) free2++;
          for(int i=0;i<3 && !bad;i++){
            if(s.closed>>i&1) continue;
            int cnt=0, okw=0, cfree=0;
            for(int w=0;w<NW;w++) if(s.r[w]&TB(i)){ cnt++; int f=DMAX-s.wt[w]; if(f>=1) okw=1; if(f>0) cfree+=f; }
            if(cnt>1 && free2<2) bad=1;
            if(!okw) bad=1;
            /* merging cnt carriers into one costs a layer on each of the two wires per
               merge, plus one layer on the survivor for its closing H */
            if(cfree < 2*(cnt-1)+1) bad=1;
          }
          if(bad) continue; }

        uint64_t h=hstate(&s); uint64_t sl=h&(HSZ-1); int dup=0;
        while(hk[sl]){ if(hk[sl]==h){dup=1;break;} sl=(sl+1)&(HSZ-1);} if(dup) continue; hk[sl]=h;
        double sc2=score(&s); if(GUMB>0) sc2+=GUMB*gumbel();
        if(CHILDCAP>0){
          if(pn<CHILDCAP){ pbuf[pn]=s; pscore[pn]=sc2; pn++; }
          else { int mi=0; for(int q=1;q<CHILDCAP;q++) if(pscore[q]<pscore[mi]) mi=q;
                 if(sc2>pscore[mi]){ pbuf[mi]=s; pscore[mi]=sc2; } }
        } else if(nc<CAP){ cand[nc]=s; he[nc].sc=sc2; he[nc].idx=nc; nc++; } }
      if(CHILDCAP>0){ for(int q=0;q<pn;q++) if(nc<CAP){ cand[nc]=pbuf[q]; he[nc].sc=pscore[q]; he[nc].idx=nc; nc++; } }
    }
    if(nc==0){ fprintf(stderr,"exhausted at step %d\n",k); break; }
    qsort(he,nc,sizeof(HE),cmpd); int keep=nc<W?nc:W;
    L[k+1]=malloc(sizeof(S)*(keep+1)); Ln[k+1]=keep;
    int newAnchor=-1;
    if(anchorOK && k<ANLEN){
      S a=anchor; a.par=anchorIdx; a.cc=anc_[k]; a.tt=ant_[k];
      if(apply_cx(&a,anc_[k],ant_[k]) && settle(&a)){ L[k+1][keep]=a; newAnchor=keep; Ln[k+1]=keep+1; anchor=a; }
      else anchorOK=0;
    } else anchorOK=0;
    int bdone=0, bcl=0, bsl=-999, bmx=99;
    for(int i=0;i<keep;i++){ L[k+1][i]=cand[he[i].idx]; S*s=&L[k+1][i];
      int dn=s->dn[0]+s->dn[1]+s->dn[2]+s->dn[3]; if(dn>bdone) bdone=dn;
      if(__builtin_popcount(s->closed)>bcl) bcl=__builtin_popcount(s->closed);
      int sk=slack(s); if(sk>bsl) bsl=sk;
      if(all_done(s)){ nalldone_++; if(s->closed!=7) ntried_++; }
      if(bidx<0 && !complete(s) && try_close(s)){
        fprintf(stderr,"exact endgame closed with %d extra CX\n",cln_);
        bestKeyD=DMAX; bestKeyS=0; bestd=DMAX; bstep=k+1; bidx=i; }
      if(complete(s)){ int d=finaldepth(s); int sm=insum(s);
        if(d<bestKeyD || (d==bestKeyD && sm<bestKeyS)){ bestKeyD=d; bestKeyS=sm; bestd=d; bstep=k+1; bidx=i;
          fprintf(stderr,"  SOL step %d depth %d insum %d\n",k+1,d,sm); } } }
    for(int i=0;i<keep;i++){ int d=finaldepth(&L[k+1][i]); if(d<bmx) bmx=d; }
    if(k%10==0||bidx>=0) fprintf(stderr,"step %d cand %d kept %d done %d/%d closed %d slack %d best %d | allrot %ld unclosed %ld\n",
        k+1,nc,keep,bdone,P,bcl,bsl,bestd,nalldone_,ntried_);
    if(newAnchor>=0){ anchorIdx=newAnchor; S*s=&L[k+1][newAnchor];
      if(complete(s)){ int d=finaldepth(s), sm=insum(s);
        if(d<bestKeyD || (d==bestKeyD && sm<bestKeyS)){ bestKeyD=d; bestKeyS=sm; bestd=d; bstep=k+1; bidx=newAnchor;
          fprintf(stderr,"  ANCHOR SOL step %d depth %d insum %d\n",k+1,d,sm); } } }
    if(bidx>=0 && k+1>=bstep+EXTRA) break;
  }
  if(bidx<0){ fprintf(stderr,"NOSOL DMAX %d\n",DMAX); return 2; }
  /* traceback */
  int n=bstep; int *cs=malloc(sizeof(int)*n), *ts=malloc(sizeof(int)*n);
  int idx=bidx;
  for(int k=n;k>=1;k--){ S*s=&L[k][idx]; cs[k-1]=s->cc; ts[k-1]=s->tt; idx=s->par; }
  FILE*f=fopen(out,"w"); fprintf(f,"%d %d\n",bestd,n+cln_);
  for(int i=0;i<n;i++) fprintf(f,"%d %d\n",cs[i],ts[i]);
  for(int i=0;i<cln_;i++) fprintf(f,"%d %d\n",clc_[i],clt_[i]);
  fclose(f);
  fprintf(stderr,"SOLVED depth %d ncx %d\n",bestd,n);
  return 0;
}
