/* Sequential Importance Sampling (Knuth-style) estimate of the NUMBER of
 * undirected Hamiltonian cycles of the n-permutohedron (bubble-sort) graph.
 *
 * Each dive builds a path from the fixed start, at every step choosing uniformly
 * among the children that survive the SAME pruning gate used by the exact counter
 * count.c (degree>=2 on the residual + connectivity). The running product of the
 * number of valid children is an unbiased estimator: a dive that closes into a
 * Hamiltonian cycle contributes (product of branchings) to the directed-cycle
 * estimate; averaging over many dives estimates the directed count, and /2 the
 * undirected count. We also report the relative standard error.
 *
 * Validate on n=4 (true value 44) before trusting n=5.
 * Build: gcc -O3 -march=native -o sis sis.c
 * Run:   ./sis 5 [num_dives] [seed]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

typedef unsigned __int128 u128;
static int N; static u128 ADJ[720]; static int nbr[720][6], ndeg[720]; static u128 FULL; static int START=0;
static int permcount, perms[720][6];
static void gen(int*a,int k,int n){ if(k==n){memcpy(perms[permcount++],a,sizeof(int)*n);return;}
  for(int i=k;i<n;i++){int t=a[k];a[k]=a[i];a[i]=t;gen(a,k+1,n);t=a[k];a[k]=a[i];a[i]=t;} }
static int pidx(int*p,int n){for(int i=0;i<permcount;i++){int ok=1;for(int j=0;j<n;j++)if(perms[i][j]!=p[j]){ok=0;break;}if(ok)return i;}return -1;}
static void build(int n){ permcount=0; int a[6]; for(int i=0;i<n;i++)a[i]=i; gen(a,0,n); N=permcount;
  for(int i=0;i<N;i++){ADJ[i]=0;ndeg[i]=0;}
  for(int i=0;i<N;i++)for(int s=0;s<n-1;s++){int q[6];memcpy(q,perms[i],sizeof(int)*n);int t=q[s];q[s]=q[s+1];q[s+1]=t;int j=pidx(q,n);
    if(j>=0&&j!=i&&!((ADJ[i]>>j)&1)){ADJ[i]|=((u128)1)<<j;nbr[i][ndeg[i]++]=j;}}
  FULL=(N>=128)?(~(u128)0):((((u128)1)<<N)-1); }

static u128 visited; static int avail[720];
static inline void mark(int v){visited|=((u128)1)<<v;for(int k=0;k<ndeg[v];k++)avail[nbr[v][k]]--;}
static inline int connected(int head){
  u128 allowed=((~visited)&FULL)|(((u128)1)<<START)|(((u128)1)<<head);
  u128 reached=((u128)1)<<head, frontier=reached;
  while(frontier){u128 next=0,f=frontier; while(f){int v;uint64_t lo=(uint64_t)f; if(lo)v=__builtin_ctzll(lo); else v=64+__builtin_ctzll((uint64_t)(f>>64)); next|=ADJ[v]; f&=f-(u128)1;} next&=allowed&~reached; reached|=next; frontier=next;}
  return (allowed&~reached)==0; }
static inline int degOK(int head){
  u128 f=(~visited)&FULL; u128 hb=ADJ[head]; u128 sb=(head!=START)?ADJ[START]:(u128)0;
  while(f){int u;uint64_t lo=(uint64_t)f; if(lo)u=__builtin_ctzll(lo); else u=64+__builtin_ctzll((uint64_t)(f>>64)); f&=f-(u128)1;
    if(avail[u]+(int)((hb>>u)&1)+(int)((sb>>u)&1)<2)return 0;} return 1; }

/* children of (head,depth) that pass the exact counter's gate */
static int kids(int head,int depth,int*out){
  int c=0;
  for(int k=0;k<ndeg[head];k++){int w=nbr[head][k]; if((visited>>w)&1)continue;
    mark(w);
    int ok=0;
    if(avail[START]>0||depth+1==N){ if(degOK(w)&&connected(w)) ok=1; }
    visited&=~(((u128)1)<<w); for(int t=0;t<ndeg[w];t++)avail[nbr[w][t]]++; /* unmark */
    if(ok) out[c++]=w;
  }
  return c;
}

static uint64_t rng;
static inline uint64_t xr(){ rng^=rng<<13; rng^=rng>>7; rng^=rng<<17; return rng; }

int main(int argc,char**argv){
  int n=argc>1?atoi(argv[1]):5; long S=argc>2?atol(argv[2]):2000000;
  rng = argc>3? (uint64_t)strtoull(argv[3],0,10) : 0x243f6a8885a308d3ULL;
  build(n);
  printf("n=%d V=%d deg=%d  SIS dives=%ld\n",n,N,ndeg[0],S);
  double sum=0.0, sumsq=0.0;     /* over directed-cycle estimates per dive */
  long hits=0;
  int out[6];
  for(long s=0;s<S;s++){
    visited=0; for(int i=0;i<N;i++)avail[i]=ndeg[i];
    mark(START);
    int head=START, depth=1; double w=1.0; int dead=0;
    while(depth<N){
      int c=kids(head,depth,out);
      if(c==0){ dead=1; break; }
      w*=c;
      int pick=out[xr()%c];
      mark(pick); head=pick; depth++;
    }
    double contrib=0.0;
    if(!dead && depth==N && ((ADJ[head]>>START)&1)) { contrib=w; hits++; }
    sum+=contrib; sumsq+=contrib*contrib;
  }
  double meanDir=sum/S;                       /* estimated directed cycles */
  double var=(sumsq/S - meanDir*meanDir)/S;   /* variance of the mean */
  double se=sqrt(var>0?var:0);
  double meanUnd=meanDir/2.0, seUnd=se/2.0;
  printf("hits (dives that closed) = %ld / %ld\n", hits, S);
  printf("estimated DIRECTED   cycles = %.6e  (SE %.2e)\n", meanDir, se);
  printf("estimated UNDIRECTED cycles = %.6e  (SE %.2e, rel %.1f%%)\n",
         meanUnd, seUnd, meanUnd>0?100.0*seUnd/meanUnd:0.0);
  return 0;
}
