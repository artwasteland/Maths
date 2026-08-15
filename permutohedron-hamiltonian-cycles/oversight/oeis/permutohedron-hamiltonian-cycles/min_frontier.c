/* Minimise the maximum CUT-FRONTIER (vertex separation) of a linear vertex order
 * of the n-permutohedron graph by simulated annealing; emit the adjacency list in
 * the best order found.  Smaller frontier -> fewer states in the frontier sweep.
 *
 * cut-frontier(order) = max over cut positions p of the number of vertices placed
 * at positions <= p that have a neighbour placed at position > p. (Verified to
 * agree with the independent node checker: bfs order of S5 -> 23.)
 *
 * Build: gcc -O3 -march=native -o min_frontier min_frontier.c -lm
 * Run:   ./min_frontier <n> <seconds> [seed] > best.dat   (frontier -> stderr)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

static int n,N,pc,perms[720][6];
static void gen(int*a,int k){ if(k==n){memcpy(perms[pc++],a,sizeof(int)*n);return;} for(int i=k;i<n;i++){int t=a[k];a[k]=a[i];a[i]=t;gen(a,k+1);t=a[k];a[k]=a[i];a[i]=t;} }
static int pidx(int*p){for(int i=0;i<pc;i++){int ok=1;for(int j=0;j<n;j++)if(perms[i][j]!=p[j]){ok=0;break;}if(ok)return i;}return -1;}
static int nd[720],nbr[720][6];
static int orderOf[720], posOf[720];

/* cut-frontier of current orderOf[]: simple O(N*N) but correct */
static int frontier(){
  /* placedAt[v] = position; a vertex contributes to cut p if pos<=p and some neighbour pos>p */
  static int mx;
  mx=0;
  /* for each vertex, it is "open" across cuts [pos[v], maxNbrPos-1]; the frontier at
     cut p = number of vertices whose open interval covers p. Compute via sweep. */
  static int openStart[720], openEnd[720];
  for(int p=0;p<N;p++){ int v=orderOf[p]; int mxnb=-1; for(int k=0;k<nd[v];k++){int q=posOf[nbr[v][k]]; if(q>mxnb)mxnb=q;}
     openStart[v]=p; openEnd[v]= (mxnb>p)? mxnb-1 : -1; }
  /* difference array over cut positions 0..N-1 */
  static int diff[722];
  for(int p=0;p<=N;p++) diff[p]=0;
  for(int v=0;v<N;v++){ if(openEnd[v]>=openStart[v]){ diff[openStart[v]]++; diff[openEnd[v]+1]--; } }
  int cur=0; for(int p=0;p<N;p++){ cur+=diff[p]; if(cur>mx)mx=cur; }
  return mx;
}

static unsigned long long rng;
static inline unsigned xr(){ rng^=rng<<13; rng^=rng>>7; rng^=rng<<17; return (unsigned)(rng>>11); }
static inline double u01(){ return (xr()&0xFFFFFF)/16777216.0; }

int main(int argc,char**argv){
  n=argc>1?atoi(argv[1]):5; double SECS=argc>2?atof(argv[2]):30; rng=argc>3?strtoull(argv[3],0,10):88172645463325252ULL;
  pc=0; int a[6]; for(int i=0;i<n;i++)a[i]=i; gen(a,0); N=pc;
  for(int i=0;i<N;i++)nd[i]=0;
  for(int i=0;i<N;i++)for(int s=0;s<n-1;s++){int q[6];memcpy(q,perms[i],sizeof(int)*n);int t=q[s];q[s]=q[s+1];q[s+1]=t;int j=pidx(q);
     if(j>=0&&j!=i){int dup=0;for(int k=0;k<nd[i];k++)if(nbr[i][k]==j)dup=1; if(!dup)nbr[i][nd[i]++]=j;}}

  /* seed: BFS order */
  { char seen[720]={0}; int q[720],h=0,t=0; q[t++]=0; seen[0]=1; int p=0;
    while(h<t){int v=q[h++]; orderOf[p++]=v; for(int k=0;k<nd[v];k++){int w=nbr[v][k]; if(!seen[w]){seen[w]=1;q[t++]=w;}}}
    for(int v=0;v<N;v++) if(!seen[v]) orderOf[p++]=v; }
  for(int p=0;p<N;p++) posOf[orderOf[p]]=p;
  int cur=frontier(), best=cur; static int bestOrder[720]; memcpy(bestOrder,orderOf,sizeof(int)*N);
  fprintf(stderr,"seed(bfs) cut-frontier=%d\n",cur);

  double t0=(double)clock()/CLOCKS_PER_SEC; long it=0; double T=2.5;
  while(((double)clock()/CLOCKS_PER_SEC - t0) < SECS){
    for(int b=0;b<3000;b++){ it++;
      int i=xr()%N, j=xr()%N; if(i==j) continue;
      int vi=orderOf[i], vj=orderOf[j];
      orderOf[i]=vj; orderOf[j]=vi; posOf[vi]=j; posOf[vj]=i;
      int cand=frontier();
      if(cand<=cur || u01()<exp((cur-cand)/T)){ cur=cand; if(cur<best){best=cur; memcpy(bestOrder,orderOf,sizeof(int)*N);} }
      else { orderOf[i]=vi; orderOf[j]=vj; posOf[vi]=i; posOf[vj]=j; }
    }
    T*=0.985; if(T<0.03)T=0.03;
  }
  fprintf(stderr,"best cut-frontier=%d after %ld iters\n",best,it);

  memcpy(orderOf,bestOrder,sizeof(int)*N); for(int p=0;p<N;p++) posOf[orderOf[p]]=p;
  fprintf(stderr,"emitted-order cut-frontier=%d\n", frontier());
  for(int p=0;p<N;p++){ int v=orderOf[p]; int rel[6],m=0; for(int k=0;k<nd[v];k++) rel[m++]=posOf[nbr[v][k]]+1;
    for(int x=0;x<m;x++)for(int y=x+1;y<m;y++) if(rel[y]<rel[x]){int tmp=rel[x];rel[x]=rel[y];rel[y]=tmp;}
    for(int x=0;x<m;x++) printf("%d%s", rel[x], x+1<m?" ":""); printf("\n"); }
  return 0;
}
