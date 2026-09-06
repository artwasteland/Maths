// Unbiased SIS estimator for the number of LABELED partial triple systems with exactly b blocks on v points
// (leave not prescribed). State: each pair is uncovered / covered / declared-leave. Deterministic rule:
// pick the uncovered pair with the fewest available triangles; branch = (declare it leave) or (one of c triangles).
// Each labeled PTS corresponds to exactly one root-to-leaf path, so prod(c+1) is unbiased.
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#define MAXV 20
static int v,b; static int pid[MAXV][MAXV]; static int np;
static int tripairs[2000][3]; static int nt;
static int pairtris[400][64]; static int npairtris[400];
static unsigned long long rng_s[2];
static inline unsigned long long rotl(unsigned long long x,int k){return (x<<k)|(x>>(64-k));}
static unsigned long long rnd(void){unsigned long long s0=rng_s[0],s1=rng_s[1],r=s0+s1;s1^=s0;rng_s[0]=rotl(s0,55)^s1^(s1<<14);rng_s[1]=rotl(s1,36);return r;}
int main(int argc,char**argv){
  v=atoi(argv[1]); b=atoi(argv[2]); long N=atol(argv[3]); unsigned long long seed=atoll(argv[4]);
  rng_s[0]=seed*0x9E3779B97F4A7C15ULL+1; rng_s[1]=seed^0xD1B54A32D192ED03ULL; for(int i=0;i<20;i++)rnd();
  np=0; for(int i=0;i<v;i++)for(int j=i+1;j<v;j++){pid[i][j]=pid[j][i]=np++;}
  nt=0; memset(npairtris,0,sizeof npairtris);
  for(int i=0;i<v;i++)for(int j=i+1;j<v;j++)for(int k=j+1;k<v;k++){
    int p0=pid[i][j],p1=pid[i][k],p2=pid[j][k];
    tripairs[nt][0]=p0;tripairs[nt][1]=p1;tripairs[nt][2]=p2;
    pairtris[p0][npairtris[p0]++]=nt;pairtris[p1][npairtris[p1]++]=nt;pairtris[p2][npairtris[p2]++]=nt;nt++;}
  int leavemax=np-3*b; if(leavemax<0){printf("too many blocks\n");return 1;}
  double sum=0,sum2=0; long dead=0; static int st[400]; static int avail[400];
  for(long s=0;s<N;s++){
    memset(st,0,sizeof(int)*np); double logw=0; int placed=0, leave=0, ok=1;
    while(placed<b){
      int best=-1,bestc=1<<30;
      for(int p=0;p<np;p++){ if(st[p])continue; int c=0;
        for(int q=0;q<npairtris[p];q++){int t=pairtris[p][q]; if(!st[tripairs[t][0]]&&!st[tripairs[t][1]]&&!st[tripairs[t][2]])c++;}
        if(c<bestc){bestc=c;best=p; if(c==0)break;}
      }
      if(best<0){ok=0;break;}
      int c=0; for(int q=0;q<npairtris[best];q++){int t=pairtris[best][q]; if(!st[tripairs[t][0]]&&!st[tripairs[t][1]]&&!st[tripairs[t][2]])avail[c++]=t;}
      // importance-weighted branch: leave with prob q, else uniform triangle
      int Lrem=leavemax-leave; int Urem=0; for(int p=0;p<np;p++) if(!st[p])Urem++;
      double q;
      if(c==0){ if(Lrem<=0){ok=0;break;} q=1.0; }
      else if(Lrem<=0) q=0.0;
      else { q=(double)Lrem/(double)Urem; if(q<0.01)q=0.01; if(q>0.9)q=0.9; }
      double u=(double)(rnd()>>11)/9007199254740992.0;
      if(u<q){ st[best]=2; leave++; logw+=log(1.0/q); }
      else { int t=avail[rnd()%c]; st[tripairs[t][0]]=st[tripairs[t][1]]=st[tripairs[t][2]]=1; placed++; logw+=log((double)c/(1.0-q)); }
    }
    double w= ok? exp(logw):0; if(!ok)dead++; sum+=w; sum2+=w*w;
  }
  double m=sum/N, var=sum2/N-m*m, se=sqrt(var/N);
  double lf=lgamma(v+1);
  printf("v=%d b=%d N=%ld dead=%ld labeled=%.4e relse=%.3f  labeled/v!=%.4e\n",v,b,N,dead,m,m>0?se/m:0,m/exp(lf));
  return 0;
}
