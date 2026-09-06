// Sequential importance sampling (Knuth estimator) for the number of triangle decompositions
// of K_v minus a given leave graph L. Heuristic: always cover the uncovered edge with the fewest
// available triangles (unbiased for the count of decompositions since the choice of edge is a
// deterministic function of the state). Usage: sis v N seed e1a e1b e2a e2b ...
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#define MAXV 20
static int v; static int pid[MAXV][MAXV]; static int np;
static int tri[2000][3]; static int nt;
static int tripairs[2000][3];
static int pairtris[400][64]; static int npairtris[400];
static unsigned long long rng_s[2];
static inline unsigned long long rotl(unsigned long long x,int k){return (x<<k)|(x>>(64-k));}
static unsigned long long rnd(void){unsigned long long s0=rng_s[0],s1=rng_s[1],r=s0+s1;s1^=s0;rng_s[0]=rotl(s0,55)^s1^(s1<<14);rng_s[1]=rotl(s1,36);return r;}
int main(int argc,char**argv){
  v=atoi(argv[1]); long N=atol(argv[2]); unsigned long long seed=atoll(argv[3]);
  rng_s[0]=seed*0x9E3779B97F4A7C15ULL+1; rng_s[1]=seed^0xD1B54A32D192ED03ULL; for(int i=0;i<20;i++)rnd();
  np=0; for(int i=0;i<v;i++)for(int j=i+1;j<v;j++){pid[i][j]=pid[j][i]=np++;}
  static int leave[400]; memset(leave,0,sizeof leave); int nl=0;
  for(int k=4;k+1<argc;k+=2){int a=atoi(argv[k]),b=atoi(argv[k+1]);leave[pid[a][b]]=1;nl++;}
  nt=0; memset(npairtris,0,sizeof npairtris);
  for(int i=0;i<v;i++)for(int j=i+1;j<v;j++)for(int k=j+1;k<v;k++){
    int p0=pid[i][j],p1=pid[i][k],p2=pid[j][k];
    if(leave[p0]||leave[p1]||leave[p2])continue;
    tri[nt][0]=i;tri[nt][1]=j;tri[nt][2]=k;tripairs[nt][0]=p0;tripairs[nt][1]=p1;tripairs[nt][2]=p2;
    pairtris[p0][npairtris[p0]++]=nt;pairtris[p1][npairtris[p1]++]=nt;pairtris[p2][npairtris[p2]++]=nt;nt++;}
  int need=(np-nl); if(need%3){printf("edge count not divisible by 3\n");return 1;} int steps=need/3;
  double sum=0,sum2=0; long dead=0;
  static int covered[400]; static int avail[400];
  for(long s=0;s<N;s++){
    memcpy(covered,leave,sizeof(int)*np); double logw=0; int ok=1;
    for(int st=0;st<steps;st++){
      int best=-1,bestc=1<<30;
      for(int p=0;p<np;p++){ if(covered[p])continue; int c=0;
        for(int q=0;q<npairtris[p];q++){int t=pairtris[p][q]; if(!covered[tripairs[t][0]]&&!covered[tripairs[t][1]]&&!covered[tripairs[t][2]])avail[c++]=t;}
        if(c<bestc){bestc=c;best=p; if(c<=1)break;}
      }
      if(bestc==0){ok=0;break;}
      // recompute avail for best
      int c=0; for(int q=0;q<npairtris[best];q++){int t=pairtris[best][q]; if(!covered[tripairs[t][0]]&&!covered[tripairs[t][1]]&&!covered[tripairs[t][2]])avail[c++]=t;}
      int t=avail[rnd()%c]; logw+=log((double)c);
      covered[tripairs[t][0]]=covered[tripairs[t][1]]=covered[tripairs[t][2]]=1;
    }
    double w= ok? exp(logw):0; if(!ok)dead++;
    sum+=w; sum2+=w*w;
  }
  double m=sum/N, var=sum2/N-m*m, se=sqrt(var/N);
  printf("v=%d leave_edges=%d triangles_needed=%d N=%ld dead=%ld mean=%.6e relse=%.3f\n",v,nl,steps,N,dead,m,m>0?se/m:0);
  return 0;
}
