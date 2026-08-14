/* count.c — fast exact counter of change-ringing sequences by length.
 *
 * Extends the family A324942–A324949 (Sønsteby 2019; all n>=5 entries carry
 * OEIS keyword "more") past their published truncation points.  The object
 * counted is exactly the one defined in ../engine.mjs (a faithful port of
 * Sønsteby's definition, already verified against every published term):
 *
 *   path(L)   = # simple paths of L DISTINCT rows starting at rounds in the
 *               change-ringing graph G_n (vertices = permutations of n bells,
 *               edges = one "change": a nonempty product of disjoint adjacent
 *               transpositions of positions).
 *   cyclic(L) = those whose LAST row is adjacent to rounds (cappable).
 *   noncappable(L) = path(L) - cyclic(L).
 *   Conventions (Sønsteby): path(1)=cyclic(1)=1, noncappable(1)=0.
 *
 * Why this reaches further than the plain DFS in ../engine.mjs:
 *   1. 2-level lookahead — the DFS stops two levels short of maxL; the two
 *      deepest (and totally dominant) levels are counted in O(deg) per node
 *      via incrementally-maintained counters:
 *        cnt[v]  = # currently-visited neighbours of v
 *        cnt2[v] = # currently-visited members of N(v) ∩ N(rounds)
 *      so    #unvisited extensions of u          = deg(u) - cnt[u]
 *            #unvisited cappable extensions of u = d2(u)  - cnt2(u).
 *   2. Symmetry — the map φ(p)[i] = (n-1) - p[(n-1)-i]  (conjugation by the
 *      reversal w0) is an automorphism of G_n fixing rounds and preserving
 *      N(rounds); it pairs up prefixes, so only lexicographically-canonical
 *      prefixes are explored, with weight 2 (or 1 if φ-invariant).  The
 *      automorphism property is ASSERTED over every edge at startup, and
 *      sym-on vs sym-off equality is part of the validation suite.
 *   3. Parallel prefix jobs with checkpointing — prefixes of depth K are
 *      enumerated deterministically; worker threads pull jobs from an atomic
 *      queue; each finished job appends one line to a checkpoint file, so a
 *      killed run resumes without recomputation.
 *
 * Modes:
 *   ./count -n 5 -L 20 -k 7 -t 4 -c ck-n5.txt        # bells mode (symmetric)
 *   ./count -n 5 -L 14 --nosym                        # symmetry off (checks)
 *   ./count -n 5 -L 12 --simple                       # plain DFS, no lookahead
 *   ./count --graph g.txt -L 9 [--simple]             # arbitrary graph (fuzz)
 *
 * Graph file: line 1 "N S" (vertex count, start vertex); then N lines, line v:
 * "d w1 ... wd" (neighbours of v).  Must be undirected, loop-free, dedup'd
 * (asserted).
 *
 * Everything is uint64; the largest count targeted here is ~1e14 << 2^64.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <inttypes.h>
#include <pthread.h>
#include <time.h>
#include <stdatomic.h>

#define MAXL_CAP 64

/* ------------------------------- graph ---------------------------------- */
typedef struct {
  int N;              /* vertices */
  int start;          /* rounds */
  int *off;           /* CSR offsets, N+1 */
  int *adj;           /* CSR neighbours (each vertex's list ascending) */
  uint8_t *inR;       /* v adjacent to start? */
  uint16_t *deg;      /* degree */
  uint16_t *d2;       /* |N(v) ∩ N(start)| */
  int *phi;           /* automorphism (bells mode) or NULL */
  /* mask engine (N <= 128 only): adjacency rows and N(start) as 2-word bitsets */
  uint64_t *amask;    /* N*2 words, or NULL */
  uint64_t rmask[2];
} Graph;

/* ---- permutation utilities (bells mode); ranks are lexicographic Lehmer -- */
static long fact_tab[13];
static void init_fact(void){ fact_tab[0]=1; for(int i=1;i<13;i++) fact_tab[i]=fact_tab[i-1]*i; }

