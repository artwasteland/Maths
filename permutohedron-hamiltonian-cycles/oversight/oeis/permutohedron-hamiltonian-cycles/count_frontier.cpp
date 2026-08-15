// Exact count of undirected Hamiltonian cycles of a graph, by a memory-light
// frontier sweep that REUSES TdZdd's proven HamiltonCycleZdd transition logic
// (getRoot/getChild) but never materialises the whole ZDD: it carries a
// map<frontier-state, count> per level and discards each level once processed.
// Peak memory is the single widest frontier level, not the whole diagram, so it
// can finish where a full ZDD build runs out of RAM.
//
// The transition function is exactly TdZdd's (validated: n=4 -> 44); this file
// only changes the *traversal* (count paths to the TRUE terminal level-by-level).
//
// Build: g++ -O3 -march=native -I/tmp/TdZdd/include -o count_frontier count_frontier.cpp
// Run:   ./count_frontier graph.dat
#include <cstdio>
#include <cstdint>
#include <string>
#include <vector>
#include <unordered_map>
#include <iostream>
#include <tdzdd/util/MessageHandler.hpp>
#include <tdzdd/util/Graph.hpp>
#include <tdzdd/spec/PathZdd.hpp>

using namespace tdzdd;
typedef unsigned __int128 u128;
typedef int16_t Mate;

static std::string u128str(u128 x){
  if(x==0) return "0";
  char buf[40]; int p=40; while(x){ buf[--p]='0'+(int)(x%10); x/=10; }
  return std::string(buf+p, 40-p);
}

int main(int argc, char** argv){
  if(argc<2){ fprintf(stderr,"usage: %s graph.dat\n",argv[0]); return 1; }
  Graph g;
  g.readAdjacencyList(argv[1]);
  int M = g.vertexSize(), E = g.edgeSize();
  fprintf(stderr,"#vertex=%d #edge=%d max_frontier=%d\n", M, E, g.maxFrontierSize());

  HamiltonCycleZdd spec(g);            // proven transition logic
  int W = spec.mateArraySize();

  // root level + initial mate
  std::vector<Mate> rootMate(W);
  int topLevel = spec.getRoot(rootMate.data());
  fprintf(stderr,"root level=%d  mate-array size=%d\n", topLevel, W);

  // level -> map<state bytes, count>
  std::vector<std::unordered_map<std::string,u128>> level(topLevel+1);
  level[topLevel][ std::string((char*)rootMate.data(), W*sizeof(Mate)) ] = 1;

  u128 answer = 0;
  size_t peak = 0;
  std::vector<Mate> tmp(W);
  for(int L=topLevel; L>=1; --L){
    auto &mp = level[L];
    if(mp.size()>peak) peak=mp.size();
    if(L%10==0 || mp.size()>1000000)
      fprintf(stderr,"  level %d : %zu states  (answer so far %s)\n", L, mp.size(), u128str(answer).c_str());
    for(auto &kv : mp){
      u128 c = kv.second;
      const Mate* base = (const Mate*)kv.first.data();
      for(int val=0; val<2; ++val){
        memcpy(tmp.data(), base, W*sizeof(Mate));
        int nl = spec.getChild(tmp.data(), L, val);
        if(nl == -1){ answer += c; }
        else if(nl > 0){
          level[nl][ std::string((char*)tmp.data(), W*sizeof(Mate)) ] += c;
        }
        // nl==0 -> dead, drop
      }
    }
    std::unordered_map<std::string,u128>().swap(mp);  // free this level
  }
  fprintf(stderr,"peak level width = %zu states\n", peak);
  printf("UNDIRECTED Hamiltonian cycles = %s\n", u128str(answer).c_str());
  return 0;
}
