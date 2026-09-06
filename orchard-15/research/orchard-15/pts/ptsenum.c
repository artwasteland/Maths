#define _POSIX_C_SOURCE 200809L
/*
 * Point-by-point orderly enumeration of partial Steiner triple systems.
 *
 * A state has k processed points. Every pair incident with a processed
 * point has already been decided: it occurs in one triple or in the leave.
 * One augmentation chooses an unprocessed point p and adds its whole row,
 * namely a matching on the other unprocessed points. An unmatched point is
 * a leave neighbour of p. Thus every intermediate object is row-complete.
 *
 * The canonical object is the incidence graph, with processed points,
 * unprocessed points, and blocks as separate colour classes. For a fixed
 * leave shard the leave edges are also present as point-to-point edges.
 * The canonical parent of a (k+1)-row child changes its canonically last
 * processed point back to unprocessed and removes precisely the blocks
 * containing it and no earlier processed point. This is the row analogue
 * of canonical block deletion.
 */
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#include <nauty.h>

#define MAXV 63
#define MAXB 400
#define MAXAUT 256
#define LOAD_FACTOR 0.70

typedef struct { unsigned char a, b, c; } Triple;
typedef struct {
    int v, b, k;
    Triple *t;
    unsigned char *leave;
    size_t keylen;
    unsigned char *key;
} System;
typedef struct { System **a; size_t n, cap; } SystemList;
typedef struct { System **tab; size_t cap, n; } KeySet;
typedef struct { uint64_t a, b; } RowCode;
typedef struct { RowCode *tab; unsigned char *used; size_t cap, n; } RowSet;

static int V, B, target_leave, parity_mode, parity_constraint;
static int use_leave_graph, drop_parity, break_orbit;
static unsigned char *initial_leave;
static uint64_t canonical_calls, accepted_extensions, rejected_orbit;
static uint64_t output_count;
static uint64_t row_states[MAXV+1];
static FILE *outf;
static double started;
static int aut_perms[MAXAUT][MAXV], aut_count;

static void die(const char *s) { fprintf(stderr, "ptsenum: %s\n", s); exit(2); }

static void *xmalloc(size_t n)
{
    void *p = malloc(n ? n : 1);
    if (!p) die("out of memory");
    return p;
}
static void *xcalloc(size_t n, size_t z)
{
    void *p = calloc(n ? n : 1, z ? z : 1);
    if (!p) die("out of memory");
    return p;
}
static void *xrealloc(void *p, size_t n)
{
    void *q = realloc(p, n ? n : 1);
    if (!q) die("out of memory");
    return q;
}
static double now_seconds(void)
{
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts)) die("clock_gettime failed");
    return (double)ts.tv_sec + 1e-9 * (double)ts.tv_nsec;
}
static int triple_cmp(const void *aa, const void *bb)
{
    const Triple *a = aa, *b = bb;
    if (a->a != b->a) return (int)a->a - (int)b->a;
    if (a->b != b->b) return (int)a->b - (int)b->b;
    return (int)a->c - (int)b->c;
}
static uint64_t hash_bytes(const unsigned char *p, size_t n)
{
    uint64_t h = UINT64_C(1469598103934665603);
    size_t i;
    for (i = 0; i < n; ++i) { h ^= p[i]; h *= UINT64_C(1099511628211); }
    return h;
}
static void free_system(System *s)
{
    if (!s) return;
    free(s->t); free(s->leave); free(s->key); free(s);
}
static void list_push(SystemList *l, System *s)
{
    if (l->n == l->cap) {
        l->cap = l->cap ? 2 * l->cap : 64;
        l->a = xrealloc(l->a, l->cap * sizeof(*l->a));
    }
    l->a[l->n++] = s;
}
static void list_free(SystemList *l)
{
    size_t i;
    for (i = 0; i < l->n; ++i) free_system(l->a[i]);
    free(l->a); l->a = NULL; l->n = l->cap = 0;
}
static void keyset_init(KeySet *s, size_t cap)
{
    size_t n = 16;
    while (n < cap) n <<= 1;
    s->cap = n; s->tab = xcalloc(n, sizeof(*s->tab)); s->n = 0;
}
static int keyset_has_or_add(KeySet *s, System *x)
{
    size_t i;
    uint64_t h = hash_bytes(x->key, x->keylen);
    if ((double)(s->n + 1) / (double)s->cap > LOAD_FACTOR) {
        KeySet z; size_t j;
        keyset_init(&z, 2 * s->cap);
        for (j = 0; j < s->cap; ++j) if (s->tab[j]) keyset_has_or_add(&z, s->tab[j]);
        free(s->tab); *s = z;
    }
    i = (size_t)h & (s->cap - 1);
    while (s->tab[i]) {
        if (s->tab[i]->keylen == x->keylen &&
            !memcmp(s->tab[i]->key, x->key, x->keylen)) return 1;
        i = (i + 1) & (s->cap - 1);
    }
    s->tab[i] = x; ++s->n; return 0;
}
static void keyset_free(KeySet *s) { free(s->tab); s->tab = NULL; s->cap = s->n = 0; }