static void rank_to_perm(long rank, int n, int *p){
  int avail[12];
  for(int i=0;i<n;i++) avail[i]=i;
  int m=n;
  for(int i=0;i<n;i++){
    long f=fact_tab[n-1-i];
    int idx=(int)(rank/f); rank%=f;
    p[i]=avail[idx];
    for(int j=idx;j<m-1;j++) avail[j]=avail[j+1];
    m--;
  }
}
static long perm_to_rank(const int *p, int n){
  long rank=0; int seen[12]={0};
  for(int i=0;i<n;i++){
    int smaller=0;
    for(int j=0;j<p[i];j++) if(!seen[j]) smaller++;
    rank += (long)smaller*fact_tab[n-1-i];
    seen[p[i]]=1;
  }
  return rank;
}

/* Rules: nonempty products of disjoint adjacent transpositions of positions.
 * Independent derivation (vs engine.mjs's recursive port): subsets of
 * {s_0..s_{n-2}} with no two ADJACENT indices — bitmasks m in [1, 2^(n-1))
 * with (m & (m<<1)) == 0.  Count must equal Fibonacci(n+1)-1 (A000071). */
static int gen_rules(int n, int rules[][12]){
  int cnt=0;
  for(int m=1; m<(1<<(n-1)); m++){
    if(m & (m<<1)) continue;
    int r[12];
    for(int i=0;i<n;i++) r[i]=i;
    for(int i=0;i<n-1;i++) if(m&(1<<i)){ r[i]=i+1; r[i+1]=i; }
    memcpy(rules[cnt++], r, sizeof(int)*n);
  }
  return cnt;
}

static int cmp_int(const void *a, const void *b){ return *(const int*)a - *(const int*)b; }

static Graph *build_bells_graph(int n){
  init_fact();
  long N=fact_tab[n];
  int rules[256][12];
  int R=gen_rules(n, rules);
  /* Fibonacci(n+1)-1 check */
  long fib[16]; fib[1]=1; fib[2]=1;
  for(int i=3;i<=n+1;i++) fib[i]=fib[i-1]+fib[i-2];
  if(R != fib[n+1]-1){ fprintf(stderr,"rule count %d != Fib(%d)-1\n",R,n+1); exit(1); }

  Graph *G=calloc(1,sizeof(Graph));
  G->N=(int)N; G->start=0;
  G->off=malloc(sizeof(int)*(N+1));
  G->adj=malloc(sizeof(int)*N*R);
  G->deg=malloc(sizeof(uint16_t)*N);
  int p[12], q[12];
  for(long v=0; v<N; v++){
    rank_to_perm(v,n,p);
    int *row=&G->adj[v*R];
    for(int k=0;k<R;k++){
      for(int i=0;i<n;i++) q[i]=p[rules[k][i]];
      row[k]=(int)perm_to_rank(q,n);
    }
    qsort(row,R,sizeof(int),cmp_int);
    for(int k=1;k<R;k++) if(row[k]==row[k-1]){ fprintf(stderr,"dup neighbour\n"); exit(1); }
    for(int k=0;k<R;k++) if(row[k]==v){ fprintf(stderr,"self loop\n"); exit(1); }
    G->off[v]=(int)(v*R); G->deg[v]=(uint16_t)R;
  }
  G->off[N]=(int)(N*R);

  /* φ(p)[i] = (n-1) - p[(n-1)-i]  — conjugation by reversal; fixes rounds */
  G->phi=malloc(sizeof(int)*N);
  for(long v=0;v<N;v++){
    rank_to_perm(v,n,p);
    for(int i=0;i<n;i++) q[i]=(n-1)-p[(n-1)-i];
    G->phi[v]=(int)perm_to_rank(q,n);
  }
  if(G->phi[0]!=0){ fprintf(stderr,"phi does not fix rounds\n"); exit(1); }
  /* assert φ is an automorphism: φ(N(v)) == N(φ(v)) for every v */
  int *tmp=malloc(sizeof(int)*R);
  for(long v=0;v<N;v++){
    const int *row=&G->adj[v*R];
    for(int k=0;k<R;k++) tmp[k]=G->phi[row[k]];
    qsort(tmp,R,sizeof(int),cmp_int);
    const int *prow=&G->adj[(long)G->phi[v]*R];
    if(memcmp(tmp,prow,sizeof(int)*R)!=0){ fprintf(stderr,"phi not an automorphism at v=%ld\n",v); exit(1); }
  }
  free(tmp);
  return G;
}

