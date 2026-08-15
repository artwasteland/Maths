// Memory-compact exact Hamiltonian-cycle counter: same TdZdd HamiltonCycleZdd
// transition logic and same level-by-level frontier sweep as count_frontier.cpp,
// but each level is a flat open-addressing hash table with the W*2-byte mate key
// stored inline and a 16-byte count value -- ~5x less RAM per state than
// unordered_map<string,__int128>, so it fits where the simple version OOMs.
//
// Validated identically: n=3 -> 1, n=4 -> 44.
// Build: g++ -O3 -march=native -I/tmp/TdZdd/include -o count_frontier2 count_frontier2.cpp
// Run:   ./count_frontier2 graph.dat
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <vector>
#include <tdzdd/util/MessageHandler.hpp>
#include <tdzdd/util/Graph.hpp>
#include <tdzdd/spec/PathZdd.hpp>

using namespace tdzdd;
typedef unsigned __int128 u128;
typedef int16_t Mate;

static int KEYB;   // key length in bytes = W*2

struct FlatMap {
  // open addressing, linear probing; key inline (KEYB bytes), value u128.
  uint8_t* keys = nullptr;     // cap*KEYB
  u128*    vals = nullptr;     // cap
  uint8_t* used = nullptr;     // cap (0/1)
  size_t cap = 0, cnt = 0;
  void init(size_t c){ cap=c; keys=(uint8_t*)malloc(cap*KEYB); vals=(u128*)malloc(cap*sizeof(u128)); used=(uint8_t*)calloc(cap,1); cnt=0; }
  void freeAll(){ free(keys);free(vals);free(used); keys=nullptr;vals=nullptr;used=nullptr; cap=0;cnt=0; }
  static inline uint64_t hash(const uint8_t* k){ uint64_t h=1469598103934665603ULL; for(int i=0;i<KEYB;i++){h^=k[i];h*=1099511628211ULL;} return h; }
  void grow();
  inline void add(const uint8_t* k, u128 d){
    if(!keys) init(1<<16);
    if((cnt+1)*10 >= cap*7) grow();
    size_t m=cap-1, i=hash(k)&m;
    while(used[i]){ if(memcmp(keys+i*KEYB,k,KEYB)==0){ vals[i]+=d; return; } i=(i+1)&m; }
    used[i]=1; memcpy(keys+i*KEYB,k,KEYB); vals[i]=d; cnt++;
  }
};
void FlatMap::grow(){
  size_t ncap=cap?cap*2:(1<<16);
  FlatMap n; n.cap=ncap; n.keys=(uint8_t*)malloc(ncap*KEYB); n.vals=(u128*)malloc(ncap*sizeof(u128)); n.used=(uint8_t*)calloc(ncap,1); n.cnt=0;
  size_t m=ncap-1;
  for(size_t i=0;i<cap;i++) if(used[i]){ const uint8_t*k=keys+i*KEYB; size_t j=hash(k)&m; while(n.used[j]) j=(j+1)&m; n.used[j]=1; memcpy(n.keys+j*KEYB,k,KEYB); n.vals[j]=vals[i]; n.cnt++; }
  free(keys);free(vals);free(used);
  keys=n.keys; vals=n.vals; used=n.used; cap=n.cap; cnt=n.cnt;
}

static std::string u128str(u128 x){ if(x==0)return "0"; char b[40]; int p=40; while(x){b[--p]='0'+(int)(x%10);x/=10;} return std::string(b+p,40-p); }

int main(int argc,char**argv){
  if(argc<2){ fprintf(stderr,"usage: %s graph.dat\n",argv[0]); return 1; }
  Graph g; g.readAdjacencyList(argv[1]);
  fprintf(stderr,"#vertex=%d #edge=%d max_frontier=%d\n", g.vertexSize(), g.edgeSize(), g.maxFrontierSize());
  HamiltonCycleZdd spec(g, false); /* lookahead off: only 2 levels alive at once */
  int W = spec.mateArraySize(); KEYB = W*sizeof(Mate);
  std::vector<Mate> rootMate(W);
  int topLevel = spec.getRoot(rootMate.data());
  fprintf(stderr,"root level=%d W=%d\n", topLevel, W);

  std::vector<FlatMap> level(topLevel+1);
  level[topLevel].add((uint8_t*)rootMate.data(), (u128)1);

  u128 answer=0; size_t peak=0;
  std::vector<Mate> tmp(W);
  for(int L=topLevel; L>=1; --L){
    FlatMap &mp = level[L];
    if(mp.cnt>peak) peak=mp.cnt;
    if(L%10==0) fprintf(stderr,"  level %d : %zu states  ans=%s\n", L, mp.cnt, u128str(answer).c_str());
    for(size_t i=0;i<mp.cap;i++) if(mp.used[i]){
      u128 c=mp.vals[i]; const uint8_t* base=mp.keys+i*KEYB;
      for(int val=0; val<2; ++val){
        memcpy(tmp.data(), base, KEYB);
        int nl=spec.getChild(tmp.data(), L, val);
        if(nl==-1) answer+=c;
        else if(nl>0) level[nl].add((uint8_t*)tmp.data(), c);
      }
    }
    mp.freeAll();
  }
  fprintf(stderr,"peak level width = %zu states\n", peak);
  printf("UNDIRECTED Hamiltonian cycles = %s\n", u128str(answer).c_str());
  return 0;
}
