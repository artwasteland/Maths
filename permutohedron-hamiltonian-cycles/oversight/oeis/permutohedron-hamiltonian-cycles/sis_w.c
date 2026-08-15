/* Warnsdorff-biased Sequential Importance Sampling for the NUMBER of undirected
 * Hamiltonian cycles of the n-permutohedron (bubble-sort) graph.
 *
 * Same as sis.c, but instead of choosing uniformly among the valid children, it
 * biases toward the most-constrained child (fewest onward valid moves — the
 * Warnsdorff heuristic, which avoids dead ends) and reweights by 1/Prob(choice).
 * The estimator stays UNBIASED (each closing dive contributes 1/ (product of the
 * choice probabilities along its path)); the bias only reduces variance, often by
 * orders of magnitude for rare-event Hamiltonian sampling.
 *
 * Validate on n=4 (true 44) before trusting n=5; compare to the uniform sis.c.
 * Build: gcc -O3 -march=native -o sis_w sis_w.c -lm
 * Run:   ./sis_w 5 [num_dives] [seed] [beta]
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
static inline void markv(int v){visited|=((u128)1)<<v;for(int k=0;k<ndeg[v];k++)avail[nbr[v][k]]--;}
static inline void unmarkv(int v){visited&=~(((u128)1)<<v);for(int k=0;k<ndeg[v];k++)avail[nbr[v][k]]++;}
static inline int connected(int head){
  u128 allowed=((~visited)&FULL)|(((u128)1)<<START)|(((u128)1)<<head);
  u128 reached=((u128)1)<<head, frontier=reached;
  while(frontier){u128 next=0,f=frontier; while(f){int v;uint64_t lo=(uint64_t)f; if(lo)v=__builtin_ctzll(lo); else v=64+__builtin_ctzll((uint64_t)(f>>64)); next|=ADJ[v]; f&=f-(u128)1;} next&=allowed&~reached; reached|=next; frontier=next;}
  return (allowed&~reached)==0; }
static inline int degOK(int head){
  u128 f=(~visited)&FULL; u128 hb=ADJ[head]; u128 sb=(head!=START)?ADJ[START]:(u128)0;
  while(f){int u;uint64_t lo=(uint64_t)f; if(lo)u=__builtin_ctzll(lo); else u=64+__builtin_ctzll((uint64_t)(f>>64)); f&=f-(u128)1;
    if(avail[u]+(int)((hb>>u)&1)+(int)((sb>>u)&1)<2)return 0;} return 1; }
static inline int gateOK(int w,int depth){ /* assumes w already marked; depth = new depth after the move */
  if(!(avail[START]>0||depth==N)) return 0;
  return degOK(w)&&connected(w);
}
/* valid children of (head,depth) -> out[]; depth is CURRENT depth (children land at depth+1) */
static int kids(int head,int depth,int*out){
  int c=0;
  for(int k=0;k<ndeg[head];k++){int w=nbr[head][k]; if((visited>>w)&1)continue;
    markv(w); int ok=gateOK(w,depth+1); unmarkv(w);
    if(ok) out[c++]=w; }
  return c;
}

static uint64_t rng;
static inline uint64_t xr(){ rng^=rng<<13; rng^=rng>>7; rng^=rng<<17; return rng; }
static inline double u01(){ return (xr()>>11)*(1.0/9007199254740992.0); }

int main(int argc,char**argv){
  int n=argc>1?atoi(argv[1]):5; long S=argc>2?atol(argv[2]):2000000;
  rng = argc>3? (uint64_t)strtoull(argv[3],0,10) : 0x243f6a8885a308d3ULL;
  double beta = argc>4? atof(argv[4]) : 2.0;
  build(n);
  printf("n=%d V=%d deg=%d  Warnsdorff-SIS dives=%ld beta=%.2f\n",n,N,ndeg[0],S,beta);
  double sum=0.0,sumsq=0.0; long hits=0; double wmax=0;
  int out[6], gk[6];
  for(long s=0;s<S;s++){
    visited=0; for(int i=0;i<N;i++)avail[i]=ndeg[i];
    markv(START);
    int head=START, depth=1; double w=1.0; int dead=0;
    while(depth<N){
      int c=kids(head,depth,out);
      if(c==0){ dead=1; break; }
      /* score each child by its onward valid-move count (lookahead) */
      double wt[6], sumw=0;
      for(int i=0;i<c;i++){
        markv(out[i]);
        int g=kids(out[i],depth+1,gk);   /* onward options from this child */
        unmarkv(out[i]);
        double sc = pow((double)(g>0?g:1), -beta);  /* fewer onward -> larger weight */
        wt[i]=sc; sumw+=sc;
      }
      double r=u01()*sumw, acc=0; int pick=c-1;
      for(int i=0;i<c;i++){ acc+=wt[i]; if(r<=acc){ pick=i; break; } }
      double p = wt[pick]/sumw;
      w *= 1.0/p;
      markv(out[pick]); head=out[pick]; depth++;
    }
    double contrib=0.0;
    if(!dead && depth==N && ((ADJ[head]>>START)&1)){ contrib=w; hits++; if(w>wmax)wmax=w; }
    sum+=contrib; sumsq+=contrib*contrib;
  }
  double meanDir=sum/S;
  double var=(sumsq/S - meanDir*meanDir)/S; double se=sqrt(var>0?var:0);
  double meanUnd=meanDir/2.0, seUnd=se/2.0;
  printf("hits=%ld/%ld  max single weight=%.3e\n",hits,S,wmax);
  printf("estimated DIRECTED   cycles = %.6e  (SE %.2e)\n", meanDir, se);
  printf("estimated UNDIRECTED cycles = %.6e  (SE %.2e, rel %.2f%%)\n",
         meanUnd, seUnd, meanUnd>0?100.0*seUnd/meanUnd:0.0);
  return 0;
}