static int pair_index(int a, int b)
{
    int i, k = 0;
    if (a > b) { int z = a; a = b; b = z; }
    for (i = 0; i < a; ++i) k += V - 1 - i;
    return k + b - a - 1;
}
static size_t pair_bytes(void) { return (size_t)(V * (V - 1) / 2 + 7) / 8; }
static int bit_pair(const unsigned char *bits, int a, int b)
{
    int k = pair_index(a,b);
    return (bits[k >> 3] >> (k & 7)) & 1;
}
static void set_pair(unsigned char *bits, int a, int b)
{
    int k = pair_index(a,b);
    bits[k >> 3] |= (unsigned char)(1u << (k & 7));
}
static void add_triple_pairs(unsigned char *used, Triple t)
{
    set_pair(used,t.a,t.b); set_pair(used,t.a,t.c); set_pair(used,t.b,t.c);
}
static void collect_automorphism(int num, int *p, int *orbits,
                                 int numorbits, int stabvertex, int n)
{
    (void)num; (void)orbits; (void)numorbits; (void)stabvertex; (void)n;
    if (aut_count < MAXAUT) {
        memcpy(aut_perms[aut_count], p, (size_t)V * sizeof(int));
        ++aut_count;
    }
}

static void make_partition(int n, int k, int *lab, int *ptn)
{
    int z = 0, i;
    for (i = 0; i < k; ++i) lab[z++] = i;
    if (k) ptn[z-1] = 0;
    for (i = k; i < V; ++i) lab[z++] = i;
    if (k < V) ptn[z-1] = 0;
    for (i = V; i < n; ++i) lab[z++] = i;
    if (n > V) ptn[z-1] = 0;
    for (i = 0; i < n; ++i)
        if ((i < k-1) || (i >= k && i < V-1) || (i >= V && i < n-1)) ptn[i] = 1;
}
static void build_graph(const Triple *t, int nb, const unsigned char *leave,
                        graph *g, int m)
{
    int i, j, n = V + nb;
    memset(g, 0, (size_t)n * m * sizeof(graph));
    if (use_leave_graph && leave) {
        for (i = 0; i < V; ++i) for (j = i + 1; j < V; ++j)
            if (bit_pair(leave,i,j)) {
                ADDELEMENT(GRAPHROW(g,i,m),j);
                ADDELEMENT(GRAPHROW(g,j,m),i);
            }
    }
    for (i = 0; i < nb; ++i) {
        int q = V + i, z[3] = {t[i].a,t[i].b,t[i].c};
        for (j = 0; j < 3; ++j) {
            ADDELEMENT(GRAPHROW(g,q,m),z[j]);
            ADDELEMENT(GRAPHROW(g,z[j],m),q);
        }
    }
}
static System *canonical_state(const Triple *in, int nb, int k,
                               const unsigned char *leave, int selected,
                               int *selected_image, int *canonical_orbits)
{
    int n = V + nb, m = SETWORDSNEEDED(n), i, p, q;
    graph *g = xmalloc((size_t)n * m * sizeof(graph));
    graph *c = xmalloc((size_t)n * m * sizeof(graph));
    int *lab = xmalloc((size_t)n * sizeof(int));
    int *ptn = xcalloc((size_t)n, sizeof(int));
    int *orbits = xmalloc((size_t)n * sizeof(int));
    Triple *out = xmalloc((size_t)(nb ? nb : 1) * sizeof(*out));
    statsblk stats;
    static DEFAULTOPTIONS_GRAPH(options);
    build_graph(in,nb,leave,g,m);
    make_partition(n,k,lab,ptn);
    options.getcanon = 1; options.defaultptn = FALSE; options.userautomproc = NULL;
    densenauty(g,lab,ptn,orbits,&options,&stats,m,n,c);
    ++canonical_calls;
    if(selected_image) {
        *selected_image=-1;
        for(i=0;i<V;++i)if(lab[i]==selected)*selected_image=i;
        if(*selected_image<0)die("nauty labelling lost selected point");
    }
    if(canonical_orbits)for(i=0;i<V;++i)canonical_orbits[i]=orbits[lab[i]];
    for (i = 0; i < nb; ++i) {
        p = V + i; int z[3], nz = 0;
        for (q = 0; q < V; ++q)
            if (ISELEMENT(GRAPHROW(c,p,m),q)) z[nz++] = q;
        if (nz != 3) die("nauty incidence graph lost a triple");
        out[i] = (Triple){(unsigned char)z[0],(unsigned char)z[1],(unsigned char)z[2]};
    }
    qsort(out,(size_t)nb,sizeof(*out),triple_cmp);
    System *s = xcalloc(1,sizeof(*s));
    s->v=V; s->b=nb; s->k=k; s->t=out;
    if (use_leave_graph) {
        s->leave=xcalloc(pair_bytes(),1);
        for (i=0;i<V;++i) for (q=i+1;q<V;++q)
            if (ISELEMENT(GRAPHROW(c,i,m),q)) set_pair(s->leave,i,q);
    }
    s->keylen=(size_t)nb*sizeof(Triple)+(use_leave_graph?pair_bytes():0);
    s->key=xmalloc(s->keylen);
    if (nb) memcpy(s->key,out,(size_t)nb*sizeof(Triple));
    if (use_leave_graph) memcpy(s->key+(size_t)nb*sizeof(Triple),s->leave,pair_bytes());
    free(g); free(c); free(lab); free(ptn); free(orbits);
    return s;
}
static void collect_parent_symmetry(const System *s, int *point_orbits)
{
    int n=V+s->b,m=SETWORDSNEEDED(n),i;
    graph *g=xmalloc((size_t)n*m*sizeof(graph));
    graph *c=xmalloc((size_t)n*m*sizeof(graph));
    int *lab=xmalloc((size_t)n*sizeof(int));
    int *ptn=xcalloc((size_t)n,sizeof(int));
    int *orbits=xmalloc((size_t)n*sizeof(int));
    statsblk stats;
    static DEFAULTOPTIONS_GRAPH(options);
    build_graph(s->t,s->b,s->leave,g,m); make_partition(n,s->k,lab,ptn);
    options.getcanon=0; options.defaultptn=FALSE; options.userautomproc=collect_automorphism;
    aut_count=0;
    densenauty(g,lab,ptn,orbits,&options,&stats,m,n,c);
    for (i=0;i<V;++i) point_orbits[i]=orbits[i];
    free(g); free(c); free(lab); free(ptn); free(orbits);
}
static void collect_point_stabilizer(const System *s,int point)
{
    int n=V+s->b,m=SETWORDSNEEDED(n),i,z=0;
    graph *g=xmalloc((size_t)n*m*sizeof(graph));
    graph *c=xmalloc((size_t)n*m*sizeof(graph));
    int *lab=xmalloc((size_t)n*sizeof(int));
    int *ptn=xcalloc((size_t)n,sizeof(int));
    int *orbits=xmalloc((size_t)n*sizeof(int));
    statsblk stats;
    static DEFAULTOPTIONS_GRAPH(options);
    build_graph(s->t,s->b,s->leave,g,m);
    for(i=0;i<s->k;++i)lab[z++]=i;
    if(s->k)ptn[z-1]=0;
    lab[z++]=point;ptn[z-1]=0;
    for(i=s->k;i<V;++i)if(i!=point)lab[z++]=i;
    if(V-s->k-1)ptn[z-1]=0;
    for(i=V;i<n;++i)lab[z++]=i;
    if(n>V)ptn[z-1]=0;
    for(i=0;i<n;++i) {
        if(i<s->k-1)ptn[i]=1;
        if(i>s->k && i<V-1)ptn[i]=1;
        if(i>=V && i<n-1)ptn[i]=1;
    }
    options.getcanon=0;options.defaultptn=FALSE;options.userautomproc=collect_automorphism;
    aut_count=0;densenauty(g,lab,ptn,orbits,&options,&stats,m,n,c);
    free(g);free(c);free(lab);free(ptn);free(orbits);
}

