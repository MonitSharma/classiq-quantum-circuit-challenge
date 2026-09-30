// Layer-synchronous beam search for conditional loaders on 9 wires.
// stdin: P; P lines "mask target"; R; R lines "vec allowedmask"
// argv: K M seed alpha beta gamma noise maxlayers out
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#define NV 9
#define MAXP 128
#define TB(i) (1u<<(6+(i)))
#define TMASK (7u<<6)
#define MAXLAY 120
int P,R; unsigned pm[MAXP]; int pt[MAXP]; unsigned rv[8], ra[8]; short pidx[512];
unsigned tmaskp[3]; // not used
typedef struct { unsigned char k,a,b; } Op; // k: 0 rot(a), 1 H(a), 2 cx(a,b)
typedef struct {
  unsigned short rows[NV]; unsigned long long done[2]; unsigned char closed; unsigned char nlay;
  short ndone; double v;
  int parent; unsigned char nops; Op ops[NV];
} St;
static unsigned rs=1; static inline unsigned xr(){ rs^=rs<<13; rs^=rs>>17; rs^=rs<<5; return rs; }
static inline double ur(){ return (xr()&0xFFFFFF)/16777216.0; }
static inline int isdone(const St*s,int p){ return (s->done[p>>6]>>(p&63))&1; }
static inline void setdone(St*s,int p){ s->done[p>>6]|=1ULL<<(p&63); }
static inline unsigned openbits(const St*s){ unsigned o=0; for(int j=0;j<3;j++) if(!(s->closed>>j&1)) o|=TB(j); return o; }
static inline int allowed(const St*s,int p){ int i=pt[p]; if(s->closed>>i&1) return 0; unsigned others=pm[p]&TMASK&~TB(i); unsigned cl=(unsigned)s->closed<<6; return (others&~cl)==0; }
int remaining_target(const St*s,int i){ for(int p=0;p<P;p++) if(pt[p]==i && !isdone(s,p)) return 1; return 0; }
unsigned coord(const unsigned short*rows, unsigned m){
  unsigned r[NV],c[NV]; for(int w=0;w<NV;w++){r[w]=rows[w]; c[w]=1u<<w;}
  int piv[NV],np=0;
  for(int bit=NV-1;bit>=0;bit--){ int k=-1; for(int w=np;w<NV;w++) if(r[w]>>bit&1){k=w;break;} if(k<0) continue;
    unsigned tr=r[k],tc=c[k]; r[k]=r[np]; c[k]=c[np]; r[np]=tr; c[np]=tc;
    for(int w=0;w<NV;w++) if(w!=np&&(r[w]>>bit&1)){ r[w]^=r[np]; c[w]^=c[np]; }
    piv[np]=bit; np++; }
  unsigned res=0; for(int k=0;k<np;k++) if(m>>piv[k]&1) res^=c[k]; return res;
}
double A_,B_,G_,NOISE;
double value(St*s){
  double dist=0; int und=0, blocked=0;
  for(int p=0;p<P;p++){ if(isdone(s,p)) continue; und++; unsigned C=coord(s->rows,pm[p]); int d=__builtin_popcount(C)-1; dist+=d; if(!allowed(s,p)) blocked++; }
  int stray=0; unsigned ob=openbits(s);
  for(int i=0;i<3;i++){ if(s->closed>>i&1) continue; int cnt=0; for(int w=0;w<NV;w++) if(s->rows[w]&TB(i)) cnt++; if(!remaining_target(s,i)) stray+=cnt; }
  int place=0; if(s->closed==7){ int used=0; for(int r=0;r<R;r++){ unsigned C=coord(s->rows,rv[r]); int best=99; for(int w=0;w<NV;w++) if(ra[r]>>w&1){ int d=__builtin_popcount(C)-1+((C>>w&1)?0:1); if(d<best) best=d; } place+=best; } }
  int openc=3-__builtin_popcount(s->closed);
  return s->nlay + A_*und + B_*dist + G_*blocked + 0.7*stray + 0.8*place + 1.5*openc;
}
int finished(St*s){
  if(s->closed!=7) return 0;
  int used=0; for(int r=0;r<R;r++){ int ok=0; for(int w=0;w<NV;w++) if((ra[r]>>w&1)&&!(used>>w&1)&&s->rows[w]==rv[r]){ok=1;used|=1<<w;break;} if(!ok) return 0; } return 1;
}
St *pool; long pooln=0, poolcap;
int main(int argc,char**argv){
  int K=atoi(argv[1]), M=atoi(argv[2]); rs=atoi(argv[3])*2654435761u+3; A_=atof(argv[4]); B_=atof(argv[5]); G_=atof(argv[6]); NOISE=atof(argv[7]); int MAXL=atoi(argv[8]); const char*out=argv[9];
  for(int i=0;i<512;i++) pidx[i]=-1;
  if(scanf("%d",&P)!=1) return 1; for(int p=0;p<P;p++){ if(scanf("%u %d",&pm[p],&pt[p])!=2) return 1; pidx[pm[p]]=p; }
  if(scanf("%d",&R)!=1) return 1; for(int r=0;r<R;r++) if(scanf("%u %u",&rv[r],&ra[r])!=2) return 1;
  poolcap=(long)K*MAXLAY*60+1000; pool=malloc(sizeof(St)*poolcap);
  // root: layer 1 = H on targets (+ fused rotations on pure target parities)
  St root; memset(&root,0,sizeof(St)); for(int w=0;w<NV;w++) root.rows[w]=1u<<w; root.parent=-1; root.nlay=1;
  for(int i=0;i<3;i++){ root.ops[root.nops].k=1; root.ops[root.nops].a=6+i; root.nops++; int p=pidx[TB(i)]; if(p>=0){ root.ops[root.nops].k=0; root.ops[root.nops].a=6+i; root.nops++; setdone(&root,p); root.ndone++; } }
  root.v=value(&root); pool[pooln++]=root;
  long *beam=malloc(sizeof(long)*K), nb=1; beam[0]=0;
  long *cand=malloc(sizeof(long)*K*400); 
  long bestidx=-1;
  for(int lay=2; lay<=MAXL && nb>0; lay++){
    long nc=0;
    for(long bi=0;bi<nb;bi++){
      St *s=&pool[beam[bi]];
      if(finished(s)){ if(bestidx<0) bestidx=beam[bi]; continue; }
      unsigned ob=openbits(s);
      // closings possible now
      int closew[3]={-1,-1,-1};
      for(int i=0;i<3;i++){ if(s->closed>>i&1) continue; if(remaining_target(s,i)) continue; int cnt=0,ww=-1; for(int w=0;w<NV;w++) if(s->rows[w]&TB(i)){cnt++;ww=w;} if(cnt==1 && !(s->rows[ww]&ob&~TB(i))) closew[i]=ww; }
      // pending rotation wires
      int pend[NV]; for(int w=0;w<NV;w++){ int p=pidx[s->rows[w]]; pend[w]=(p>=0&&!isdone(s,p)&&allowed(s,p))?p:-1; }
      // wires busy with H
      int hbusy=0; for(int i=0;i<3;i++) if(closew[i]>=0) hbusy|=1<<closew[i];
      // candidate cx list
      double csc[NV*NV]; int cc[NV*NV], ct[NV*NV]; int ncand=0;
      unsigned Cs[MAXP]; int np2=0; int pidlist[MAXP];
      for(int p=0;p<P;p++) if(!isdone(s,p)){ Cs[np2]=coord(s->rows,pm[p]); pidlist[np2]=p; np2++; }
      for(int c=0;c<NV;c++){ if(hbusy>>c&1) continue; for(int t=0;t<NV;t++){ if(t==c||(hbusy>>t&1)||pend[t]>=0) continue;
        unsigned nw=s->rows[t]^s->rows[c]; if(__builtin_popcount(nw&ob)>1) continue;
        double sc=0; int p=pidx[nw]; if(p>=0&&!isdone(s,p)&&allowed(s,p)) sc+=10;
        for(int i=0;i<3;i++){ if(!(ob&TB(i))) continue; if(remaining_target(s,i)) continue; if((s->rows[t]&TB(i))&&!(nw&TB(i))) sc+=8; if((nw&TB(i))&&!(s->rows[t]&TB(i))) sc-=20; }
        double dd=0; for(int k=0;k<np2;k++){ unsigned C=Cs[k]; if(C>>t&1){ int pc=__builtin_popcount(C); int pc2=(C>>c&1)?pc-1:pc+1; dd+=(1.0/pc2-1.0/pc)*(allowed(s,pidlist[k])?1.0:0.5); } }
        sc+=4.0*dd;
        if(s->closed==7){ // placement progress
          for(int r=0;r<R;r++){ unsigned C=coord(s->rows,rv[r]); if(C>>t&1){ int pc=__builtin_popcount(C); int pc2=(C>>c&1)?pc-1:pc+1; if(pc2<pc) sc+=3; else sc-=1; } }
        }
        sc+=NOISE*ur();
        if(sc<0.3 && !(p>=0&&!isdone(s,p))) continue;
        csc[ncand]=sc; cc[ncand]=c; ct[ncand]=t; ncand++; } }
      // sort candidates desc, keep top M
      for(int i=0;i<ncand;i++) for(int j=i+1;j<ncand;j++) if(csc[j]>csc[i]){ double d=csc[i]; csc[i]=csc[j]; csc[j]=d; int x=cc[i]; cc[i]=cc[j]; cc[j]=x; x=ct[i]; ct[i]=ct[j]; ct[j]=x; }
      if(ncand>M) ncand=M;
      // enumerate matchings via DFS (limit children)
      int nchild=0; int stackc[4],stackt[4];
      // iterative enumeration of subsets up to size 4 with disjoint wires, in greedy-prefix order
      int limit=40;
      // include empty matching too
      int idx[5]; 
      for(int mask_iter=0; mask_iter<1; mask_iter++){}
      // recursive lambda substitute
      int depthsel=0; int choose[4];
      // simple: generate combos by nested loops over sorted candidates
      int combos[400][5]; int ncomb=0;
      combos[ncomb][0]=0; ncomb++;
      for(int a=0;a<ncand&&ncomb<limit;a++){
        combos[ncomb][0]=1; combos[ncomb][1]=a; ncomb++;
        for(int b=a+1;b<ncand&&ncomb<limit;b++){ int wa=(1<<cc[a])|(1<<ct[a]), wb=(1<<cc[b])|(1<<ct[b]); if(wa&wb) continue;
          combos[ncomb][0]=2; combos[ncomb][1]=a; combos[ncomb][2]=b; ncomb++;
          for(int c3=b+1;c3<ncand&&ncomb<limit;c3++){ int w3=(1<<cc[c3])|(1<<ct[c3]); if((wa|wb)&w3) continue;
            combos[ncomb][0]=3; combos[ncomb][1]=a; combos[ncomb][2]=b; combos[ncomb][3]=c3; ncomb++;
            for(int d4=c3+1;d4<ncand&&ncomb<limit;d4++){ int w4=(1<<cc[d4])|(1<<ct[d4]); if((wa|wb|w3)&w4) continue;
              combos[ncomb][0]=4; combos[ncomb][1]=a; combos[ncomb][2]=b; combos[ncomb][3]=c3; combos[ncomb][4]=d4; ncomb++; break; }
          }
        }
      }
      for(int ci=0;ci<ncomb;ci++){
        if(pooln>=poolcap) break;
        St ch=*s; ch.parent=beam[bi]; ch.nops=0; ch.nlay=lay;
        int used=0; for(int q=1;q<=combos[ci][0];q++){ int k=combos[ci][q]; used|=(1<<cc[k])|(1<<ct[k]); }
        // closings
        for(int i=0;i<3;i++) if(closew[i]>=0){ int w=closew[i]; if(pend[w]>=0){ ch.ops[ch.nops].k=0; ch.ops[ch.nops].a=w; ch.nops++; setdone(&ch,pend[w]); ch.ndone++; } ch.ops[ch.nops].k=1; ch.ops[ch.nops].a=w; ch.nops++; }
        // rotations on non-used wires
        for(int w=0;w<NV;w++){ if(pend[w]<0||(used>>w&1)||(hbusy>>w&1)) continue; if(isdone(&ch,pend[w])) continue; ch.ops[ch.nops].k=0; ch.ops[ch.nops].a=w; ch.nops++; setdone(&ch,pend[w]); ch.ndone++; }
        // cx
        for(int q=1;q<=combos[ci][0];q++){ int k=combos[ci][q]; ch.ops[ch.nops].k=2; ch.ops[ch.nops].a=cc[k]; ch.ops[ch.nops].b=ct[k]; ch.nops++; }
        // apply: closings reset rows, cx update
        for(int i=0;i<3;i++) if(closew[i]>=0){ ch.closed|=1<<i; ch.rows[closew[i]]=TB(i); }
        for(int q=1;q<=combos[ci][0];q++){ int k=combos[ci][q]; ch.rows[ct[k]]^=s->rows[cc[k]]; }
        if(ch.nops==0) continue;
        ch.v=value(&ch)+NOISE*0.05*ur();
        pool[pooln]=ch; cand[nc++]=pooln; pooln++;
      }
    }
    if(bestidx>=0) break;
    // select top K unique
    for(long i=0;i<nc;i++) for(long j=i+1;j<nc && j<i+1;j++){}
    // partial sort by v
    for(long i=0;i<nc && i<K*3;i++){ long bj=i; for(long j=i+1;j<nc;j++) if(pool[cand[j]].v<pool[cand[bj]].v) bj=j; long t=cand[i]; cand[i]=cand[bj]; cand[bj]=t; }
    nb=0;
    for(long i=0;i<nc && nb<K && i<K*3;i++){ St*x=&pool[cand[i]]; int dup=0; for(long j=0;j<nb;j++){ St*y=&pool[beam[j]]; if(!memcmp(x->rows,y->rows,sizeof(x->rows))&&x->done[0]==y->done[0]&&x->done[1]==y->done[1]&&x->closed==y->closed){dup=1;break;} } if(!dup) beam[nb++]=cand[i]; }
    if(pooln>=poolcap){ fprintf(stderr,"pool exhausted at layer %d\n",lay); break; }
    if(lay%10==0 && nb>0){ St*b=&pool[beam[0]]; fprintf(stderr,"lay %d nb %ld best v %.1f ndone %d/%d closed %d rows",lay,nb,b->v,b->ndone,P,b->closed); for(int w=0;w<NV;w++) fprintf(stderr," %x",b->rows[w]); fprintf(stderr,"\n"); }
  }
  if(bestidx<0){ for(long bi=0;bi<nb;bi++) if(finished(&pool[beam[bi]])){ bestidx=beam[bi]; break; } }
  FILE*f=fopen(out,"w");
  if(bestidx<0){ fprintf(f,"FAIL\n"); fclose(f); fprintf(stderr,"FAIL\n"); return 0; }
  // backtrack
  long chain[MAXLAY+2]; int nch=0; long x=bestidx; while(x>=0){ chain[nch++]=x; x=pool[x].parent; }
  fprintf(f,"%d\n",pool[bestidx].nlay);
  for(int i=nch-1;i>=0;i--){ St*s=&pool[chain[i]]; for(int k=0;k<s->nops;k++){ Op o=s->ops[k]; if(o.k==0){ // rotation: need parity index -> recompute from parent rows
          St*par = (i<nch-1)? &pool[chain[i+1]] : s; unsigned row=(i<nch-1)? par->rows[o.a] : (1u<<o.a); int p=pidx[row]; fprintf(f,"R %d %d\n",o.a,p); }
      else if(o.k==1) fprintf(f,"H %d\n",o.a); else fprintf(f,"C %d %d\n",o.a,o.b); } }
  fclose(f); fprintf(stderr,"done layers %d pool %ld\n",pool[bestidx].nlay,pooln);
  return 0;
}
