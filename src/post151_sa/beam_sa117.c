// Anneal an actual layered kernel, keeping every state's wire labels and
// charging both missed phase terms and restoration. CX layers are mutable.
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#define N 8
#define ML 80
uint64_t rng=0x3bd39e10ULL;
uint64_t xr(){rng^=rng<<13;rng^=rng>>7;rng^=rng<<17;return rng;}
double ur(){return (xr()>>11)*0x1p-53;}
int ST[N],ZS[N],XS[N],ZD[N],XD[N],term[256],P,TAU,L;
uint64_t all;
typedef struct{signed char to[N];} Layer;
typedef struct{Layer x[ML];} Net;
typedef struct{double score;int miss,dist,late,touch;uint64_t done;} Ev;
int used(Layer*l,int w){if(l->to[w]>=0)return 1;for(int i=0;i<N;i++)if(l->to[i]==w)return 1;return 0;}
Ev eval(Net*a){
 int rows[N];memcpy(rows,ST,sizeof rows);uint64_t done=0;int late=0,touch=0;
 for(int d=0;d<L;d++){
  int t=TAU+d+1;
  for(int w=0;w<N;w++)if(!used(&a->x[d],w)&&ZS[w]<t&&t<=ZD[w]){int k=term[rows[w]];if(k>=0)done|=1ULL<<k;}
  for(int c=0;c<N;c++)if(a->x[d].to[c]>=0){int b=a->x[d].to[c];rows[b]^=rows[c];touch+=2;late+=(t<=ZS[c]||t>ZD[c]||t<=XS[b]||t>XD[b]);}
  for(int w=0;w<N;w++)if(t==XD[w]&&rows[w]!=ST[w])late+=__builtin_popcount(rows[w]^ST[w]);
 }
 int dist=0;for(int w=0;w<N;w++)dist+=__builtin_popcount(rows[w]^ST[w]);int miss=P-__builtin_popcountll(done);
 Ev r={miss*3.0+dist*2.0+late*2.0+touch*.0002,miss,dist,late,touch,done};return r;
}
void save(Net*a,char*path){FILE*f=fopen(path,"w");fprintf(f,"%d %d\n",L,TAU);for(int d=0;d<L;d++){int k=0;for(int c=0;c<N;c++)k+=a->x[d].to[c]>=0;fprintf(f,"%d",k);for(int c=0;c<N;c++)if(a->x[d].to[c]>=0)fprintf(f," %d %d",c,a->x[d].to[c]);fprintf(f,"\n");}fclose(f);}
int main(int argc,char**argv){
 long iters=atol(argv[1]);rng^=atol(argv[2]);char*out=argv[3];
 scanf("%d %d %d",&P,&TAU,&L);memset(term,-1,sizeof term);for(int i=0;i<P;i++){int m;scanf("%d",&m);term[m]=i;}all=P==64?~0ULL:(1ULL<<P)-1;
 for(int w=0;w<N;w++)scanf("%d %d %d %d %d",&ST[w],&ZS[w],&XS[w],&ZD[w],&XD[w]);
 Net base,cur,cand,best;memset(&base,-1,sizeof base);for(int d=0;d<L;d++){int k;scanf("%d",&k);for(int i=0;i<k;i++){int c,b;scanf("%d %d",&c,&b);base.x[d].to[c]=b;}}
 cur=best=base;Ev ce=eval(&cur),be=ce;fprintf(stderr,"init %.5f miss %d dist %d late %d\n",ce.score,ce.miss,ce.dist,ce.late);
 for(long it=0;it<iters;it++){
  cand=cur;int mv=xr()%7;int d=xr()%L,c=xr()%N,b=xr()%N;if(c==b)continue;
  if(mv==0){if(cand.x[d].to[c]<0){if(used(&cand.x[d],c)||used(&cand.x[d],b))continue;cand.x[d].to[c]=b;}else cand.x[d].to[c]=-1;}
  else if(mv==1){if(cand.x[d].to[c]<0)continue;b=cand.x[d].to[c];cand.x[d].to[c]=-1;cand.x[d].to[b]=c;}
  else if(mv==2||mv==3){if(cand.x[d].to[c]<0)continue;int e=d+((xr()&1)?1:-1);if(e<0||e>=L)continue;b=cand.x[d].to[c];if(used(&cand.x[e],c)||used(&cand.x[e],b))continue;cand.x[d].to[c]=-1;cand.x[e].to[c]=b;}
  else if(mv==4){int e=xr()%L;Layer z=cand.x[d];cand.x[d]=cand.x[e];cand.x[e]=z;}
  else if(mv==5){if(cand.x[d].to[c]<0)continue;int old=cand.x[d].to[c];cand.x[d].to[c]=-1;if(used(&cand.x[d],b)||b==c)continue;cand.x[d].to[c]=b;}
  else {int e=xr()%L;if(e==d)continue;if(used(&cand.x[d],c)||used(&cand.x[d],b)||used(&cand.x[e],c)||used(&cand.x[e],b))continue;cand.x[d].to[c]=b;cand.x[e].to[c]=b;}
  Ev e=eval(&cand);double frac=(it%100000)/(double)100000;double temp=.08+.75*(1-frac)*(1-frac);
  if(e.score<=ce.score||ur()<exp((ce.score-e.score)/temp)){cur=cand;ce=e;if(e.score<be.score){best=cur;be=e;if(be.miss+be.dist+be.late<=3)fprintf(stderr,"it %ld best %.5f miss %d dist %d late %d\n",it,be.score,be.miss,be.dist,be.late);}}
  if(be.miss+be.dist+be.late==0){save(&best,out);fprintf(stderr,"SUCCESS %ld\n",it);return 0;}
  if(it%100000==99999){cur=(xr()%4)?best:base;ce=eval(&cur);}
 }
 save(&best,out);fprintf(stderr,"final %.5f miss %d dist %d late %d\n",be.score,be.miss,be.dist,be.late);return 2;
}