static int triangle_decomposition_rec(uint64_t *adj,int edges,uint64_t *nodes)
{
    int u=-1,v=-1,best=MAXV+1,i,j,w;
    uint64_t common=0;
    if(!edges)return 1;
    if(++*nodes>UINT64_C(100000))return 1;
    for(i=0;i<V;++i)for(j=i+1;j<V;++j)if((adj[i]>>j)&1) {
        int n=__builtin_popcountll(adj[i]&adj[j]);
        if(n<best){best=n;u=i;v=j;common=adj[i]&adj[j];if(!n)return 0;}
    }
    while(common) {
        w=__builtin_ctzll(common);common&=common-1;
        adj[u]&=~(UINT64_C(1)<<v);adj[v]&=~(UINT64_C(1)<<u);
        adj[u]&=~(UINT64_C(1)<<w);adj[w]&=~(UINT64_C(1)<<u);
        adj[v]&=~(UINT64_C(1)<<w);adj[w]&=~(UINT64_C(1)<<v);
        if(triangle_decomposition_rec(adj,edges-3,nodes))return 1;
        adj[u]|=UINT64_C(1)<<v;adj[v]|=UINT64_C(1)<<u;
        adj[u]|=UINT64_C(1)<<w;adj[w]|=UINT64_C(1)<<u;
        adj[v]|=UINT64_C(1)<<w;adj[w]|=UINT64_C(1)<<v;
    }
    return 0;
}

/*
 * This is the row-level decomposability prune. For each unprocessed point,
 * its still available degree d must split as 2r+l, where r is no larger
 * than the remaining block budget and l contributes to the remaining leave.
 */