static Graph *read_graph_file(const char *path){
  FILE *f=fopen(path,"r");
  if(!f){ perror("graph file"); exit(1); }
  Graph *G=calloc(1,sizeof(Graph));
  if(fscanf(f,"%d %d",&G->N,&G->start)!=2){ fprintf(stderr,"bad graph header\n"); exit(1); }
  G->off=malloc(sizeof(int)*(G->N+1));
  G->deg=malloc(sizeof(uint16_t)*G->N);
  int cap=1024, m=0;
  G->adj=malloc(sizeof(int)*cap);
  for(int v=0;v<G->N;v++){
    int d; if(fscanf(f,"%d",&d)!=1){ fprintf(stderr,"bad degree line %d\n",v); exit(1); }
    G->off[v]=m; G->deg[v]=(uint16_t)d;
    for(int k=0;k<d;k++){
      int w; if(fscanf(f,"%d",&w)!=1||w<0||w>=G->N||w==v){ fprintf(stderr,"bad neighbour\n"); exit(1); }
      if(m==cap){ cap*=2; G->adj=realloc(G->adj,sizeof(int)*cap); }
      G->adj[m++]=w;
    }
    qsort(&G->adj[G->off[v]],d,sizeof(int),cmp_int);
    for(int k=1;k<d;k++) if(G->adj[G->off[v]+k]==G->adj[G->off[v]+k-1]){ fprintf(stderr,"dup neighbour\n"); exit(1); }
  }
  G->off[G->N]=m;
  fclose(f);
  /* undirectedness check */
  for(int v=0;v<G->N;v++) for(int k=G->off[v];k<G->off[v+1];k++){
    int w=G->adj[k]; int found=0;
    for(int j=G->off[w];j<G->off[w+1];j++) if(G->adj[j]==v){ found=1; break; }
    if(!found){ fprintf(stderr,"graph not undirected (%d->%d)\n",v,w); exit(1); }
  }
  G->phi=NULL;
  return G;
}

static void finish_graph(Graph *G){
  G->inR=calloc(G->N,1);
  for(int k=G->off[G->start];k<G->off[G->start+1];k++) G->inR[G->adj[k]]=1;
  G->d2=calloc(G->N,sizeof(uint16_t));
  for(int v=0;v<G->N;v++){
    int c=0;
    for(int k=G->off[v];k<G->off[v+1];k++) c+=G->inR[G->adj[k]];
    G->d2[v]=(uint16_t)c;
  }
  if(G->N<=128){
    G->amask=calloc((size_t)G->N*2,sizeof(uint64_t));
    for(int v=0;v<G->N;v++)
      for(int k=G->off[v];k<G->off[v+1];k++){
        int w=G->adj[k];
        G->amask[v*2+(w>>6)] |= 1ULL<<(w&63);
      }
    G->rmask[0]=G->amask[(size_t)G->start*2];
    G->rmask[1]=G->amask[(size_t)G->start*2+1];
  }
}

/* simple deterministic hash of the graph, to guard checkpoint resumes */
static uint64_t graph_hash(const Graph *G){
  uint64_t h=1469598103934665603ULL;
  #define MIX(x) do{ h^=(uint64_t)(x); h*=1099511628211ULL; }while(0)
  MIX(G->N); MIX(G->start);
  for(int v=0;v<=G->N;v++) MIX(G->off[v]);
  for(int k=0;k<G->off[G->N];k++) MIX(G->adj[k]);
  #undef MIX
  return h;
}

