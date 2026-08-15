/* Parallel count of UNDIRECTED Hamiltonian cycles in the n-permutohedron
 * (bubble-sort) graph: Cayley graph of S_n on adjacent transpositions.
 *
 * Same backtracking + pruning as count.c (validated n=3->1, n=4->44), but:
 *   - prefixes are enumerated single-threaded down to depth CUT, producing a
 *     task list;
 *   - the tasks are completed in parallel with OpenMP (thread-local state).
 *
 * Build: gcc -O3 -march=native -fopenmp -o count_par count_par.c
 * Run:   ./count_par 5 [CUT]
 *
 * It prints periodic progress (tasks done / total, running undirected count)
 * so a long run can be monitored and extrapolated.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <omp.h>

typedef unsigned __int128 u128;

static int N;
static u128 ADJ[720];
static int  nbr[720][6];
static int  ndeg[720];
static u128 FULL;
static int  START=0;

static int n_global, permcount, perms[720][6];
static void gen(int*a,int k,int n){ if(k==n){memcpy(perms[permcount++],a,sizeof(int)*n);return;}
  for(int i=k;i<n;i++){int t=a[k];a[k]=a[i];a[i]=t;gen(a,k+1,n);t=a[k];a[k]=a[i];a[i]=t;} }
static int permindex(int*p,int n){ for(int i=0;i<permcount;i++){int ok=1;for(int j=0;j<n;j++)if(perms[i][j]!=p[j]){ok=0;break;}if(ok)return i;} return -1; }
static void build(int n){
  n_global=n; permcount=0; int a[6]; for(int i=0;i<n;i++)a[i]=i; gen(a,0,n); N=permcount;
  for(int i=0;i<N;i++){ADJ[i]=0;ndeg[i]=0;}
  for(int i=0;i<N;i++){ for(int s=0;s<n-1;s++){ int q[6];memcpy(q,perms[i],sizeof(int)*n);
        int t=q[s];q[s]=q[s+1];q[s+1]=t; int j=permindex(q,n);
        if(j>=0&&j!=i&&!((ADJ[i]>>j)&1)){ADJ[i]|=((u128)1)<<j; nbr[i][ndeg[i]++]=j;} } }
  FULL = (N>=128)?(~(u128)0):((((u128)1)<<N)-1);
}

/* ---- thread-local search context ---- */
typedef struct { u128 visited; int avail[720]; unsigned long long count; } Ctx;

static inline int connected(Ctx*c,int head){
  u128 allowed = ((~c->visited)&FULL) | (((u128)1)<<START) | (((u128)1)<<head);
  u128 reached = ((u128)1)<<head, frontier = reached;
  while(frontier){ u128 next=0,f=frontier;
    while(f){ int v; uint64_t lo=(uint64_t)f; if(lo)v=__builtin_ctzll(lo); else v=64+__builtin_ctzll((uint64_t)(f>>64));
      next|=ADJ[v]; f&=f-(u128)1; }
    next &= allowed & ~reached; reached|=next; frontier=next; }
  return (allowed & ~reached)==0;
}
static inline int degOK(Ctx*c,int head){
  u128 f=(~c->visited)&FULL; u128 hb=ADJ[head]; u128 sb=(head!=START)?ADJ[START]:(u128)0;
  while(f){ int u; uint64_t lo=(uint64_t)f; if(lo)u=__builtin_ctzll(lo); else u=64+__builtin_ctzll((uint64_t)(f>>64));
    f&=f-(u128)1;
    int d=c->avail[u]+(int)((hb>>u)&1)+(int)((sb>>u)&1); if(d<2)return 0; }
  return 1;
}
static inline void mark(Ctx*c,int v){ c->visited|=((u128)1)<<v; for(int k=0;k<ndeg[v];k++)c->avail[nbr[v][k]]--; }
static inline void unmark(Ctx*c,int v){ c->visited&=~(((u128)1)<<v); for(int k=0;k<ndeg[v];k++)c->avail[nbr[v][k]]++; }

static void dfs(Ctx*c,int head,int depth){
  if(depth==N){ if((ADJ[head]>>START)&1) c->count++; return; }
  for(int k=0;k<ndeg[head];k++){ int w=nbr[head][k];
    if((c->visited>>w)&1) continue;
    mark(c,w);
    if(c->avail[START]>0 || depth+1==N){ if(degOK(c,w)&&connected(c,w)) dfs(c,w,depth+1); }
    unmark(c,w);
  }
}

/* ---- task generation: enumerate prefixes to depth CUT ---- */
typedef struct { u128 visited; int head; int depth; } Task;
static Task *tasks=NULL; static long ntasks=0, captasks=0;
static int CUT;
static void pushtask(u128 vis,int head,int depth){
  if(ntasks==captasks){ captasks=captasks?captasks*2:1024; tasks=realloc(tasks,captasks*sizeof(Task)); }
  tasks[ntasks].visited=vis; tasks[ntasks].head=head; tasks[ntasks].depth=depth; ntasks++;
}
static void genTasks(Ctx*c,int head,int depth){
  if(depth==CUT){ pushtask(c->visited,head,depth); return; }
  for(int k=0;k<ndeg[head];k++){ int w=nbr[head][k];
    if((c->visited>>w)&1) continue;
    mark(c,w);
    if(c->avail[START]>0 || depth+1==N){ if(degOK(c,w)&&connected(c,w)){
        if(depth+1==CUT) pushtask(c->visited,w,depth+1);
        else genTasks(c,w,depth+1);
    } }
    unmark(c,w);
  }
}

int main(int argc,char**argv){
  int n=argc>1?atoi(argv[1]):5;
  CUT=argc>2?atoi(argv[2]):12;
  build(n);
  fprintf(stderr,"n=%d V=%d deg=%d CUT=%d\n",n,N,ndeg[0],CUT);

  /* generate tasks single-threaded */
  Ctx g; g.visited=0; g.count=0; for(int i=0;i<N;i++)g.avail[i]=ndeg[i];
  mark(&g,START);
  for(int k=0;k<ndeg[START];k++){ int w=nbr[START][k];
    mark(&g,w); genTasks(&g, w, 2); unmark(&g,w);
  }
  fprintf(stderr,"generated %ld tasks at depth %d\n",ntasks,CUT);

  /* complete tasks in parallel */
  unsigned long long total=0;
  long done=0;
  double t0=omp_get_wtime();
  #pragma omp parallel
  {
    Ctx c;
    #pragma omp for schedule(dynamic,1) reduction(+:total)
    for(long ti=0; ti<ntasks; ti++){
      c.visited=tasks[ti].visited; c.count=0;
      for(int i=0;i<N;i++) c.avail[i]=__builtin_popcountll((uint64_t)(ADJ[i]&~c.visited)) + __builtin_popcountll((uint64_t)((ADJ[i]&~c.visited)>>64));
      dfs(&c, tasks[ti].head, tasks[ti].depth);
      total += c.count;
      #pragma omp atomic
      done++;
      if((done & 1023)==0){
        #pragma omp critical
        { fprintf(stderr,"  %ld/%ld tasks  directed=%llu (undirected~%llu)  t=%.0fs\n",
                  done,ntasks,total,total/2,omp_get_wtime()-t0); }
      }
    }
  }
  fprintf(stderr,"DONE %ld tasks t=%.0fs\n",ntasks,omp_get_wtime()-t0);
  printf("n=%d: UNDIRECTED Hamiltonian cycles = %llu\n", n, total/2);
  return 0;
}
