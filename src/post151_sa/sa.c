// Simulated annealing over CX sequences for conditional loaders (9 wires: z0..z5, t0..t2 -> vars 0..8)
// stdin: P ; P lines "mask target" ; R ; R lines "vector allowedmask" ; L ; L lines "c t" (initial seq)
// argv: seed iters T0 T1 lam mu outfile
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#define NV 9
#define MAXP 256
#define MAXL 600
#define TB(i) (1u<<(6+(i)))
#define TMASK (7u<<6)
int P, R; unsigned pm[MAXP]; int pt[MAXP]; unsigned rv[16]; unsigned ra[16];
short pidx[512];
typedef struct { unsigned char c,t; } CX;
static unsigned rs=1; static inline unsigned xr(){ rs^=rs<<13; rs^=rs>>17; rs^=rs<<5; return rs; }
static inline double ur(){ return (xr()&0xFFFFFF)/16777216.0; }
// evaluation result
typedef struct { int depth; int pen; int sumwt; int ncx; } Ev;
// gate emission buffer
typedef struct { char k; unsigned char a,b; short p; } G;
static G gbuf[4000]; static int gn;
static int emit_on=0;
static inline void emitg(char k,int a,int b,int p){ if(emit_on){ gbuf[gn].k=k; gbuf[gn].a=a; gbuf[gn].b=b; gbuf[gn].p=p; gn++; } }
Ev eval(CX *seq, int L){
  unsigned rows[NV]; int wt[NV]; char lu[NV]; int pend[NV];
  unsigned char done[MAXP]; memset(done,0,P);
  int remcnt[3]={0,0,0}; for(int p=0;p<P;p++) remcnt[pt[p]]++;
  int closed=0; gn=0;
  for(int w=0;w<NV;w++){ rows[w]=1u<<w; wt[w]=0; lu[w]=0; pend[w]=-1; }
  for(int i=0;i<3;i++){ int w=6+i; wt[w]=1; lu[w]=1; emitg('H',w,0,-1); }
  // helper macros inline as loops
  #define ALLOWED(p) ( !(closed>>pt[p]&1) && (((pm[p]&TMASK&~TB(pt[p])) & ~((unsigned)closed<<6))==0) )
  for(int step=0; step<=L; step++){
    // settle: mark pending rotations and closings (iterate until stable)
    int changed=1;
    while(changed){ changed=0;
      for(int w=0;w<NV;w++){ if(pend[w]>=0) continue; int p=pidx[rows[w]]; if(p>=0 && !done[p] && ALLOWED(p)){ pend[w]=p; done[p]=1; remcnt[pt[p]]--; changed=1; } }
      for(int i=0;i<3;i++){ if(closed>>i&1) continue; if(remcnt[i]) continue;
        int cnt=0, ww=-1; for(int w=0;w<NV;w++) if(rows[w]&TB(i)){cnt++; ww=w;}
        if(cnt!=1) continue;
        unsigned ob=0; for(int j=0;j<3;j++) if(!(closed>>j&1)) ob|=TB(j);
        if(rows[ww]&ob&~TB(i)) continue;
        // pending rotations on this wire must precede H -> they fuse
        if(pend[ww]>=0){ if(!lu[ww]){ wt[ww]++; lu[ww]=1; } emitg('R',ww,0,pend[ww]); pend[ww]=-1; }
        // wires holding pending rotations involving t_i? none other has t_i
        if(!lu[ww]){ wt[ww]++; lu[ww]=1; } emitg('H',ww,0,-1);
        closed|=1<<i; rows[ww]=TB(i); changed=1;
      }
    }
    if(step==L) break;
    int c=seq[step].c, t=seq[step].t;
    // target pending rotation must be placed before
    if(pend[t]>=0){ if(!lu[t]){ wt[t]++; lu[t]=1; } emitg('R',t,0,pend[t]); pend[t]=-1; }
    int tau=(wt[c]>wt[t]?wt[c]:wt[t])+1;
    if(pend[c]>=0){
      if(lu[c]){ emitg('R',c,0,pend[c]); pend[c]=-1; }
      else if(wt[c]+1<tau){ wt[c]++; lu[c]=1; emitg('R',c,0,pend[c]); pend[c]=-1; }
      // else defer until after cx
    }
    wt[c]=wt[t]=tau; lu[c]=lu[t]=0; rows[t]^=rows[c]; emitg('C',c,t,-1);
    // deferred control rotation can go right after (parity unchanged)
    if(pend[c]>=0){ wt[c]++; lu[c]=1; emitg('R',c,0,pend[c]); pend[c]=-1; }
  }
  for(int w=0;w<NV;w++) if(pend[w]>=0){ if(!lu[w]){wt[w]++; lu[w]=1;} emitg('R',w,0,pend[w]); pend[w]=-1; }
  Ev e; e.depth=0; e.sumwt=0; for(int w=0;w<NV;w++){ if(wt[w]>e.depth) e.depth=wt[w]; e.sumwt+=wt[w]; }
  int pen=0; for(int i=0;i<3;i++){ pen+=remcnt[i]; if(!(closed>>i&1)) pen+=3; }
  // final placement requirements
  int used=0;
  for(int r=0;r<R;r++){ int ok=0; for(int w=0;w<NV;w++) if((ra[r]>>w&1) && !(used>>w&1) && rows[w]==rv[r]){ ok=1; used|=1<<w; break; } if(!ok) pen+=2; }
  e.pen=pen; e.ncx=L; return e;
}
int main(int argc,char**argv){
  rs=atoi(argv[1])*2654435761u+7; long iters=atol(argv[2]); double T0=atof(argv[3]), T1=atof(argv[4]); double lam=atof(argv[5]), mu=atof(argv[6]); const char*out=argv[7]; int CUT=argc>8?atoi(argv[8]):0;
  for(int i=0;i<512;i++) pidx[i]=-1;
  if(scanf("%d",&P)!=1) return 1; for(int p=0;p<P;p++){ if(scanf("%u %d",&pm[p],&pt[p])!=2) return 1; pidx[pm[p]]=p; }
  if(scanf("%d",&R)!=1) return 1; for(int r=0;r<R;r++) if(scanf("%u %u",&rv[r],&ra[r])!=2) return 1;
  int L; if(scanf("%d",&L)!=1) return 1; CX *cur=malloc(sizeof(CX)*MAXL), *cand=malloc(sizeof(CX)*MAXL), *best=malloc(sizeof(CX)*MAXL);
  for(int i=0;i<L;i++){ int c,t; if(scanf("%d %d",&c,&t)!=2) return 1; cur[i].c=c; cur[i].t=t; }
  Ev ec=eval(cur,L); double cc=ec.depth+lam*ec.pen+mu*ec.sumwt/9.0+0.001*L;
  memcpy(best,cur,sizeof(CX)*L); int bL=L; Ev eb=ec; double bc=cc;
  fprintf(stderr,"init depth %d pen %d L %d\n",ec.depth,ec.pen,L);
  for(long it=0; it<iters; it++){
    double T=T0*pow(T1/T0,(double)it/iters);
    int nL=L; memcpy(cand,cur,sizeof(CX)*L);
    int mv=xr()%7;
    if(mv==0 && nL>CUT){ int i=CUT+xr()%(nL-CUT); int c,t; do{ c=xr()%NV; t=xr()%NV; }while(c==t); if(xr()&1) cand[i].c=c; else cand[i].t=t; if(cand[i].c==cand[i].t) continue; }
    else if(mv==1 && nL<MAXL-1){ int i=CUT+xr()%(nL-CUT+1); memmove(cand+i+1,cand+i,sizeof(CX)*(nL-i)); int c,t; do{ c=xr()%NV; t=xr()%NV; }while(c==t); cand[i].c=c; cand[i].t=t; nL++; }
    else if(mv==2 && nL>CUT+1){ int i=CUT+xr()%(nL-CUT); memmove(cand+i,cand+i+1,sizeof(CX)*(nL-i-1)); nL--; }
    else if(mv==3 && nL>CUT+1){ int i=CUT+xr()%(nL-CUT-1); CX tmp=cand[i]; cand[i]=cand[i+1]; cand[i+1]=tmp; }
    else if(mv==4 && nL>CUT+2){ int i=CUT+xr()%(nL-CUT), j=CUT+xr()%(nL-CUT); if(i==j) continue; CX tmp=cand[i]; if(i<j){ memmove(cand+i,cand+i+1,sizeof(CX)*(j-i)); cand[j]=tmp; } else { memmove(cand+j+1,cand+j,sizeof(CX)*(i-j)); cand[j]=tmp; } }
    else if(mv==5 && nL>CUT){ int i=CUT+xr()%(nL-CUT); int c=cand[i].c; cand[i].c=cand[i].t; cand[i].t=c; }
    else if(mv==6 && nL>CUT+3){ // delete then insert elsewhere with random wires (2-change)
      int i=CUT+xr()%(nL-CUT); memmove(cand+i,cand+i+1,sizeof(CX)*(nL-i-1)); nL--; int j=CUT+xr()%(nL-CUT+1); memmove(cand+j+1,cand+j,sizeof(CX)*(nL-j)); int c,t; do{ c=xr()%NV; t=xr()%NV; }while(c==t); cand[j].c=c; cand[j].t=t; nL++; }
    else continue;
    Ev e=eval(cand,nL); double cst=e.depth+lam*e.pen+mu*e.sumwt/9.0+0.001*nL;
    if(cst<=cc || ur()<exp((cc-cst)/T)){ CX*tmp=cur; cur=cand; cand=tmp; L=nL; cc=cst; ec=e;
      if(e.pen==0 && (eb.pen>0 || e.depth<eb.depth || (e.depth==eb.depth && cst<bc))){ memcpy(best,cur,sizeof(CX)*L); bL=L; eb=e; bc=cst; }
    }
    if(it%2000000==0) fprintf(stderr,"it %ld T %.3f cur d %d pen %d L %d | best d %d pen %d\n",it,T,ec.depth,ec.pen,L,eb.depth,eb.pen);
  }
  emit_on=1; Ev fe=eval(best,bL); emit_on=0;
  FILE*f=fopen(out,"w"); fprintf(f,"%d %d %d\n",fe.depth,fe.pen,bL);
  for(int i=0;i<gn;i++){ if(gbuf[i].k=='H') fprintf(f,"H %d\n",gbuf[i].a); else if(gbuf[i].k=='R') fprintf(f,"R %d %d\n",gbuf[i].a,gbuf[i].p); else fprintf(f,"C %d %d\n",gbuf[i].a,gbuf[i].b); }
  fclose(f); fprintf(stderr,"final depth %d pen %d L %d\n",fe.depth,fe.pen,bL);
  return 0;
}