/* ------------------------------ counting -------------------------------- */
typedef struct {
  const Graph *G;
  int maxL;
  uint8_t *visited;
  uint8_t *cnt, *cnt2;
  uint64_t vis64[2];                    /* mask engine visited set */
  uint64_t path[MAXL_CAP+1], cyc[MAXL_CAP+1];
} Ctx;

static Ctx *ctx_new(const Graph *G, int maxL){
  Ctx *c=calloc(1,sizeof(Ctx));
  c->G=G; c->maxL=maxL;
  c->visited=calloc(G->N,1);
  c->cnt=calloc(G->N,1);
  c->cnt2=calloc(G->N,1);
  return c;
}

static inline void mark(Ctx *c, int u){
  const Graph *G=c->G;
  c->visited[u]=1;
  if(G->inR[u]){
    for(int k=G->off[u];k<G->off[u+1];k++){ int w=G->adj[k]; c->cnt[w]++; c->cnt2[w]++; }
  } else {
    for(int k=G->off[u];k<G->off[u+1];k++) c->cnt[G->adj[k]]++;
  }
}
static inline void unmark(Ctx *c, int u){
  const Graph *G=c->G;
  c->visited[u]=0;
  if(G->inR[u]){
    for(int k=G->off[u];k<G->off[u+1];k++){ int w=G->adj[k]; c->cnt[w]--; c->cnt2[w]--; }
  } else {
    for(int k=G->off[u];k<G->off[u+1];k++) c->cnt[G->adj[k]]--;
  }
}

/* deep DFS with 2-level lookahead; counts levels depth+1 .. maxL.
 * PRECONDITION: depth <= maxL-2; every vertex on the current path is marked
 * (counter-marked via mark()).
 * At depth maxL-3 the last recursion level is inlined with a "bare mark" (the
 * child u is set visited but its counters are NOT propagated; the lookahead
 * sums are corrected by exactly the child's missing contribution: u is a
 * neighbour of every w in N(u), so deg(w)-cnt[w] overcounts by 1 and
 * d2(w)-cnt2(w) overcounts by inR[u]). */
static void dfs_deep(Ctx *c, int v, int depth){
  const Graph *G=c->G;
  if(depth == c->maxL-2){
    uint64_t pL=0, cL=0, p1=0, c1=0;
    for(int k=G->off[v];k<G->off[v+1];k++){
      int u=G->adj[k];
      if(c->visited[u]) continue;
      p1++; c1+=G->inR[u];
      pL += (uint64_t)(G->deg[u]-c->cnt[u]);
      cL += (uint64_t)(G->d2[u]-c->cnt2[u]);
    }
    c->path[c->maxL-1]+=p1; c->cyc[c->maxL-1]+=c1;
    c->path[c->maxL]+=pL;   c->cyc[c->maxL]+=cL;
    return;
  }
  if(depth == c->maxL-3){
    uint64_t p2=0, c2=0, p1=0, c1=0, pL=0, cL=0;
    for(int k=G->off[v];k<G->off[v+1];k++){
      int u=G->adj[k];
      if(c->visited[u]) continue;
      p2++; c2+=G->inR[u];
      c->visited[u]=1;                       /* bare mark, no counters */
      uint64_t corr2=G->inR[u];
      for(int j=G->off[u];j<G->off[u+1];j++){
        int w=G->adj[j];
        if(c->visited[w]) continue;
        p1++; c1+=G->inR[w];
        pL += (uint64_t)(G->deg[w]-c->cnt[w])-1;
        cL += (uint64_t)(G->d2[w]-c->cnt2[w])-corr2;
      }
      c->visited[u]=0;
    }
    c->path[c->maxL-2]+=p2; c->cyc[c->maxL-2]+=c2;
    c->path[c->maxL-1]+=p1; c->cyc[c->maxL-1]+=c1;
    c->path[c->maxL]+=pL;   c->cyc[c->maxL]+=cL;
    return;
  }
  int nd=depth+1;
  for(int k=G->off[v];k<G->off[v+1];k++){
    int u=G->adj[k];
    if(c->visited[u]) continue;
    c->path[nd]++; c->cyc[nd]+=G->inR[u];
    mark(c,u);
    dfs_deep(c,u,nd);
    unmark(c,u);
  }
}

