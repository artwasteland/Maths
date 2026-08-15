/* Knuth (1975) random-sampling estimate of the size of the backtracking tree
 * used by count.c to enumerate Hamiltonian cycles of the n-permutohedron.
 * Each random dive multiplies the number of VALID children at each level;
 * the running product is an unbiased estimator of the number of leaves
 * (≈ the work). Average over many dives. This tells us, in seconds, whether
 * the exact enumeration is feasible (10^7 leaves: trivial; 10^13: hopeless).
 *
 * Uses exactly the same pruning as count.c so the estimate matches the real run.
 * Build: gcc -O3 -march=native -o estimate estimate.c
 * Run:   ./estimate 5 [num_samples]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

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
static inline void unmark(int v){visited&=~(((u128)1)<<v);for(int k=0;k<ndeg[v];k++)avail[nbr[v][k]]++;}
static inline int connected(int head){
  u128 allowed=((~visited)&FULL)|(((u128)1)<<START)|(((u128)1)<<head);
  u128 reached=((u128)1)<<head, frontier=reached;
  while(frontier){u128 next=0,f=frontier; while(f){int v;uint64_t lo=(uint64_t)f; if(lo)v=__builtin_ctzll(lo); else v=64+__builtin_ctzll((uint64_t)(f>>64)); next|=ADJ[v]; f&=f-(u128)1;} next&=allowed&~reached; reached|=next; frontier=next;}
  return (allowed&~reached)==0; }
static inline int degOK(int head){
  u128 f=(~visited)&FULL; u128 hb=ADJ[head]; u128 sb=(head!=START)?ADJ[START]:(u128)0;
  while(f){int u;uint64_t lo=(uint64_t)f; if(lo)u=__builtin_ctzll(lo); else u=64+__builtin_ctzll((uint64_t)(f>>64)); f&=f-(u128)1;
    if(avail[u]+(int)((hb>>u)&1)+(int)((sb>>u)&1)<2)return 0;} return 1; }

/* valid children of (head,depth): neighbors w that pass the same gate as count.c */
static int validChildren(int head,int depth,int*out){
  int c=0;
  for(int k=0;k<ndeg[head];k++){int w=nbr[head][k]; if((visited>>w)&1)continue;
    mark(w);
    int ok=0;
    if(avail[START]>0||depth+1==N){ if(depth+1==N){ ok=1; } else if(degOK(w)&&connected(w)) ok=1; }
    unmark(w);
    if(ok) out[c++]=w;
  }
  return c;
}

static uint64_t rng=0x9e3779b97f4a7c15ULL;
static inline uint64_t xr(){ rng^=rng<<13; rng^=rng>>7; rng^=rng<<17; return rng; }

int main(int argc,char**argv){
  int n=argc>1?atoi(argv[1]):5; long S=argc>2?atol(argv[2]):200000;
  build(n);
  printf("n=%d V=%d deg=%d  sampling %ld dives\n",n,N,ndeg[0],S);
  double sumLeaves=0.0, sumNodes=0.0;
  for(long s=0;s<S;s++){
    visited=0; for(int i=0;i<N;i++)avail[i]=ndeg[i];
    mark(START);
    /* fix first move arbitrarily among START's neighbors as a child level too */
    int head=START, depth=1; double est=1.0, nodes=1.0; int out[6];
    while(1){
      int c;
      if(depth==N){ break; }              /* full path reached (a real cycle leaf) */
      c=validChildren(head,depth,out);
      if(c==0) break;                       /* dead leaf */
      est*=c; nodes+=est;                   /* est = estimated #nodes at this level */
      int pick=out[xr()%c];
      mark(pick); head=pick; depth++;
    }
    sumLeaves+=est; sumNodes+=nodes;
    /* unwind not needed: we reset visited each dive */
  }
  double leaves=sumLeaves/S, totnodes=sumNodes/S;
  printf("estimated leaves  ~ %.3e\n", leaves);
  printf("estimated nodes   ~ %.3e  (total backtracking-tree size)\n", totnodes);
  return 0;
}