static int feasible_raw(const Triple *t, int nb, const unsigned char *leave,
                        const unsigned char *processed)
{
    int pairs=V*(V-1)/2, remB=B-nb, frozen=0, avail=0, i,j,z;
    int fdeg[MAXV]={0}, adeg[MAXV]={0};
    unsigned char *used=xcalloc(pair_bytes(),1);
    if (nb>B) { free(used); return 0; }
    for (z=0;z<nb;++z) {
        if (bit_pair(used,t[z].a,t[z].b) || bit_pair(used,t[z].a,t[z].c) ||
            bit_pair(used,t[z].b,t[z].c)) { free(used); return 0; }
        if (use_leave_graph &&
            (bit_pair(leave,t[z].a,t[z].b) || bit_pair(leave,t[z].a,t[z].c) ||
             bit_pair(leave,t[z].b,t[z].c))) { free(used); return 0; }
        add_triple_pairs(used,t[z]);
    }
    for (i=0;i<V;++i) for (j=i+1;j<V;++j) if (!bit_pair(used,i,j)) {
        if (processed[i] || processed[j]) {
            ++frozen; ++fdeg[i]; ++fdeg[j];
            if (use_leave_graph && !bit_pair(leave,i,j)) { free(used); return 0; }
        } else {
            ++avail; ++adeg[i]; ++adeg[j];
        }
    }
    if (frozen>target_leave || avail != 3*remB+(target_leave-frozen)) {
        free(used); return 0;
    }
    if (3*nb + frozen + avail != pairs) { free(used); return 0; }
    for (i=0;i<V;++i) {
        int ok=0,l,lim=target_leave-frozen;
        if (processed[i]) {
            if (!drop_parity && parity_constraint && ((fdeg[i]&1)!=parity_mode)) {
                free(used); return 0;
            }
            continue;
        }
        if (use_leave_graph) {
            int future=0;
            for (j=0;j<V;++j) if (!processed[j] && j!=i && bit_pair(leave,i,j)) ++future;
            if (future<=adeg[i] && ((adeg[i]-future)&1)==0 &&
                (adeg[i]-future)/2<=remB) ok=1;
        } else {
            if (lim>adeg[i]) lim=adeg[i];
            for (l=0;l<=lim;++l)
                if (((adeg[i]-l)&1)==0 && (adeg[i]-l)/2<=remB &&
                    (drop_parity || !parity_constraint || ((fdeg[i]+l)&1)==parity_mode)) {
                    ok=1; break;
                }
        }
        if (!ok) { free(used); return 0; }
    }
    if (use_leave_graph || target_leave==frozen) {
        uint64_t adj[MAXV]={0},todo=0;
        int cover_edges=0,unprocessed_count=0;
        uint64_t search_nodes=0;
        for(i=0;i<V;++i)if(!processed[i])++unprocessed_count;
        for(i=0;i<V;++i)if(!processed[i])for(j=i+1;j<V;++j)if(!processed[j] &&
            !bit_pair(used,i,j) && (!use_leave_graph || !bit_pair(leave,i,j))) {
            adj[i]|=UINT64_C(1)<<j;adj[j]|=UINT64_C(1)<<i;++cover_edges;
        }
        if(cover_edges!=3*remB){free(used);return 0;}
        for(i=0;i<V;++i)if(!processed[i]) {
            if(__builtin_popcountll(adj[i])&1){free(used);return 0;}
            for(j=i+1;j<V;++j)if((adj[i]>>j)&1)
                if(!(adj[i]&adj[j])){free(used);return 0;}
            if(adj[i])todo|=UINT64_C(1)<<i;
        }
        while(todo) {
            uint64_t front=UINT64_C(1)<<__builtin_ctzll(todo),seen=0;int ce=0;
            while(front) {
                int x=__builtin_ctzll(front);front&=front-1;
                if((seen>>x)&1)continue;
                seen|=UINT64_C(1)<<x;
                front|=adj[x]&~seen;ce+=__builtin_popcountll(adj[x]);
            }
            if((ce/2)%3){free(used);return 0;}todo&=~seen;
        }
        if(unprocessed_count<=11 && !triangle_decomposition_rec(adj,cover_edges,&search_nodes)) {
            free(used);return 0;
        }
    }
    free(used); return 1;
}
static int canonical_reduction_point(const System *child)
{
    int q=0,z,best=-1;
    /* Prefer a point whose deletion removes the most current-row blocks. */
    for (int x=0;x<child->k;++x) {
        int score=0;
        for (z=0;z<child->b;++z) {
            Triple t=child->t[z];
            int has=(t.a==x||t.b==x||t.c==x),other_processed=0;
            if(!has)continue;
            if((t.a<child->k&&t.a!=x)||(t.b<child->k&&t.b!=x)||
               (t.c<child->k&&t.c!=x))other_processed=1;
            if(!other_processed)++score;
        }
        if(score>=best){best=score;q=x;}
    }
    return q;
}
static void print_system(const System *s, FILE *f)
{
    int i;
    fprintf(f,"%d %d : ",s->v,s->b);
    for (i=0;i<s->b;++i) {
        if (i) fputs(" , ",f);
        fprintf(f,"%d %d %d",s->t[i].a,s->t[i].b,s->t[i].c);
    }
    fputs(";\n",f);
}