/* mask engine (N <= 128): visited is two words; the deepest level is counted
 * by AND+popcount against per-vertex adjacency masks — no cnt[] maintenance.
 * PRECONDITION: depth <= maxL-2; path vertices are set in c->vis64. */
static void dfs_mask(Ctx *c, int v, int depth){
  const Graph *G=c->G;
  const uint64_t v0=c->vis64[0], v1=c->vis64[1];
  if(depth == c->maxL-2){
    const uint64_t m0=G->amask[v*2]&~v0, m1=G->amask[v*2+1]&~v1;
    uint64_t p1=(uint64_t)__builtin_popcountll(m0)+__builtin_popcountll(m1);
    uint64_t c1=(uint64_t)__builtin_popcountll(m0&G->rmask[0])
               +__builtin_popcountll(m1&G->rmask[1]);
    uint64_t pL=0, cL=0;
    uint64_t m=m0; int base=0;
    for(int half=0;half<2;half++){
      while(m){
        int w=base+__builtin_ctzll(m); m&=m-1;
        const uint64_t *aw=&G->amask[w*2];
        pL += (uint64_t)G->deg[w]
            - __builtin_popcountll(aw[0]&v0) - __builtin_popcountll(aw[1]&v1);
        cL += (uint64_t)__builtin_popcountll(aw[0]&G->rmask[0]&~v0)
            + __builtin_popcountll(aw[1]&G->rmask[1]&~v1);
      }
      m=m1; base=64;
    }
    c->path[c->maxL-1]+=p1; c->cyc[c->maxL-1]+=c1;
    c->path[c->maxL]+=pL;   c->cyc[c->maxL]+=cL;
    return;
  }
  int nd=depth+1;
  for(int k=G->off[v];k<G->off[v+1];k++){
    int u=G->adj[k];
    if((c->vis64[u>>6]>>(u&63))&1) continue;
    c->path[nd]++; c->cyc[nd]+=G->inR[u];
    c->vis64[u>>6] |= 1ULL<<(u&63);
    dfs_mask(c,u,nd);
    c->vis64[u>>6] &= ~(1ULL<<(u&63));
  }
}

/* plain DFS, no lookahead — the slow reference (--simple), counts 2..maxL */
static void dfs_simple(Ctx *c, int v, int depth){
  const Graph *G=c->G;
  if(depth>=c->maxL) return;
  int nd=depth+1;
  for(int k=G->off[v];k<G->off[v+1];k++){
    int u=G->adj[k];
    if(c->visited[u]) continue;
    c->path[nd]++; c->cyc[nd]+=G->inR[u];
    c->visited[u]=1;
    dfs_simple(c,u,nd);
    c->visited[u]=0;
  }
}

/* ------------------------- prefix enumeration --------------------------- */
typedef struct { int *seq; int weight; } Prefix;
typedef struct {
  Prefix *list; int n, cap; int K;
  const Graph *G; int use_sym;
  int *cur; uint8_t *vis;
} PrefEnum;

static void pref_rec(PrefEnum *E, int v, int depth){
  if(depth==E->K){
    int keep=1, weight=1;
    if(E->use_sym){
      const int *phi=E->G->phi;
      /* compare (cur) with φ(cur) lexicographically; both start at start */
      int cmp=0;
      for(int i=0;i<E->K;i++){
        int a=E->cur[i], b=phi[E->cur[i]];
        if(a!=b){ cmp=(a<b)?-1:1; break; }
      }
      if(cmp>0) keep=0;            /* φ-image is canonical; skip */
      else if(cmp<0) weight=2;     /* canonical of a 2-orbit */
      else weight=1;               /* φ-invariant prefix */
    }
    if(keep){
      if(E->n==E->cap){ E->cap*=2; E->list=realloc(E->list,sizeof(Prefix)*E->cap); }
      Prefix *P=&E->list[E->n++];
      P->seq=malloc(sizeof(int)*E->K);
      memcpy(P->seq,E->cur,sizeof(int)*E->K);
      P->weight=weight;
    }
    return;
  }
  const Graph *G=E->G;
  for(int k=G->off[v];k<G->off[v+1];k++){
    int u=G->adj[k];
    if(E->vis[u]) continue;
    E->vis[u]=1; E->cur[depth]=u;
    pref_rec(E,u,depth+1);
    E->vis[u]=0;
  }
}

