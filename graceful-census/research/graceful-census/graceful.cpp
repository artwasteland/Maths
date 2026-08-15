// research/graceful-census/graceful.cpp
//
// Independent C++ engine for counting GRACEFUL LABELINGS of a graph, used to
// (a) reach terms beyond the JS counters' range and (b) serve as a THIRD,
// structurally separate code path (different language + bitmask implementation)
// that must agree with the two JS counters on every overlapping term.
//
// Reads a graph from stdin:  first line "v m", then m lines "a b" (0-indexed).
// Prints the exact count of graceful labelings (all complement pairs) to stdout.
//
// Method: assign a label in {0..m} to each vertex in a greedy most-constrained
// order (max already-placed neighbours first), pruning on the set of used edge
// differences. 64-bit masks for used labels / used differences (needs m <= 63).
// The running count is unsigned __int128 (prints via a base-10 helper), so it
// never overflows for the ranges we reach.
//
//   g++ -O3 -march=native -o graceful graceful.cpp
//   node -e '...build graph...' | ./graceful

#include <cstdio>
#include <cstdint>
#include <vector>
#include <algorithm>
#include <string>
using namespace std;

typedef unsigned __int128 u128;

int V, M;
vector<vector<int>> adj;
vector<int> order_;             // vertex visiting order
vector<vector<int>> backNbr;    // earlier-order neighbours of order_[idx]
int labelOf[64];                // label assigned to each vertex (-1 if none)
uint64_t usedLabel, usedDiff;
u128 count_;
int rootLabel = -1;            // if >=0, only try this label for order_[0] (sharding)

void rec(int idx) {
    if (idx == V) { count_++; return; }
    int v = order_[idx];
    const vector<int>& bn = backNbr[idx];
    for (int L = 0; L <= M; L++) {
        if (idx == 0 && rootLabel >= 0 && L != rootLabel) continue; // shard on root label
        if (usedLabel >> L & 1ULL) continue;
        bool ok = true;
        uint64_t added = 0;
        for (int k = 0; k < (int)bn.size(); k++) {
            int d = L - labelOf[bn[k]]; if (d < 0) d = -d;
            if (d < 1 || d > M || (usedDiff >> d & 1ULL)) { ok = false; break; }
            usedDiff |= (1ULL << d); added |= (1ULL << d);
        }
        if (ok) {
            usedLabel |= (1ULL << L); labelOf[v] = L;
            rec(idx + 1);
            labelOf[v] = -1; usedLabel &= ~(1ULL << L);
        }
        usedDiff &= ~added;
    }
}

string toStr(u128 x) {
    if (x == 0) return "0";
    string s;
    while (x > 0) { s += char('0' + (int)(x % 10)); x /= 10; }
    reverse(s.begin(), s.end());
    return s;
}

int main(int argc, char** argv) {
    if (argc > 1) rootLabel = atoi(argv[1]);   // optional: shard on order_[0]'s label
    if (scanf("%d %d", &V, &M) != 2) return 1;
    if (M > 63) { fprintf(stderr, "m=%d exceeds 63-bit mask\n", M); return 2; }
    adj.assign(V, {});
    for (int i = 0; i < M; i++) { int a, b; if (scanf("%d %d", &a, &b) != 2) return 1; adj[a].push_back(b); adj[b].push_back(a); }
    // greedy order: max already-placed neighbours, tie -> higher degree, then lower id
    vector<char> placed(V, 0);
    for (int step = 0; step < V; step++) {
        int best = -1, bestBack = -1, bestDeg = -1;
        for (int u = 0; u < V; u++) {
            if (placed[u]) continue;
            int back = 0; for (int w : adj[u]) if (placed[w]) back++;
            if (back > bestBack || (back == bestBack && (int)adj[u].size() > bestDeg)) { best = u; bestBack = back; bestDeg = adj[u].size(); }
        }
        placed[best] = 1; order_.push_back(best);
    }
    vector<int> pos(V); for (int i = 0; i < V; i++) pos[order_[i]] = i;
    backNbr.assign(V, {});
    for (int i = 0; i < V; i++) { int v = order_[i]; for (int w : adj[v]) if (pos[w] < i) backNbr[i].push_back(w); }
    for (int i = 0; i < V; i++) labelOf[i] = -1;
    usedLabel = usedDiff = 0; count_ = 0;
    rec(0);
    printf("%s\n", toStr(count_).c_str());
    return 0;
}