static uint64_t row_hash(RowCode x)
{
    uint64_t h=x.a*UINT64_C(0x9e3779b97f4a7c15);
    h^=x.b+UINT64_C(0x9e3779b97f4a7c15)+(h<<6)+(h>>2); return h;
}
static int row_equal(RowCode x,RowCode y) { return x.a==y.a && x.b==y.b; }
static void rowset_init(RowSet *s,size_t cap)
{
    size_t n=16; while(n<cap)n<<=1;
    s->cap=n;s->n=0;s->tab=xcalloc(n,sizeof(*s->tab));s->used=xcalloc(n,1);
}
static int rowset_has_or_add(RowSet *s,RowCode x)
{
    size_t i;
    if ((double)(s->n+1)/(double)s->cap>LOAD_FACTOR) {
        RowSet z; size_t j; rowset_init(&z,2*s->cap);
        for(j=0;j<s->cap;++j)if(s->used[j])rowset_has_or_add(&z,s->tab[j]);
        free(s->tab);free(s->used);*s=z;
    }
    i=(size_t)row_hash(x)&(s->cap-1);
    while(s->used[i]) { if(row_equal(s->tab[i],x))return 1;i=(i+1)&(s->cap-1); }
    s->used[i]=1;s->tab[i]=x;++s->n;return 0;
}
static void rowset_free(RowSet *s) { free(s->tab);free(s->used);memset(s,0,sizeof(*s)); }
static RowCode row_add(RowCode x,int a,int b)
{
    int p=pair_index(a,b);
    if(p<64)x.a|=UINT64_C(1)<<p;else x.b|=UINT64_C(1)<<(p-64);
    return x;
}
static RowCode row_transform(RowCode x,const int *perm)
{
    RowCode y={0,0}; int i,j,p;
    for(i=0;i<V;++i)for(j=i+1;j<V;++j) {
        p=pair_index(i,j);
        if ((p<64 ? (x.a>>p)&1 : (x.b>>(p-64))&1)) y=row_add(y,perm[i],perm[j]);
    }
    return y;
}
static int row_orbit_seen(RowSet *seen,RowCode start,int point)
{
    RowCode *queue; size_t head=0,n=0,cap=64;
    if(rowset_has_or_add(seen,start))return 1;
    queue=xmalloc(cap*sizeof(*queue));queue[n++]=start;
    while(head<n) {
        RowCode x=queue[head++]; int g;
        for(g=0;g<aut_count;++g)if(aut_perms[g][point]==point) {
            RowCode y=row_transform(x,aut_perms[g]);
            if(!rowset_has_or_add(seen,y)) {
                if(n==cap){cap*=2;queue=xrealloc(queue,cap*sizeof(*queue));}
                queue[n++]=y;
            }
        }
    }
    free(queue); return 0;
}

typedef struct {
    const System *parent;
    int point;
    int need[MAXV], nneed;
    Triple added[MAXV/2+1];
    int nadded;
    int nleaves, max_leaves;
    unsigned char *used_pairs;
    unsigned char processed[MAXV];
    RowSet row_seen;
    KeySet *next_seen;
    SystemList *next;
} RowContext;