static PrefEnum *enumerate_prefixes(const Graph *G, int K, int use_sym){
  PrefEnum *E=calloc(1,sizeof(PrefEnum));
  E->K=K; E->G=G; E->use_sym=use_sym;
  E->cap=1024; E->list=malloc(sizeof(Prefix)*E->cap);
  E->cur=malloc(sizeof(int)*K);
  E->vis=calloc(G->N,1);
  E->cur[0]=G->start; E->vis[G->start]=1;
  pref_rec(E,G->start,1);
  return E;
}

/* ------------------------------ job runner ------------------------------ */
typedef struct {
  const Graph *G; PrefEnum *E;
  int maxL, K, nthreads, use_mask;
  FILE *ck; pthread_mutex_t ck_mu;
  uint8_t *done;                       /* per-job done flag (from checkpoint) */
  _Atomic long next_job;
  _Atomic long jobs_done;
  long total_jobs;
  time_t t0;
} Pool;

static void *worker(void *arg){
  Pool *P=(Pool*)arg;
  Ctx *c=ctx_new(P->G,P->maxL);
  const int K=P->K;
  for(;;){
    long j=atomic_fetch_add_explicit(&P->next_job,1,memory_order_relaxed);
    if(j>=P->total_jobs) break;
    if(P->done[j]){ atomic_fetch_add_explicit(&P->jobs_done,1,memory_order_relaxed); continue; }
    Prefix *pf=&P->E->list[j];
    memset(c->path,0,sizeof(c->path));
    memset(c->cyc,0,sizeof(c->cyc));
    if(P->use_mask){
      c->vis64[0]=c->vis64[1]=0;
      for(int i=0;i<K;i++){ int u=pf->seq[i]; c->vis64[u>>6] |= 1ULL<<(u&63); }
      dfs_mask(c,pf->seq[K-1],K);
    } else {
      for(int i=0;i<K;i++) mark(c,pf->seq[i]);
      dfs_deep(c,pf->seq[K-1],K);
      for(int i=K-1;i>=0;i--) unmark(c,pf->seq[i]);
    }
    /* append checkpoint line: J <id> <weight> <path,cyc pairs for K+1..maxL> */
    pthread_mutex_lock(&P->ck_mu);
    fprintf(P->ck,"J %ld %d",j,pf->weight);
    for(int L=K+1;L<=P->maxL;L++)
      fprintf(P->ck," %" PRIu64 ",%" PRIu64,c->path[L],c->cyc[L]);
    fprintf(P->ck,"\n");
    fflush(P->ck);
    pthread_mutex_unlock(&P->ck_mu);
    atomic_fetch_add_explicit(&P->jobs_done,1,memory_order_relaxed);
  }
  free(c->visited); free(c->cnt); free(c->cnt2); free(c);
  return NULL;
}

/* ------------------------------- main ----------------------------------- */
static void usage(void){
  fprintf(stderr,
    "usage: count -n <bells> -L <maxL> [-k prefixK] [-t threads] [-c ckfile]\n"
    "             [--nosym] [--simple] [--progress sec]\n"
    "       count --graph <file> -L <maxL> [--simple] [-k K] [-t T] [-c ck]\n");
  exit(2);
}

