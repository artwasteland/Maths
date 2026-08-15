// Most memory-frugal exact Hamiltonian-cycle counter: TdZdd's proven
// HamiltonCycleZdd transitions, lookahead OFF (only 2 levels alive at once), AND
// the mate window stored window-RELATIVE so each slot is 1 byte instead of 2.
// (mate values always lie in {0} U [v0, v0+W); store (mate? mate-v0+1 : 0) in a
// uint8.)  Halves the key size vs count_frontier3 -> ~half the RAM.
//
// Validated identically (n=3->1, n=4->44, random graphs vs brute force).
// Build: g++ -O3 -march=native -I/tmp/TdZdd/include -o count_frontier4 count_frontier4.cpp
// Run:   ./count_frontier4 graph.dat
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
static int W;                 // mate window size
static int KEYB;              // = W bytes (1 byte/slot, packed)

struct FlatMap {
  uint8_t* keys=nullptr; u128* vals=nullptr; uint8_t* used=nullptr; size_t cap=0,cnt=0;
  static inline uint64_t hash(const uint8_t*k){ uint64_t h=1469598103934665603ULL; for(int i=0;i<KEYB;i++){h^=k[i];h*=1099511628211ULL;} return h; }
  void grow();
  inline void add(const uint8_t*k,u128 d){
    if(!keys){ cap=1<<16; keys=(uint8_t*)malloc(cap*KEYB); vals=(u128*)malloc(cap*sizeof(u128)); used=(uint8_t*)calloc(cap,1); cnt=0; }
    if((cnt+1)*10>=cap*7) grow();
    size_t m=cap-1,i=hash(k)&m;
    while(used[i]){ if(memcmp(keys+i*KEYB,k,KEYB)==0){vals[i]+=d;return;} i=(i+1)&m; }
    used[i]=1; memcpy(keys+i*KEYB,k,KEYB); vals[i]=d; cnt++;
  }
  void freeAll(){ free(keys);free(vals);free(used); keys=nullptr;vals=nullptr;used=nullptr;cap=0;cnt=0; }
};
void FlatMap::grow(){
  size_t nc=cap*2; uint8_t*nk=(uint8_t*)malloc(nc*KEYB); u128*nv=(u128*)malloc(nc*sizeof(u128)); uint8_t*nu=(uint8_t*)calloc(nc,1);
  size_t m=nc-1;
  for(size_t i=0;i<cap;i++) if(used[i]){ const uint8_t*k=keys+i*KEYB; size_t j=hash(k)&m; while(nu[j])j=(j+1)&m; nu[j]=1; memcpy(nk+j*KEYB,k,KEYB); nv[j]=vals[i]; }
  free(keys);free(vals);free(used); keys=nk;vals=nv;used=nu;cap=nc;
}

static std::string u128str(u128 x){ if(x==0)return "0"; char b[40]; int p=40; while(x){b[--p]='0'+(int)(x%10);x/=10;} return std::string(b+p,40-p); }

int main(int argc,char**argv){
  if(argc<2){ fprintf(stderr,"usage: %s graph.dat\n",argv[0]); return 1; }
  Graph g; g.readAdjacencyList(argv[1]);
  int E=g.edgeSize();
  fprintf(stderr,"#vertex=%d #edge=%d max_frontier=%d\n", g.vertexSize(), E, g.maxFrontierSize());
  HamiltonCycleZdd spec(g, false);  // nolookahead (2 levels) + packed keys = lowest, most predictable RAM
  W = spec.mateArraySize(); KEYB = W;          // 1 byte/slot

  auto v0at=[&](int L)->int{ return (int)g.edgeInfo(E-L).v0; };  // window base at level L

  std::vector<Mate> mate(W), tmp(W);
  int topLevel = spec.getRoot(mate.data());
  int v0root = v0at(topLevel);
  std::vector<uint8_t> pk(W);
  for(int k=0;k<W;k++){ int mv=mate[k]; pk[k]= mv==0?0:(uint8_t)(mv - v0root + 1); }

  std::vector<FlatMap> level(topLevel+1);
  level[topLevel].add(pk.data(), (u128)1);

  u128 answer=0; size_t peak=0;
  for(int L=topLevel; L>=1; --L){
    FlatMap &mp=level[L]; if(mp.cnt>peak)peak=mp.cnt;
    int v0L=v0at(L);
    if(L%10==0) fprintf(stderr,"  level %d : %zu states  ans=%s\n", L, mp.cnt, u128str(answer).c_str());
    for(size_t i=0;i<mp.cap;i++) if(mp.used[i]){
      u128 c=mp.vals[i]; const uint8_t* key=mp.keys+i*KEYB;
      for(int val=0; val<2; ++val){
        // unpack to absolute window at v0L
        for(int k=0;k<W;k++){ int r=key[k]; tmp[k]= r==0?0:(Mate)(r-1+v0L); }
        int nl=spec.getChild(tmp.data(), L, val);
        if(nl==-1) answer+=c;
        else if(nl>0){
          int v0n=v0at(nl);
          for(int k=0;k<W;k++){ int mv=tmp[k]; pk[k]= mv==0?0:(uint8_t)(mv - v0n + 1); }
          level[nl].add(pk.data(), c);
        }
      }
    }
    mp.freeAll();
  }
  fprintf(stderr,"peak level width = %zu states\n", peak);
  printf("UNDIRECTED Hamiltonian cycles = %s\n", u128str(answer).c_str());
  return 0;
}