static void emit_row(RowContext *r,RowCode code)
{
    int nb=r->parent->b+r->nadded,z,k=r->parent->k;
    Triple *tmp,*mapped;
    unsigned char *mapped_leave=NULL;
    System *child;
    if (!break_orbit && row_orbit_seen(&r->row_seen,code,r->point)) return;
    tmp=xmalloc((size_t)(nb?nb:1)*sizeof(*tmp));
    if(r->parent->b)memcpy(tmp,r->parent->t,(size_t)r->parent->b*sizeof(*tmp));
    for(z=0;z<r->nadded;++z)tmp[r->parent->b+z]=r->added[z];
    if(!feasible_raw(tmp,nb,r->parent->leave,r->processed)){free(tmp);return;}
    mapped=xmalloc((size_t)(nb?nb:1)*sizeof(*mapped));
    for(z=0;z<nb;++z) {
        int a=tmp[z].a,b=tmp[z].b,c=tmp[z].c,w,p=r->point;
        if(a==p)a=k;else if(a==k)a=p;
        if(b==p)b=k;else if(b==k)b=p;
        if(c==p)c=k;else if(c==k)c=p;
        if(a>b){w=a;a=b;b=w;}if(b>c){w=b;b=c;c=w;}if(a>b){w=a;a=b;b=w;}
        mapped[z]=(Triple){(unsigned char)a,(unsigned char)b,(unsigned char)c};
    }
    if(use_leave_graph) {
        mapped_leave=xcalloc(pair_bytes(),1);
        for(int a=0;a<V;++a)for(int b=a+1;b<V;++b)if(bit_pair(r->parent->leave,a,b)) {
            int x=a==r->point?k:(a==k?r->point:a);
            int y=b==r->point?k:(b==k?r->point:b);
            set_pair(mapped_leave,x,y);
        }
    }
    int selected_image,child_orbits[MAXV];
    child=canonical_state(mapped,nb,k+1,mapped_leave,k,&selected_image,child_orbits);
    free(tmp);free(mapped);free(mapped_leave);
    ++accepted_extensions;
    if(!(accepted_extensions%UINT64_C(100000)))
        fprintf(stderr,"progress rows=%" PRIu64 " canonical_calls=%" PRIu64 " depth=%d\n",
                accepted_extensions,canonical_calls,k+1);
    if(!break_orbit && child_orbits[selected_image]!=child_orbits[canonical_reduction_point(child)]) {
        ++rejected_orbit;free_system(child);return;
    }
    if(!break_orbit && keyset_has_or_add(r->next_seen,child)) {free_system(child);return;}
    list_push(r->next,child);
}
static void enumerate_matchings(RowContext *r,uint64_t unresolved,RowCode code)
{
    int ix,x,jy,y;
    if(!unresolved){emit_row(r,code);return;}
    ix=__builtin_ctzll(unresolved);x=r->need[ix];unresolved&=~(UINT64_C(1)<<ix);
    if(!use_leave_graph && r->nleaves<r->max_leaves) {
        ++r->nleaves;enumerate_matchings(r,unresolved,code);--r->nleaves;
    }
    for(jy=ix+1;jy<r->nneed;++jy)if(unresolved&(UINT64_C(1)<<jy)) {
        y=r->need[jy];
        if(bit_pair(r->used_pairs,x,y))continue;
        if(use_leave_graph && bit_pair(r->parent->leave,x,y))continue;
        if(r->parent->b+r->nadded>=B)continue;
        int a=r->point,b=x,c=y,t;
        if(a>b){t=a;a=b;b=t;}if(b>c){t=b;b=c;c=t;}if(a>b){t=a;a=b;b=t;}
        r->added[r->nadded++]=(Triple){(unsigned char)a,(unsigned char)b,(unsigned char)c};
        enumerate_matchings(r,unresolved&~(UINT64_C(1)<<jy),row_add(code,x,y));
        --r->nadded;
    }
}
static void augment_point(const System *s,int p,KeySet *seen,SystemList *next)
{
    RowContext r; int x,y,z,frozen=0;
    memset(&r,0,sizeof(r));r.parent=s;r.point=p;r.next_seen=seen;r.next=next;
    if(!break_orbit)collect_point_stabilizer(s,p);
    r.used_pairs=xcalloc(pair_bytes(),1);
    for(z=0;z<s->b;++z)add_triple_pairs(r.used_pairs,s->t[z]);
    for(x=0;x<V;++x)for(y=x+1;y<V;++y)
        if((x<s->k||y<s->k)&&!bit_pair(r.used_pairs,x,y))++frozen;
    r.max_leaves=target_leave-frozen;
    if(r.max_leaves<0){free(r.used_pairs);return;}
    for(x=0;x<s->k;++x)r.processed[x]=1;
    r.processed[p]=1;
    for(x=s->k;x<V;++x)if(x!=p && !bit_pair(r.used_pairs,p,x)) {
        if(use_leave_graph && bit_pair(s->leave,p,x))continue;
        r.need[r.nneed++]=x;
    }
    rowset_init(&r.row_seen,64);
    enumerate_matchings(&r,r.nneed==64?UINT64_MAX:((UINT64_C(1)<<r.nneed)-1),(RowCode){0,0});
    rowset_free(&r.row_seen);free(r.used_pairs);
}
static void augment_first_generic(const System *s,KeySet *seen,SystemList *next)
{
    int m,max=(V-1)/2;
    for(m=0;m<=max;++m) {
        RowContext r; int z;
        memset(&r,0,sizeof(r));r.parent=s;r.point=0;r.next_seen=seen;r.next=next;
        r.used_pairs=xcalloc(pair_bytes(),1);r.processed[0]=1;r.nadded=m;
        RowCode code={0,0};
        for(z=0;z<m;++z) {
            r.added[z]=(Triple){0,(unsigned char)(1+2*z),(unsigned char)(2+2*z)};
            code=row_add(code,1+2*z,2+2*z);
        }
        rowset_init(&r.row_seen,16);emit_row(&r,code);rowset_free(&r.row_seen);free(r.used_pairs);
    }
}
static void generate_children(const System *s,SystemList *next)
{
    KeySet seen;int orbits[MAXV],p,q,rep;
    keyset_init(&seen,128);
    if(s->k==0 && !use_leave_graph && !break_orbit) {
        augment_first_generic(s,&seen,next);
    } else {
        collect_parent_symmetry(s,orbits);
        for(p=s->k;p<V;++p) {
            rep=1;
            for(q=s->k;q<p;++q)if(orbits[q]==orbits[p]){rep=0;break;}
            if(rep || break_orbit)augment_point(s,p,&seen,next);
        }
    }
    keyset_free(&seen);
}
static void enumerate_dfs(const System *s)
{
    SystemList children={0};size_t i;
    if(s->k==V) {
        if(s->b==B){print_system(s,outf);++output_count;}
        return;
    }
    generate_children(s,&children);row_states[s->k+1]+=children.n;
    for(i=0;i<children.n;++i)enumerate_dfs(children.a[i]);
    list_free(&children);
}

