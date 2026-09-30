// SA over sequences with delayed target openings (target wires usable as clean helpers before opening).
// stdin: P ; P lines "mask target" ; R ; R lines "vec allowedmask" ; L ; L lines "c t"  (c>=100 -> open target c-100 on wire t)
// argv: seed iters T0 T1 lam mu out
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#define NV 9
#define MAXP 256
#define MAXL 700
#define TB(i) (1u<<(6+(i)))
#define TMASK (7u<<6)
int P,R; unsigned pm[MAXP]; int pt[MAXP]; unsigned rv[16], ra[16]; short pidx[512];
typedef struct { unsigned char c,t; } IT;
static unsigned rs=1; static inline unsigned xr(){ rs^=rs<<13; rs^=rs>>17; rs^=rs<<5; return rs; }
static inline double ur(){ return (xr()&0xFFFFFF)/16777216.0; }
typedef struct { int depth,pen,sumwt; } Ev;
typedef struct { char k; unsigned char a,b; short p; } G;
static G gbuf[5000]; static int gn; static int emit_on=0;
static inline void emitg(char k,int a,int b,int p){ if(emit_on){ gbuf[gn].k=k; gbuf[gn].a=a; gbuf[gn].b=b; gbuf[gn].p=p; gn++; } }
Ev eval(IT*seq,int L){
  unsigned rows[NV]; int wt[NV]; char lu[NV]; int pend[NV]; unsigned char done[MAXP]; memset(done,0,P);
  int remcnt[3]={0,0,0}; for(int p=0;p<P;p++) remcnt[pt[p]]++;
  int closed=0, opened=0, bad=0; gn=0;
  for(int w=0;w<NV;w++){ rows[w]=(w<6)?(1u<<w):0; wt[w]=0; lu[w]=0; pend[w]=-1; }
  for(int step=0;step<=L;step++){
    int changed=1;
    while(changed){ changed=0;
      for(int w=0;w<NV;w++){ if(pend[w]>=0) continue; int p=pidx[rows[w]]; if(p<0||done[p]) continue; int i=pt[p];
        if(!(opened>>i&1)||(closed>>i&1)) continue; unsigned others=pm[p]&TMASK&~TB(i); if(others&~((unsigned)closed<<6)) continue;
        pend[w]=p; done[p]=1; remcnt[i]--; changed=1; }
      for(int i=0;i<3;i++){ if(!(opened>>i&1)||(closed>>i&1)||remcnt[i]) continue;
        int cnt=0,ww=-1; for(int w=0;w<NV;w++) if(rows[w]&TB(i)){cnt++;ww=w;}
        if(cnt!=1) continue; unsigned ob=0; for(int j=0;j<3;j++) if((opened>>j&1)&&!(closed>>j&1)) ob|=TB(j);
        if(rows[ww]&ob&~TB(i)) continue;
        if(pend[ww]>=0){ if(!lu[ww]){wt[ww]++; lu[ww]=1;} emitg('R',ww,0,pend[ww]); pend[ww]=-1; }
        if(!lu[ww]){wt[ww]++; lu[ww]=1;} emitg('H',ww,0,-1); closed|=1<<i; rows[ww]=TB(i); changed=1; }
    }
    if(step==L) break;
    int c=seq[step].c, t=seq[step].t;
    if(c>=100){ int i=c-100; if(i>2||(opened>>i&1)||rows[t]!=0){ bad++; continue; }
      if(pend[t]>=0){ if(!lu[t]){wt[t]++; lu[t]=1;} emitg('R',t,0,pend[t]); pend[t]=-1; }
      if(!lu[t]){wt[t]++; lu[t]=1;} emitg('O',t,i,-1); opened|=1<<i; rows[t]=TB(i); continue; }
    if(pend[t]>=0){ if(!lu[t]){wt[t]++; lu[t]=1;} emitg('R',t,0,pend[t]); pend[t]=-1; }
    int tau=(wt[c]>wt[t]?wt[c]:wt[t])+1;
    if(pend[c]>=0){ if(lu[c]){ emitg('R',c,0,pend[c]); pend[c]=-1; } else if(wt[c]+1<tau){ wt[c]++; lu[c]=1; emitg('R',c,0,pend[c]); pend[c]=-1; } }
    wt[c]=wt[t]=tau; lu[c]=lu[t]=0; rows[t]^=rows[c]; emitg('C',c,t,-1);
    if(pend[c]>=0){ wt[c]++; lu[c]=1; emitg('R',c,0,pend[c]); pend[c]=-1; }
  }
  for(int w=0;w<NV;w++) if(pend[w]>=0){ if(!lu[w]){wt[w]++; lu[w]=1;} emitg('R',w,0,pend[w]); pend[w]=-1; }
  Ev e; e.depth=0; e.sumwt=0; for(int w=0;w<NV;w++){ if(wt[w]>e.depth) e.depth=wt[w]; e.sumwt+=wt[w]; }
  int tot[3]={0,0,0}; for(int p=0;p<P;p++) tot[pt[p]]++;
  int pen=bad*2; for(int i=0;i<3;i++){ pen+=remcnt[i]; if(tot[i]==0){ if(opened>>i&1 && !(closed>>i&1)) pen+=3; continue; } if(!(closed>>i&1)) pen+=3; if(!(opened>>i&1)) pen+=3; }
  int used=0; for(int r=0;r<R;r++){ int ok=0; for(int w=0;w<NV;w++) if((ra[r]>>w&1)&&!(used>>w&1)&&rows[w]==rv[r]){ok=1;used|=1<<w;break;} if(!ok) pen+=2; }
  e.pen=pen; return e;
}
int main(int argc,char**argv){
  rs=atoi(argv[1])*2654435761u+7; long iters=atol(argv[2]); double T0=atof(argv[3]),T1=atof(argv[4]),lam=atof(argv[5]),mu=atof(argv[6]); const char*out=argv[7];
  for(int i=0;i<512;i++) pidx[i]=-1;
  if(scanf("%d",&P)!=1) return 1; for(int p=0;p<P;p++){ if(scanf("%u %d",&pm[p],&pt[p])!=2) return 1; pidx[pm[p]]=p; }
  if(scanf("%d",&R)!=1) return 1; for(int r=0;r<R;r++) if(scanf("%u %u",&rv[r],&ra[r])!=2) return 1;
  int L; if(scanf("%d",&L)!=1) return 1; IT*cur=malloc(sizeof(IT)*MAXL),*cand=malloc(sizeof(IT)*MAXL),*best=malloc(sizeof(IT)*MAXL);
  for(int i=0;i<L;i++){ int c,t; if(scanf("%d %d",&c,&t)!=2) return 1; cur[i].c=c; cur[i].t=t; }
  Ev ec=eval(cur,L); double cc=ec.depth+lam*ec.pen+mu*ec.sumwt/9.0; memcpy(best,cur,sizeof(IT)*L); int bL=L; Ev eb=ec;
  fprintf(stderr,"init depth %d pen %d L %d\n",ec.depth,ec.pen,L);
  for(long it=0;it<iters;it++){
    double T=T0*pow(T1/T0,(double)it/iters);
    int nL=L; memcpy(cand,cur,sizeof(IT)*L); int mv=xr()%8;
    #define RANDCX(x) do{ x.c=xr()%NV; x.t=xr()%NV; }while(x.c==x.t)
    if(mv==0&&nL>0){ int i=xr()%nL; if(cand[i].c>=100){ cand[i].t=xr()%NV; } else { int x=xr()%NV; if(xr()&1) cand[i].c=x; else cand[i].t=x; if(cand[i].c==cand[i].t) continue; } }
    else if(mv==1&&nL<MAXL-1){ int i=xr()%(nL+1); memmove(cand+i+1,cand+i,sizeof(IT)*(nL-i)); RANDCX(cand[i]); nL++; }
    else if(mv==2&&nL>1){ int i=xr()%nL; if(cand[i].c>=100) continue; memmove(cand+i,cand+i+1,sizeof(IT)*(nL-i-1)); nL--; }
    else if(mv==3&&nL>1){ int i=xr()%(nL-1); IT tmp=cand[i]; cand[i]=cand[i+1]; cand[i+1]=tmp; }
    else if(mv==4&&nL>2){ int i=xr()%nL,j=xr()%nL; if(i==j) continue; IT tmp=cand[i]; if(i<j){ memmove(cand+i,cand+i+1,sizeof(IT)*(j-i)); cand[j]=tmp; } else { memmove(cand+j+1,cand+j,sizeof(IT)*(i-j)); cand[j]=tmp; } }
    else if(mv==5&&nL>0){ int i=xr()%nL; if(cand[i].c>=100) continue; int c=cand[i].c; cand[i].c=cand[i].t; cand[i].t=c; }
    else if(mv==6&&nL>3){ int i=xr()%nL; if(cand[i].c>=100) continue; memmove(cand+i,cand+i+1,sizeof(IT)*(nL-i-1)); nL--; int j=xr()%(nL+1); memmove(cand+j+1,cand+j,sizeof(IT)*(nL-j)); RANDCX(cand[j]); nL++; }
    else if(mv==7&&nL<MAXL-3){ // insert a copy pair: cx(a,b) at i and cx(a,b) at j>i (temporary)
      int i=xr()%(nL+1), j=xr()%(nL+1); if(j<i){int x=i;i=j;j=x;} IT g; RANDCX(g); memmove(cand+j+1,cand+j,sizeof(IT)*(nL-j)); cand[j]=g; nL++; memmove(cand+i+1,cand+i,sizeof(IT)*(nL-i)); cand[i]=g; nL++; }
    else continue;
    Ev e=eval(cand,nL); double cst=e.depth+lam*e.pen+mu*e.sumwt/9.0;
    if(cst<=cc||ur()<exp((cc-cst)/T)){ IT*tmp=cur; cur=cand; cand=tmp; L=nL; cc=cst; ec=e;
      if(e.pen==0&&(eb.pen>0||e.depth<eb.depth)){ memcpy(best,cur,sizeof(IT)*L); bL=L; eb=e; } }
    if(it%2000000==0) fprintf(stderr,"it %ld T %.3f cur %d pen %d L %d | best %d pen %d\n",it,T,ec.depth,ec.pen,L,eb.depth,eb.pen);
  }
  emit_on=1; Ev fe=eval(best,bL); emit_on=0;
  FILE*f=fopen(out,"w"); fprintf(f,"%d %d %d\n",fe.depth,fe.pen,bL);
  for(int i=0;i<gn;i++){ if(gbuf[i].k=='O') fprintf(f,"O %d %d\n",gbuf[i].a,gbuf[i].b); else if(gbuf[i].k=='H') fprintf(f,"H %d\n",gbuf[i].a); else if(gbuf[i].k=='R') fprintf(f,"R %d %d\n",gbuf[i].a,gbuf[i].p); else fprintf(f,"C %d %d\n",gbuf[i].a,gbuf[i].b); }
  fclose(f); fprintf(stderr,"final depth %d pen %d L %d\n",fe.depth,fe.pen,bL); return 0;
}