int main(int argc, char **argv){
  int n=0, maxL=0, K=0, nthreads=4, use_sym=1, simple=0, progress=30;
  int engine=-1; /* -1 auto, 0 cnt, 1 mask */
  const char *ckpath=NULL, *gpath=NULL;
  for(int i=1;i<argc;i++){
    if(!strcmp(argv[i],"-n")) n=atoi(argv[++i]);
    else if(!strcmp(argv[i],"-L")) maxL=atoi(argv[++i]);
    else if(!strcmp(argv[i],"-k")) K=atoi(argv[++i]);
    else if(!strcmp(argv[i],"-t")) nthreads=atoi(argv[++i]);
    else if(!strcmp(argv[i],"-c")) ckpath=argv[++i];
    else if(!strcmp(argv[i],"--nosym")) use_sym=0;
    else if(!strcmp(argv[i],"--simple")) simple=1;
    else if(!strcmp(argv[i],"--graph")) gpath=argv[++i];
    else if(!strcmp(argv[i],"--progress")) progress=atoi(argv[++i]);
    else if(!strcmp(argv[i],"--engine")){
      i++;
      if(!strcmp(argv[i],"cnt")) engine=0;
      else if(!strcmp(argv[i],"mask")) engine=1;
      else usage();
    }
    else usage();
  }
  if(maxL<2||maxL>MAXL_CAP) usage();
  if(!gpath&&(n<2||n>10)) usage();

  Graph *G = gpath ? read_graph_file(gpath) : build_bells_graph(n);
  finish_graph(G);
  if(gpath) use_sym=0;
  uint64_t ghash=graph_hash(G);
  fprintf(stderr,"# graph: N=%d start=%d hash=%016" PRIx64 "%s\n",
          G->N,G->start,ghash, gpath?" (file)":" (bells)");

  uint64_t path[MAXL_CAP+1]={0}, cyc[MAXL_CAP+1]={0};
  path[1]=1; cyc[1]=1;   /* Sønsteby's L=1 convention */

  time_t t0=time(NULL);

  if(simple){
    Ctx *c=ctx_new(G,maxL);
    c->visited[G->start]=1;
    dfs_simple(c,G->start,1);
    for(int L=2;L<=maxL;L++){ path[L]=c->path[L]; cyc[L]=c->cyc[L]; }
  } else {
    if(K<2) K = (maxL>=9)?7:2;
    if(K>maxL-2) K=maxL-2;
    if(K<2) K=2;
    /* Phase A: levels 2..K by full (unsymmetrised) DFS — cheap */
    Ctx *ca=ctx_new(G,K);
    ca->visited[G->start]=1;
    dfs_simple(ca,G->start,1);
    for(int L=2;L<=K;L++){ path[L]=ca->path[L]; cyc[L]=ca->cyc[L]; }
    free(ca->visited); free(ca->cnt); free(ca->cnt2); free(ca);

    /* Phase B: prefix jobs for levels K+1..maxL */
    PrefEnum *E=enumerate_prefixes(G,K,use_sym);
    fprintf(stderr,"# K=%d jobs=%d sym=%d threads=%d maxL=%d\n",K,E->n,use_sym,nthreads,maxL);

    Pool P; memset(&P,0,sizeof(P));
    P.G=G; P.E=E; P.maxL=maxL; P.K=K; P.nthreads=nthreads;
    P.use_mask = (engine==-1) ? (G->amask!=NULL) : engine;
    if(P.use_mask && !G->amask){ fprintf(stderr,"mask engine needs N<=128\n"); exit(1); }
    fprintf(stderr,"# engine=%s\n",P.use_mask?"mask":"cnt");
    P.total_jobs=E->n; P.t0=t0;
    P.done=calloc(E->n,1);
    pthread_mutex_init(&P.ck_mu,NULL);
    atomic_store(&P.next_job,0); atomic_store(&P.jobs_done,0);

    char header[256];
    snprintf(header,sizeof(header),"H n=%d graph=%016" PRIx64 " maxL=%d K=%d sym=%d jobs=%d",
             gpath?0:n, ghash, maxL, K, use_sym, E->n);

    if(!ckpath){
      static char tmp[]= "/tmp/count-ck-XXXXXX";
      int fd=mkstemp(tmp); ckpath=tmp;
      P.ck=fdopen(fd,"w+");
      fprintf(P.ck,"%s\n",header); fflush(P.ck);
    } else {
      FILE *old=fopen(ckpath,"r");
      if(old){
        char line[8192];
        if(fgets(line,sizeof(line),old)){
          line[strcspn(line,"\n")]=0;
          if(strcmp(line,header)!=0){
            fprintf(stderr,"checkpoint header mismatch:\n  file: %s\n  want: %s\n",line,header);
            exit(1);
          }
          long already=0;
          while(fgets(line,sizeof(line),old)){
            long id; int w;
            if(sscanf(line,"J %ld %d",&id,&w)==2 && id>=0 && id<E->n && !P.done[id]){
              /* verify the line is complete (has all levels) before trusting */
              int commas=0; for(char *s=line;*s;s++) commas += (*s==',');
              if(commas == maxL-K){ P.done[id]=1; already++; }
            }
          }
          fprintf(stderr,"# resume: %ld/%d jobs already done in %s\n",already,E->n,ckpath);
        }
        fclose(old);
        P.ck=fopen(ckpath,"a");
      } else {
        P.ck=fopen(ckpath,"w");
        if(!P.ck){ perror("checkpoint"); exit(1); }
        fprintf(P.ck,"%s\n",header); fflush(P.ck);
      }
    }

    pthread_t th[64];
    if(nthreads>64) nthreads=64;
    for(int i=0;i<nthreads;i++) pthread_create(&th[i],NULL,worker,&P);
    /* progress loop: tick fast, print rarely */
    time_t last_print=t0;
    for(;;){
      long d=atomic_load(&P.jobs_done);
      if(d>=P.total_jobs) break;
      struct timespec ts={0,200000000};
      nanosleep(&ts,NULL);
      time_t now=time(NULL);
      if(difftime(now,last_print)>=progress){
        last_print=now;
        d=atomic_load(&P.jobs_done);
        double el=difftime(now,t0);
        if(d>0 && d<P.total_jobs)
          fprintf(stderr,"# progress %ld/%ld (%.1f%%) elapsed %.0fs eta %.0fs\n",
                  d,P.total_jobs,100.0*d/P.total_jobs,el,el*(P.total_jobs-d)/d);
      }
    }
    for(int i=0;i<nthreads;i++) pthread_join(th[i],NULL);
    fclose(P.ck);

    /* aggregate from the checkpoint file — single source of truth */
    FILE *ck=fopen(ckpath,"r");
    char line[8192];
    if(!fgets(line,sizeof(line),ck)){ fprintf(stderr,"empty checkpoint\n"); exit(1); }
    uint8_t *seen=calloc(E->n,1);
    long counted=0;
    while(fgets(line,sizeof(line),ck)){
      long id; int w; int pos=0;
      if(sscanf(line,"J %ld %d%n",&id,&w,&pos)!=2) continue;
      if(id<0||id>=E->n||seen[id]) continue;
      char *s=line+pos; int ok=1;
      uint64_t pv[MAXL_CAP+1], cv[MAXL_CAP+1];
      for(int L=K+1;L<=maxL;L++){
        uint64_t a,b; int adv=0;
        if(sscanf(s," %" SCNu64 ",%" SCNu64 "%n",&a,&b,&adv)!=2){ ok=0; break; }
        pv[L]=a; cv[L]=b; s+=adv;
      }
      if(!ok) continue;
      seen[id]=1; counted++;
      for(int L=K+1;L<=maxL;L++){ path[L]+=(uint64_t)w*pv[L]; cyc[L]+=(uint64_t)w*cv[L]; }
    }
    fclose(ck);
    if(counted!=E->n){
      fprintf(stderr,"INCOMPLETE: %ld/%d jobs in checkpoint — results not printed\n",counted,E->n);
      exit(3);
    }
    free(seen);
  }

  double el=difftime(time(NULL),t0);
  fprintf(stderr,"# done in %.0fs\n",el);
  printf("# L path cyclic noncappable\n");
  for(int L=1;L<=maxL;L++){
    uint64_t nc=(L==1)?0:path[L]-cyc[L];
    printf("%d %" PRIu64 " %" PRIu64 " %" PRIu64 "\n",L,path[L],cyc[L],nc);
  }
  return 0;
}
