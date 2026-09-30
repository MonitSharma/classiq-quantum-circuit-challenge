// Kernel SA on NW wires (<=18) with loader profile.
// stdin: NW ; P ; P lines "mask(hex-free decimal)" ; NW lines "startrow e_w lu_w" ; L ; L lines "c t"
// argv: seed iters T0 T1 lam out
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#define MAXW 18
#define MAXP 128
#define MAXL 1500
int NW,P; unsigned ANC=0; unsigned pm[MAXP]; unsigned srow[MAXW]; int ew[MAXW]; int luw[MAXW];
typedef struct { unsigned char c,t; } CX;
static unsigned rs=1; static inline unsigned xr(){ rs^=rs<<13; rs^=rs>>17; rs^=rs<<5; return rs; }
static inline double ur(){ return (xr()&0xFFFFFF)/16777216.0; }
// hash map mask->index (open addressing)
#define HS 4096
unsigned hkey[HS]; int hval[HS];
int hfind(unsigned k){ unsigned h=(k*2654435761u)>>20; while(hval[h]!=-2){ if(hkey[h]==k) return hval[h]; h=(h+1)&(HS-1);} return -1; }
void hput(unsigned k,int v){ unsigned h=(k*2654435761u)>>20; while(hval[h]!=-2) h=(h+1)&(HS-1); hkey[h]=k; hval[h]=v; }
typedef struct { char k; unsigned char a,b; short p; } G;
static G gbuf[5000]; static int gn; static int emit_on=0;
static inline void emitg(char k,int a,int b,int p){ if(emit_on){ gbuf[gn].k=k; gbuf[gn].a=a; gbuf[gn].b=b; gbuf[gn].p=p; gn++; } }
typedef struct { int total; int pen; int sum; } Ev;
int sigma[MAXW];
Ev eval(CX*seq,int L){
  unsigned rows[MAXW]; int wt[MAXW]; char lu[MAXW]; int pend[MAXW]; unsigned char done[MAXP]; memset(done,0,P); int rem=P; gn=0;
  for(int w=0;w<NW;w++){ rows[w]=srow[w]; wt[w]=ew[w]; lu[w]=luw[w]; pend[w]=-1; }
  for(int step=0;step<=L;step++){
    for(int w=0;w<NW;w++){ if(pend[w]>=0) continue; int p=hfind(rows[w]); if(p>=0 && !done[p]){ pend[w]=p; done[p]=1; rem--; } }
    if(step==L) break;
    int c=seq[step].c,t=seq[step].t;
    if(pend[t]>=0){ if(!lu[t]){wt[t]++; lu[t]=1;} emitg('R',t,0,pend[t]); pend[t]=-1; }
    int tau=(wt[c]>wt[t]?wt[c]:wt[t])+1;
    if(pend[c]>=0){ if(lu[c]){ emitg('R',c,0,pend[c]); pend[c]=-1; } else if(wt[c]+1<tau){ wt[c]++; lu[c]=1; emitg('R',c,0,pend[c]); pend[c]=-1; } }
    wt[c]=wt[t]=tau; lu[c]=lu[t]=0; rows[t]^=rows[c]; emitg('C',c,t,-1);
    if(pend[c]>=0){ wt[c]++; lu[c]=1; emitg('R',c,0,pend[c]); pend[c]=-1; }
  }
  for(int w=0;w<NW;w++) if(pend[w]>=0){ if(!lu[w]){wt[w]++; lu[w]=1;} emitg('R',w,0,pend[w]); pend[w]=-1; }
  Ev e; e.total=0; e.sum=0; int mis=0;
  for(int w=0;w<NW;w++){
    int u=-1; for(int k=0;k<NW;k++) if(srow[k]==rows[w]){u=k;break;}
    if(u<0){ mis++; u=w; }
    else if(u!=w && !((ANC>>w&1) && (ANC>>u&1))){ mis++; }
    int tot=wt[w]+ew[u] - ((lu[w]&&luw[u])?1:0); if(tot>e.total) e.total=tot; e.sum+=wt[w];
    if(emit_on) sigma[w]=u;
  }
  e.pen=rem+2*mis; return e;
}
int main(int argc,char**argv){
  rs=atoi(argv[1])*2654435761u+11; long iters=atol(argv[2]); double T0=atof(argv[3]),T1=atof(argv[4]),lam=atof(argv[5]); const char*out=argv[6];
  for(int i=0;i<HS;i++) hval[i]=-2;
  if(scanf("%d %d %u",&NW,&P,&ANC)!=3) return 1;
  for(int p=0;p<P;p++){ if(scanf("%u",&pm[p])!=1) return 1; hput(pm[p],p); }
  for(int w=0;w<NW;w++) if(scanf("%u %d %d",&srow[w],&ew[w],&luw[w])!=3) return 1;
  int L; if(scanf("%d",&L)!=1) return 1;
  CX*cur=malloc(sizeof(CX)*MAXL),*cand=malloc(sizeof(CX)*MAXL),*best=malloc(sizeof(CX)*MAXL);
  for(int i=0;i<L;i++){ int c,t; if(scanf("%d %d",&c,&t)!=2) return 1; cur[i].c=c; cur[i].t=t; }
  Ev ec=eval(cur,L); double cc=ec.total+lam*ec.pen+0.02*ec.sum/NW+0.0005*L;
  memcpy(best,cur,sizeof(CX)*L); int bL=L; Ev eb=ec;
  fprintf(stderr,"init total %d pen %d L %d\n",ec.total,ec.pen,L);
  for(long it=0;it<iters;it++){
    double T=T0*pow(T1/T0,(double)it/iters);
    int nL=L; memcpy(cand,cur,sizeof(CX)*L);
    int mv=xr()%7;
    if(mv==0&&nL>0){ int i=xr()%nL; int x=xr()%NW; if(xr()&1) cand[i].c=x; else cand[i].t=x; if(cand[i].c==cand[i].t) continue; }
    else if(mv==1&&nL<MAXL-1){ int i=xr()%(nL+1); memmove(cand+i+1,cand+i,sizeof(CX)*(nL-i)); int c,t; do{c=xr()%NW;t=xr()%NW;}while(c==t); cand[i].c=c; cand[i].t=t; nL++; }
    else if(mv==2&&nL>1){ int i=xr()%nL; memmove(cand+i,cand+i+1,sizeof(CX)*(nL-i-1)); nL--; }
    else if(mv==3&&nL>1){ int i=xr()%(nL-1); CX tmp=cand[i]; cand[i]=cand[i+1]; cand[i+1]=tmp; }
    else if(mv==4&&nL>2){ int i=xr()%nL,j=xr()%nL; if(i==j) continue; CX tmp=cand[i]; if(i<j){ memmove(cand+i,cand+i+1,sizeof(CX)*(j-i)); cand[j]=tmp; } else { memmove(cand+j+1,cand+j,sizeof(CX)*(i-j)); cand[j]=tmp; } }
    else if(mv==5&&nL>0){ int i=xr()%nL; int c=cand[i].c; cand[i].c=cand[i].t; cand[i].t=c; }
    else if(mv==6&&nL>1){ // delete a matching pair (same cx) - cancellation move
      int i=xr()%nL; int j=-1; for(int k=i+1;k<nL;k++){ if(cand[k].c==cand[i].c&&cand[k].t==cand[i].t){ j=k; break; } }
      if(j<0) continue; memmove(cand+j,cand+j+1,sizeof(CX)*(nL-j-1)); nL--; memmove(cand+i,cand+i+1,sizeof(CX)*(nL-i-1)); nL--; }
    else continue;
    Ev e=eval(cand,nL); double cst=e.total+lam*e.pen+0.02*e.sum/NW+0.0005*nL;
    if(cst<=cc || ur()<exp((cc-cst)/T)){ CX*tmp=cur; cur=cand; cand=tmp; L=nL; cc=cst; ec=e;
      if(e.pen==0 && (eb.pen>0 || e.total<eb.total)){ memcpy(best,cur,sizeof(CX)*L); bL=L; eb=e; } }
    if(it%2000000==0) fprintf(stderr,"it %ld T %.3f cur %d pen %d L %d | best %d pen %d\n",it,T,ec.total,ec.pen,L,eb.total,eb.pen);
  }
  emit_on=1; Ev fe=eval(best,bL); emit_on=0;
  FILE*f=fopen(out,"w"); fprintf(f,"%d %d %d\n",fe.total,fe.pen,bL); for(int w=0;w<NW;w++) fprintf(f,"%d ",sigma[w]); fprintf(f,"\n");
  for(int i=0;i<gn;i++){ if(gbuf[i].k=='R') fprintf(f,"R %d %d\n",gbuf[i].a,gbuf[i].p); else fprintf(f,"C %d %d\n",gbuf[i].a,gbuf[i].b); }
  fclose(f); fprintf(stderr,"final total %d pen %d L %d\n",fe.total,fe.pen,bL); return 0;
}
