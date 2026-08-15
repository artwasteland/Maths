// ─────────────────────────────────────────────────────────────────────────────
// Labeled chip-firing on Z — the scaling enumerator (odd N).
//
//   N = 2n+1 labeled chips start at the origin. Fire any unstable site (≥2 chips)
//   by sending the lesser-labeled of a chosen pair left and the greater right.
//   Count the DISTINCT stable terminal permutations reachable = OEIS A282901(n).
//
//   State encoding: nibble l (l = 0..N-1) holds the position (0..N-1) of label
//   l+1, packed into a uint64_t (N ≤ 15). For odd N the support never touches the
//   boundary sites 0 and N-1, so no chip is ever pushed to −1 or N; the assert
//   below enforces that invariant (it never triggers). Visited set is a flat
//   open-addressing hash of uint64_t so the table is ~8 bytes/state.
//
//   Reproduces A282901 term-for-term: N=1,3,5,7,9 → 1,3,12,54,232 (see verify.mjs
//   and the JS enumerators enum.mjs, which agree on every odd N ≤ 9). New:
//   N=11 → a(5)=819 (6 520 201 configs); N=13 → a(6) (this is the wall).
//
//   Build:  g++ -O3 -march=native -o cf cf.cpp
//   Run:    ./cf 11        # a(5)   (default table 2^24 slots)
//           ./cf 13 30     # a(6)   (2^30 slots ≈ 8.6 GB)
// ─────────────────────────────────────────────────────────────────────────────
#include <cstdio>
#include <cstdint>
#include <vector>
#include <cstdlib>
#include <cassert>
using namespace std;

static int N;
static inline int      getp(uint64_t s, int lab)          { return (int)((s >> (4 * lab)) & 0xF); }
static inline uint64_t setp(uint64_t s, int lab, int p)   { uint64_t m = ~(0xFULL << (4 * lab)); return (s & m) | ((uint64_t)p << (4 * lab)); }

struct FlatSet {                       // open-addressing set of uint64_t (EMPTY = ~0)
  vector<uint64_t> t; size_t mask, cnt = 0; static const uint64_t EMPTY = ~0ULL;
  void init(int log2) { t.assign((size_t)1 << log2, EMPTY); mask = ((size_t)1 << log2) - 1; cnt = 0; }
  static inline uint64_t mix(uint64_t x) { x ^= x >> 33; x *= 0xff51afd7ed558ccdULL; x ^= x >> 33; x *= 0xc4ceb9fe1a85ec53ULL; x ^= x >> 33; return x; }
  bool insert(uint64_t k) { size_t i = mix(k) & mask; while (t[i] != EMPTY) { if (t[i] == k) return false; i = (i + 1) & mask; } t[i] = k; cnt++; return true; }
};

int main(int argc, char** argv) {
  if (argc < 2) { fprintf(stderr, "usage: cf N [log2_slots]\n"); return 1; }
  N = atoi(argv[1]);
  int log2 = argc > 2 ? atoi(argv[2]) : 24;
  int origin = (N - 1) / 2;
  uint64_t start = 0;
  for (int l = 0; l < N; l++) start = setp(start, l, origin);

  FlatSet seen; seen.init(log2);
  vector<uint64_t> stack; stack.reserve(1 << 20);
  seen.insert(start); stack.push_back(start);
  uint64_t stablePerms = 0;

  while (!stack.empty()) {
    uint64_t s = stack.back(); stack.pop_back();
    int cnt[16] = {0}; static int at[16][16];
    for (int l = 0; l < N; l++) { int p = getp(s, l); at[p][cnt[p]++] = l; }
    bool stable = true;
    for (int p = 0; p < N; p++) if (cnt[p] > 1) { stable = false; break; }
    if (stable) { stablePerms++; continue; }              // a distinct reachable permutation
    for (int p = 0; p < N; p++) {
      if (cnt[p] < 2) continue;
      assert(p > 0 && p < N - 1);                          // odd-N invariant: boundary never fires
      for (int i = 0; i < cnt[p]; i++) for (int j = i + 1; j < cnt[p]; j++) {
        int a = at[p][i], b = at[p][j];                    // labels scanned ascending ⇒ a<b
        uint64_t ns = setp(s, a, p - 1); ns = setp(ns, b, p + 1);
        if (seen.insert(ns)) stack.push_back(ns);
      }
    }
  }
  printf("N=%d n=%d: a(n)=%llu configs=%zu load=%.3f\n",
         N, (N - 1) / 2, (unsigned long long)stablePerms, seen.cnt, (double)seen.cnt / seen.t.size());
  return 0;
}