static int parse_g6(const char *s,unsigned char **out)
{
    int n,x,y,bit=0,pos=1,val=0,edges=0;
    if(!s || !*s || (unsigned char)s[0]>=126)return 0;
    n=(unsigned char)s[0]-63;
    if(n!=V || (int)strlen(s)<1+(n*(n-1)/2+5)/6)return 0;
    *out=xcalloc(pair_bytes(),1);
    for(x=1;x<n;++x)for(y=0;y<x;++y) {
        if(!bit){val=(unsigned char)s[pos++]-63;if(val<0||val>63)return 0;bit=6;}
        if(val&(1<<(--bit))){set_pair(*out,y,x);++edges;}
    }
    return edges;
}
static int sha256_external(const char *path,char hex[65])
{
    int fd[2],status; ssize_t got=0,n; pid_t pid;
    char buf[128];
    if(pipe(fd))return 0;
    pid=fork();
    if(pid<0){close(fd[0]);close(fd[1]);return 0;}
    if(pid==0){dup2(fd[1],STDOUT_FILENO);close(fd[0]);close(fd[1]);execl("/usr/bin/sha256sum","sha256sum",path,(char*)NULL);_exit(127);}
    close(fd[1]);
    while(got<(ssize_t)sizeof(buf)-1 && (n=read(fd[0],buf+got,sizeof(buf)-1-(size_t)got))>0)got+=n;
    close(fd[0]);if(waitpid(pid,&status,0)<0)return 0;buf[got]='\0';
    if(!WIFEXITED(status)||WEXITSTATUS(status)!=0||got<64)return 0;
    memcpy(hex,buf,64);hex[64]='\0';return 1;
}
static void write_done(const char *path,uint64_t count)
{
    char hash[65],done[4096]; FILE *f;
    if(!sha256_external(path,hash))die("cannot hash completed dataset");
    if(snprintf(done,sizeof(done),"%s.DONE",path)>=(int)sizeof(done))die("output path too long");
    f=fopen(done,"w");if(!f)die("cannot write DONE marker");
    fprintf(f,"count=%" PRIu64 "\nsha256=%s\n",count,hash);fclose(f);
}
static void manifest(const char *path)
{
    FILE *f=fopen(path,"w");char self[65];
    if(!f)die("cannot write manifest");
    if(!sha256_external("/proc/self/exe",self))die("cannot hash generator");
    fprintf(f,"{\"v\":%d,\"b\":%d,\"count\":%" PRIu64
            ",\"canonical_calls\":%" PRIu64 ",\"accepted_extensions\":%" PRIu64
            ",\"rejected_orbit\":%" PRIu64 ",\"leave_edges\":%d,\"parity\":\"%s\""
            ",\"generator_sha256\":\"%s\",\"leave_type_histogram\":{\"selected\":%" PRIu64 "}}\n",
            V,B,output_count,canonical_calls,accepted_extensions,rejected_orbit,target_leave,
            drop_parity?"dropped":(parity_constraint==0?"any":(parity_mode==0?"even":"odd")),
            self,output_count);fclose(f);
}
static int delete_point_file(const char *path)
{
    FILE *in=fopen(path,"r"),*f;char line[8192],*p;KeySet seen;SystemList owned={0};
    const char *outpath="pointed-14-28.txt";
    if(!in){fprintf(stderr,"ptsenum: %s: %s\n",path,strerror(errno));return 2;}
    V=14;B=28;target_leave=7;parity_mode=1;parity_constraint=1;use_leave_graph=0;
    keyset_init(&seen,128);f=fopen(outpath,"w");if(!f)die("cannot write pointed-14-28.txt");
    while(fgets(line,sizeof(line),in)) {
        Triple all[64];int nb=0,oldv,oldb;
        if(sscanf(line,"%d %d",&oldv,&oldb)!=2)continue;
        p=strchr(line,':');if(!p)continue;++p;
        while(*p&&nb<64) {
            char *e;long a=strtol(p,&e,10);if(e==p){++p;continue;}p=e;
            long b=strtol(p,&e,10);if(e==p)continue;p=e;
            long c=strtol(p,&e,10);if(e==p)continue;p=e;
            if(a<0||b<0||c<0||a>=oldv||b>=oldv||c>=oldv)continue;
            all[nb++]=(Triple){(unsigned char)a,(unsigned char)b,(unsigned char)c};
        }
        if(nb!=oldb||oldv!=15)continue;
        for(int x=0;x<15;++x) {
            Triple reduced[64];int nr=0;
            for(int z=0;z<nb;++z) {
                int q[3]={all[z].a,all[z].b,all[z].c},hit=0;
                for(int h=0;h<3;++h)if(q[h]==x)hit=1;
                if(hit)continue;
                for(int h=0;h<3;++h)if(q[h]>x)--q[h];
                reduced[nr++]=(Triple){(unsigned char)q[0],(unsigned char)q[1],(unsigned char)q[2]};
            }
            if(nr!=28)continue;
            System *s=canonical_state(reduced,nr,V,NULL,-1,NULL,NULL);
            if(!keyset_has_or_add(&seen,s)){print_system(s,f);++output_count;list_push(&owned,s);}else free_system(s);
        }
    }
    fclose(in);fclose(f);write_done(outpath,output_count);keyset_free(&seen);list_free(&owned);
    fprintf(stderr,"pointed_count=%" PRIu64 " wall_seconds=%.6f\n",output_count,now_seconds()-started);return 0;
}
static void usage(void)
{
    fprintf(stderr,"usage: ptsenum --sts v | --pts v b [--leave-even|--leave-odd|--leave-any] [--leave-graph g6] [--output file]\n");
    fprintf(stderr,"       ptsenum --delete-point sts-file\n");exit(2);
}
int main(int argc,char **argv)
{
    int i,mode_sts=0,delete_mode=0;const char *outpath=NULL,*g6=NULL,*delete_path=NULL;
    System *root;char default_out[128],default_man[128];
    V=B=0;started=now_seconds();
    for(i=1;i<argc;++i) {
        if(!strcmp(argv[i],"--sts")&&i+1<argc){mode_sts=1;V=atoi(argv[++i]);}
        else if(!strcmp(argv[i],"--pts")&&i+2<argc){V=atoi(argv[++i]);B=atoi(argv[++i]);}
        else if(!strcmp(argv[i],"--leave-even")){parity_mode=0;parity_constraint=1;drop_parity=0;}
        else if(!strcmp(argv[i],"--leave-odd")){parity_mode=1;parity_constraint=1;drop_parity=0;}
        else if(!strcmp(argv[i],"--leave-any")){parity_mode=0;parity_constraint=0;}
        else if(!strcmp(argv[i],"--drop-parity"))drop_parity=1;
        else if(!strcmp(argv[i],"--break-orbit"))break_orbit=1;
        else if(!strcmp(argv[i],"--leave-graph")&&i+1<argc)g6=argv[++i];
        else if(!strcmp(argv[i],"--output")&&i+1<argc)outpath=argv[++i];
        else if(!strcmp(argv[i],"--delete-point")&&i+1<argc){delete_mode=1;delete_path=argv[++i];}
        else usage();
    }
    if(delete_mode)return delete_point_file(delete_path);
    if(V<3||V>MAXV||B<0||B>MAXB)usage();
    if(mode_sts){if(V*(V-1)%6)die("STS pair count is not divisible by 3");B=V*(V-1)/6;parity_mode=(V-1)&1;parity_constraint=1;}
    target_leave=V*(V-1)/2-3*B;if(target_leave<0)die("too many blocks");
    if(g6){int edges;use_leave_graph=1;edges=parse_g6(g6,&initial_leave);if(!edges&&target_leave)die("invalid leave graph6");if(edges!=target_leave)die("leave graph has wrong edge budget");}
    nauty_check(WORDSIZE,SETWORDSNEEDED(V+B),V+B,NAUTYVERSIONID);
    snprintf(default_out,sizeof(default_out),"pts-%d-%d.txt",V,B);
    snprintf(default_man,sizeof(default_man),"manifest-%d-%d.json",V,B);
    if(!outpath)outpath=default_out;
    outf=fopen(outpath,"w");if(!outf){fprintf(stderr,"ptsenum: %s: %s\n",outpath,strerror(errno));return 2;}
    root=canonical_state(NULL,0,0,initial_leave,-1,NULL,NULL);enumerate_dfs(root);free_system(root);
    for(i=0;i<V;++i)fprintf(stderr,"row %d -> %" PRIu64 " systems\n",i+1,row_states[i+1]);
    fclose(outf);write_done(outpath,output_count);manifest(default_man);
    fprintf(stderr,"count=%" PRIu64 " wall_seconds=%.6f canonical_calls=%" PRIu64 "\n",
            output_count,now_seconds()-started,canonical_calls);
    free(initial_leave);return 0;
}
