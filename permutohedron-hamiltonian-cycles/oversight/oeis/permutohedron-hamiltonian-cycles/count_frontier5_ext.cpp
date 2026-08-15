// count_frontier5_ext.cpp — EXTERNAL-MEMORY exact Hamiltonian-cycle counter.
//
// Same proven transition logic as count_frontier4.cpp (TdZdd's HamiltonCycleZdd,
// lookahead OFF so children always land exactly one level down), but the state
// table lives on DISK, not in RAM: classic delayed-duplicate-detection.
//
//   - A level's states are (24-byte packed mate key, 128-bit count) records,
//     hash-partitioned into B bucket files, zstd-compressed in framed chunks.
//   - EXPAND: stream each parent bucket, apply both edge decisions via
//     spec.getChild, append children to per-thread per-bucket buffers; full
//     buffers are sorted, locally deduped, compressed, appended as one "run".
//   - COMPACT: per child bucket, load all runs, sort, merge equal keys by
//     summing counts (overflow-checked), write one compacted bucket file.
//   - A manifest is written after every completed level -> crash-resumable.
//
// This removes RAM as the binding constraint: the in-RAM sweep OOMs a 15 GB
// box around level 176 of 240, and the measured census (see
// research/permutohedron-a5/WALL.md) shows the mid-sweep table is terabyte-
// scale — so the state table lives on disk, sized per level, and RAM holds
// only buffers. All arithmetic is 128-bit with explicit overflow checks; mate
// values are range-checked before packing; any I/O error aborts loudly.
//
// Validated: n=3 -> 1, n=4 -> 44, and random graphs vs brute force + vs
// count_frontier4, including with tiny buffers/many buckets to force every
// spill/merge path (see validate-ext.sh).
//
// Build: g++ -O3 -march=native -pthread -I/tmp/TdZdd/include \
//        -o count_frontier5_ext count_frontier5_ext.cpp -lzstd
// Run:   ./count_frontier5_ext graph.dat workdir/
// Env knobs: A5_THREADS · A5_ZLEVEL · A5_HASH_SEED · A5_MIN_FREE_GB (abort-below
//   floor, default 3) · A5_BUFMEM_MB (RAM budget for buffers & per-thread bucket
//   loads, default 3072 — raise on big-RAM boxes for full-speed peak levels)
//   · A5_TARGET_MB (per-bucket raw target, default 384) · A5_BUCKETS/A5_BUFREC
//   (force FIXED values, overriding the per-level adaptive sizing; used by the
//   validation battery's hostile-knob sweeps).
// Bucket count adapts per level to the level's measured size (manifest carries
// buckets+states per checkpoint), and worker counts self-throttle when a peak
// level's buckets outgrow the RAM budget — so the run degrades to slower, never
// to OOM. The per-level census (levels.csv) is unchanged by any of these knobs;
// it is bit-identical across bucketings (regression-checked against the archived
// levels-bs5-partial.csv).
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <cinttypes>
#include <string>
#include <vector>
#include <thread>
#include <mutex>
#include <atomic>
#include <algorithm>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <sys/resource.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <zstd.h>
#include <tdzdd/util/MessageHandler.hpp>
#include <tdzdd/util/Graph.hpp>
#include <tdzdd/spec/PathZdd.hpp>

using namespace tdzdd;
typedef unsigned __int128 u128;
typedef int16_t Mate;

static const int KEYB = 24;          // fixed key size; graphs with W>24 are rejected
struct Rec { uint8_t k[KEYB]; uint64_t lo, hi; };   // 40 bytes, no padding
static_assert(sizeof(Rec) == KEYB + 16, "Rec must be packed to 40 bytes");

static inline u128 rc(const Rec& r){ return ((u128)r.hi << 64) | r.lo; }
static inline void wc(Rec& r, u128 c){ r.lo = (uint64_t)c; r.hi = (uint64_t)(c >> 64); }
static inline bool addChecked(u128& a, u128 b){ u128 s = a + b; if (s < a) return false; a = s; return true; }

static std::string u128str(u128 x){ if(!x) return "0"; char b[48]; int p=48; while(x){ b[--p]='0'+(int)(x%10); x/=10; } return std::string(b+p,48-p); }
static u128 parseU128(const char* s){ u128 x=0; for(; *s>='0'&&*s<='9'; ++s) x = x*10 + (u128)(*s-'0'); return x; }

[[noreturn]] static void die(const char* what){ fprintf(stderr, "FATAL: %s (errno=%d %s)\n", what, errno, strerror(errno)); exit(2); }

// ---------- config ----------
// Bucket count and buffer size adapt PER LEVEL to the level's measured size, so
// RAM stays bounded (~a few GB) whether a level holds 10^3 states or 10^11:
//   B_child  = smallest power of 2 keeping a bucket's pre-dedup raw <= TARGET
//   (children <= 2x parent records, a hard bound), clamped to [64, BMAX];
//   BUFREC   = BUF_BYTES / (threads x B_child x sizeof(Rec)).
// A5_BUCKETS / A5_BUFREC, if set, force fixed values (used by the validation
// battery's hostile-knob sweeps; also preserves old behavior exactly).
static int NTHREADS, ZLEVEL, FIXED_B; static size_t FIXED_BUFREC;
static uint64_t HASH_SEED; static double MIN_FREE_GB;
static size_t TARGET_BUCKET_RAW, BUF_BYTES;
static const int BMAX = 8192;
static std::string DIR;

static inline int pow2ceil(double x){ int b = 1; while (b < x && b < BMAX) b <<= 1; return b; }
static int childBuckets(size_t parentRecs){
  if (FIXED_B) return FIXED_B;
  int b = pow2ceil((double)(2 * parentRecs) * sizeof(Rec) / (double)TARGET_BUCKET_RAW);
  return b < 64 ? 64 : b;
}
static size_t bufrecFor(int Bc){
  if (FIXED_BUFREC) return FIXED_BUFREC;
  size_t r = BUF_BYTES / ((size_t)NTHREADS * Bc * sizeof(Rec));
  return r < 1024 ? 1024 : (r > 65536 ? 65536 : r);
}

static inline uint64_t hashKey(const uint8_t* k){
  uint64_t h = 1469598103934665603ULL ^ HASH_SEED;
  for(int i=0;i<KEYB;i++){ h ^= k[i]; h *= 1099511628211ULL; }
  h ^= h >> 33; h *= 0xff51afd7ed558ccdULL; h ^= h >> 33;
  return h;
}

static std::string lvlPath(int L, int b){ char p[512]; snprintf(p,sizeof p, "%s/lvl%d_b%d.z", DIR.c_str(), L, b); return p; }
static std::string runPath(int L, int b){ char p[512]; snprintf(p,sizeof p, "%s/run%d_b%d.z", DIR.c_str(), L, b); return p; }

// ---------- framed zstd file I/O ----------
// v1 frame = [u64 nrec][u64 compBytes][zstd of nrec*sizeof(Rec) row-major raw]
// v2 frame = [u64 nrec|VERBIT][u64 rawBytes][u64 compBytes][zstd of transposed payload]
//   v2 payload: KEYB columns of nrec bytes each (records are sorted, so columns are
//   long near-constant runs zstd crushes), then LEB128 varints of the u128 counts.
//   ~4-8x smaller on disk than v1 at the same zstd level. Reader accepts both, so a
//   run checkpointed under v1 resumes seamlessly under a v2 binary.
static const uint64_t VERBIT = 1ULL << 63;

static size_t encodeV2(const Rec* recs, size_t n, std::vector<uint8_t>& raw){
  raw.resize(KEYB * n + 19 * n);          // worst-case varint space
  uint8_t* p = raw.data();
  for (int k = 0; k < KEYB; ++k){ for (size_t i = 0; i < n; ++i) p[i] = recs[i].k[k]; p += n; }
  for (size_t i = 0; i < n; ++i){
    u128 c = rc(recs[i]);
    do { uint8_t b = (uint8_t)(c & 0x7f); c >>= 7; *p++ = b | (c ? 0x80 : 0); } while (c);
  }
  return p - raw.data();
}
static void decodeV2(const uint8_t* raw, size_t rawBytes, size_t n, Rec* out){
  const uint8_t* p = raw;
  for (int k = 0; k < KEYB; ++k){ for (size_t i = 0; i < n; ++i) out[i].k[k] = p[i]; p += n; }
  const uint8_t* end = raw + rawBytes;
  for (size_t i = 0; i < n; ++i){
    u128 c = 0; int sh = 0;
    for(;;){ if (p >= end) die("v2 varint truncated"); uint8_t b = *p++; c |= (u128)(b & 0x7f) << sh; if (!(b & 0x80)) break; sh += 7; if (sh > 126) die("v2 varint overlong"); }
    wc(out[i], c);
  }
  if (p != end) die("v2 payload trailing bytes");
}

static void appendFrame(FILE* f, ZSTD_CCtx* cc, const Rec* recs, size_t n, std::vector<uint8_t>& scratch){
  static thread_local std::vector<uint8_t> raw;
  size_t rawBytes = encodeV2(recs, n, raw);
  size_t bound = ZSTD_compressBound(rawBytes);
  if (scratch.size() < bound) scratch.resize(bound);
  size_t comp = ZSTD_compressCCtx(cc, scratch.data(), bound, raw.data(), rawBytes, ZLEVEL);
  if (ZSTD_isError(comp)) die("zstd compress");
  uint64_t hdr[3] = { (uint64_t)n | VERBIT, (uint64_t)rawBytes, (uint64_t)comp };
  if (fwrite(hdr, 8, 3, f) != 3) die("fwrite frame header");
  if (fwrite(scratch.data(), 1, comp, f) != comp) die("fwrite frame body");
}

// read entire framed file into out (appending); missing file = empty; returns rec count
static size_t readAll(const std::string& path, ZSTD_DCtx* dc, std::vector<Rec>& out){
  FILE* f = fopen(path.c_str(), "rb");
  if (!f){ if (errno == ENOENT) return 0; die("fopen read"); }
  std::vector<uint8_t> comp; static thread_local std::vector<uint8_t> raw;
  size_t added = 0;
  for(;;){
    uint64_t h0;
    size_t got = fread(&h0, 8, 1, f);
    if (got == 0 && feof(f)) break;
    if (got != 1) die("fread frame header");
    if (h0 & VERBIT){                                   // v2
      uint64_t hdr[2];
      if (fread(hdr, 8, 2, f) != 2) die("fread v2 header");
      size_t n = h0 & ~VERBIT, rawBytes = hdr[0], cb = hdr[1];
      comp.resize(cb);
      if (fread(comp.data(), 1, cb, f) != cb) die("fread frame body");
      raw.resize(rawBytes);
      size_t r = ZSTD_decompressDCtx(dc, raw.data(), rawBytes, comp.data(), cb);
      if (ZSTD_isError(r) || r != rawBytes) die("zstd decompress v2");
      size_t old = out.size(); out.resize(old + n);
      decodeV2(raw.data(), rawBytes, n, out.data()+old);
      added += n;
    } else {                                            // v1 (legacy row-major)
      uint64_t h1;
      if (fread(&h1, 8, 1, f) != 1) die("fread v1 header");
      size_t n = h0, cb = h1;
      comp.resize(cb);
      if (fread(comp.data(), 1, cb, f) != cb) die("fread frame body");
      size_t old = out.size(); out.resize(old + n);
      size_t r = ZSTD_decompressDCtx(dc, out.data()+old, n*sizeof(Rec), comp.data(), cb);
      if (ZSTD_isError(r) || r != n*sizeof(Rec)) die("zstd decompress v1");
      added += n;
    }
  }
  fclose(f);
  return added;
}

static inline bool keyLess(const Rec& a, const Rec& b){ return memcmp(a.k, b.k, KEYB) < 0; }
static inline bool keyEq(const Rec& a, const Rec& b){ return memcmp(a.k, b.k, KEYB) == 0; }

// sort + merge equal keys in place; returns new size. Aborts on count overflow.
static size_t sortDedupe(std::vector<Rec>& v){
  std::sort(v.begin(), v.end(), keyLess);
  size_t o = 0;
  for (size_t i = 0; i < v.size(); ){
    Rec r = v[i]; u128 c = rc(r); size_t j = i+1;
    for (; j < v.size() && keyEq(v[j], r); ++j)
      if (!addChecked(c, rc(v[j]))) die("128-bit count overflow in dedupe");
    wc(r, c); v[o++] = r; i = j;
  }
  v.resize(o);
  return o;
}

// ---------- shared per-level state ----------
struct BucketOut {           // one child bucket: append-only run file
  std::mutex mtx;
  FILE* f = nullptr;
  std::string path;
  void ensureOpen(){ if(!f){ f = fopen(path.c_str(), "ab"); if(!f) die("fopen run append"); } }
};

static double freeGB(){ struct statvfs s; if (statvfs(DIR.c_str(), &s)) die("statvfs"); return (double)s.f_bavail * s.f_frsize / (1024.0*1024*1024); }
static long rssMB(){ FILE* f=fopen("/proc/self/status","r"); if(!f) return -1; char ln[256]; long kb=-1; while(fgets(ln,sizeof ln,f)) if(!strncmp(ln,"VmRSS:",6)) sscanf(ln+6,"%ld",&kb); fclose(f); return kb/1024; }

int main(int argc, char** argv){
  if (argc < 3){ fprintf(stderr, "usage: %s graph.dat workdir/\n", argv[0]); return 1; }
  DIR = argv[2];
  mkdir(DIR.c_str(), 0755);
  NTHREADS = getenv("A5_THREADS") ? atoi(getenv("A5_THREADS")) : (int)std::thread::hardware_concurrency();
  if (NTHREADS < 1) NTHREADS = 1;
  FIXED_B = getenv("A5_BUCKETS") ? atoi(getenv("A5_BUCKETS")) : 0;                    // 0 = adaptive
  if (FIXED_B && (FIXED_B & (FIXED_B-1))) { fprintf(stderr,"A5_BUCKETS must be a power of 2\n"); return 1; }
  if (FIXED_B > BMAX) { fprintf(stderr,"A5_BUCKETS must be <= %d\n", BMAX); return 1; }
  FIXED_BUFREC = getenv("A5_BUFREC") ? (size_t)atoll(getenv("A5_BUFREC")) : 0;        // 0 = adaptive
  ZLEVEL  = getenv("A5_ZLEVEL") ? atoi(getenv("A5_ZLEVEL")) : 1;
  HASH_SEED = getenv("A5_HASH_SEED") ? strtoull(getenv("A5_HASH_SEED"),0,0) : 0;
  MIN_FREE_GB = getenv("A5_MIN_FREE_GB") ? atof(getenv("A5_MIN_FREE_GB")) : 3.0;
  TARGET_BUCKET_RAW = getenv("A5_TARGET_MB") ? (size_t)atoll(getenv("A5_TARGET_MB"))<<20 : (size_t)384<<20;
  BUF_BYTES = getenv("A5_BUFMEM_MB") ? (size_t)atoll(getenv("A5_BUFMEM_MB"))<<20 : (size_t)3072<<20;
  int STOP_AT = getenv("A5_STOP_AT_LEVEL") ? atoi(getenv("A5_STOP_AT_LEVEL")) : -1;   // clean exit after this level compacts (resume test)
  { struct rlimit rl;                                   // adaptive B can hold up to BMAX run files open
    if (getrlimit(RLIMIT_NOFILE, &rl) == 0 && rl.rlim_cur < 2*BMAX + 64){
      rl.rlim_cur = (rl.rlim_max == RLIM_INFINITY || rl.rlim_max > 2*BMAX + 64) ? 2*BMAX + 64 : rl.rlim_max;
      setrlimit(RLIMIT_NOFILE, &rl);
    }
    if (getrlimit(RLIMIT_NOFILE, &rl) == 0 && rl.rlim_cur < (rlim_t)(BMAX + 64) && !FIXED_B)
      fprintf(stderr, "warning: fd limit %llu < %d; adaptive bucketing may hit it at peak levels\n",
              (unsigned long long)rl.rlim_cur, BMAX + 64);
  }

  Graph g; g.readAdjacencyList(argv[1]);
  int E = g.edgeSize();
  fprintf(stderr, "#vertex=%d #edge=%d max_frontier=%d threads=%d buckets=%s zlevel=%d\n",
          g.vertexSize(), E, g.maxFrontierSize(), NTHREADS,
          FIXED_B ? "fixed" : "adaptive", ZLEVEL);
  HamiltonCycleZdd spec(g, false);              // lookahead OFF: children go exactly one level down
  const int W = spec.mateArraySize();
  if (W > KEYB){ fprintf(stderr, "graph frontier %d exceeds compiled key size %d\n", W, KEYB); return 1; }
  auto v0at = [&](int L)->int{ return (int)g.edgeInfo(E-L).v0; };

  // --- resume or init ---
  std::string manifest = DIR + "/manifest.txt";
  int curLevel = -1;                            // level whose compacted files exist on disk
  u128 answer = 0;
  int Bprev = 0;                                // bucket count of curLevel's files
  uint64_t prevStates = 0;                      // record count of curLevel's files
  {
    FILE* mf = fopen(manifest.c_str(), "r");
    if (mf){
      char abuf[64]; char tail[8] = {0}; int L, Bm; unsigned long long Sm;
      int got = fscanf(mf, "level %d answer %63s buckets %d states %llu %7s", &L, abuf, &Bm, &Sm, tail);
      if (got >= 2){
        curLevel = L; answer = parseU128(abuf);
        if (got == 5 && strcmp(tail, "end") == 0){ Bprev = Bm; prevStates = Sm; }
        else if (got == 2){ Bprev = 0; prevStates = 0; }  // legacy checkpoint: derive both from disk
        else die("manifest is truncated or malformed — refusing to guess (inspect manifest.txt)");
        fprintf(stderr, "RESUME from manifest: level %d done (%llu states), answer so far %s\n",
                L, (unsigned long long)prevStates, abuf);
      }
      fclose(mf);
    }
  }
  int topLevel;
  {
    std::vector<Mate> mate(W);
    topLevel = spec.getRoot(mate.data());
    if (curLevel < 0){
      // seed the top level with the single root state (clearing any stale
      // seed left by a run that died before its first manifest)
      for (int b = 0; b < BMAX; ++b) remove(lvlPath(topLevel, b).c_str());
      Rec r; memset(&r, 0, sizeof r);
      int v0 = v0at(topLevel);
      for (int k = 0; k < W; ++k){
        int mv = mate[k];
        if (mv && (mv < v0 || mv >= v0 + W)) die("root mate out of window");
        r.k[k] = mv ? (uint8_t)(mv - v0 + 1) : 0;
      }
      wc(r, 1);
      Bprev = childBuckets(1); prevStates = 1;
      ZSTD_CCtx* cc = ZSTD_createCCtx(); std::vector<uint8_t> scratch;
      FILE* f = fopen(lvlPath(topLevel, (int)(hashKey(r.k) & (Bprev-1))).c_str(), "wb");
      if (!f) die("seed fopen");
      appendFrame(f, cc, &r, 1, scratch);
      fclose(f); ZSTD_freeCCtx(cc);
      curLevel = topLevel;
    }
  }

  FILE* statsf = fopen((DIR + "/levels.csv").c_str(), "a");
  if (statsf && ftell(statsf) == 0) fprintf(statsf, "level,states_in,children_raw,states_out,hits,secs,rss_mb,free_gb,answer,buckets,bufrec\n");

  // --- main sweep: curLevel down to 1 ---
  for (int L = curLevel; L >= 1; --L){
    if (freeGB() < MIN_FREE_GB){ fprintf(stderr, "ABORT: free disk %.1f GB below %.1f GB floor (manifest at level %d intact — free space and re-run to resume)\n", freeGB(), MIN_FREE_GB, L); return 3; }
    time_t t0 = time(nullptr);
    const int v0L = v0at(L), v0n = (L > 1) ? v0at(L-1) : 0;

    // Derive the parent's bucket count from the files actually on disk, not
    // from bookkeeping: any file with a higher bucket index than the manifest
    // implies would otherwise be silently treated as empty (dropped states).
    {
      int maxb = -1; struct stat st;
      for (int b = 0; b < BMAX; ++b) if (stat(lvlPath(L, b).c_str(), &st) == 0) maxb = b;
      if (maxb >= 0) Bprev = maxb + 1;
      else if (prevStates > 0) die("resume: manifest claims states but the level has no files on disk");
      else Bprev = 1;                             // legitimately empty level: every state died upstream
    }
    if (prevStates == 0 && L < topLevel){         // legacy checkpoint: estimate records from file bytes
      uint64_t bytes = 0; struct stat st;
      for (int b = 0; b < Bprev; ++b) if (stat(lvlPath(L, b).c_str(), &st) == 0) bytes += st.st_size;
      prevStates = bytes / 5 + 1;                 // mid-band of the measured 3.3-12 B/state on-disk range
    }
    const int Bp = Bprev;                          // parent's bucket count
    int Bc = childBuckets(prevStates);             // child bucket count, sized to the level
    { struct rlimit rl;                            // never exceed what we can actually open
      if (getrlimit(RLIMIT_NOFILE, &rl) == 0 && rl.rlim_cur != RLIM_INFINITY){
        while (Bc > 64 && (rlim_t)(Bc + NTHREADS + 64) > rl.rlim_cur) Bc >>= 1;
      }
    }
    const size_t bufrec = bufrecFor(Bc);
    // At extreme levels a single bucket outgrows TARGET (Bc capped at BMAX);
    // throttle worker counts so RAM stays inside BUF_BYTES instead of OOMing.
    // A worker's footprint = its parent-bucket load + its full set of write
    // buffers (Bc x bufrec recs); a compactor's = one pre-dedup child bucket
    // plus its compacted copy (~1.5x).
    size_t parentRaw = Bp ? (prevStates * sizeof(Rec)) / (size_t)Bp : 0;
    size_t childRaw  = (2 * prevStates * sizeof(Rec)) / (size_t)Bc;
    size_t perExpand  = parentRaw + (size_t)Bc * bufrec * sizeof(Rec);
    size_t perCompact = childRaw + childRaw / 2;
    int expandThreads  = (int)std::min((size_t)NTHREADS, std::max((size_t)1, BUF_BYTES / std::max(perExpand,  (size_t)1)));
    int compactThreads = (int)std::min((size_t)NTHREADS, std::max((size_t)1, BUF_BYTES / std::max(perCompact, (size_t)1)));
    if (expandThreads < NTHREADS || compactThreads < NTHREADS)
      fprintf(stderr, "  level %d: RAM-throttled to %d expand / %d compact threads (raise A5_BUFMEM_MB on a bigger box)\n", L, expandThreads, compactThreads);

    // stale files from an interrupted attempt at this level: truncate both the
    // runs AND any partially-compacted child level (an interrupted compact can
    // leave lvl(L-1) buckets that would otherwise survive if their re-expanded
    // run bucket happened to be empty). Sweep the FULL possible bucket range —
    // the interrupted attempt may have used a different bucket count.
    for (int b = 0; b < BMAX; ++b){ remove(runPath(L-1, b).c_str()); remove(lvlPath(L-1, b).c_str()); }

    std::vector<BucketOut> outs(Bc);
    for (int b = 0; b < Bc; ++b) outs[b].path = runPath(L-1, b);

    std::atomic<int> nextBucket{0};
    std::atomic<uint64_t> statesIn{0}, childrenRaw{0}, hits{0};
    std::mutex ansMtx; u128 ansLevel = 0;
    std::atomic<bool> failed{false};

    auto worker = [&](){
      ZSTD_CCtx* cc = ZSTD_createCCtx(); ZSTD_DCtx* dc = ZSTD_createDCtx();
      std::vector<uint8_t> scratch;
      std::vector<std::vector<Rec>> buf(Bc);
      std::vector<Mate> tmp(W);
      u128 myAns = 0; uint64_t myIn = 0, myKids = 0, myHits = 0;
      auto flush = [&](int b){
        if (buf[b].empty()) return;
        sortDedupe(buf[b]);
        std::lock_guard<std::mutex> lk(outs[b].mtx);
        outs[b].ensureOpen();
        appendFrame(outs[b].f, cc, buf[b].data(), buf[b].size(), scratch);
        buf[b].clear();
      };
      std::vector<Rec> in;
      for(;;){
        int b = nextBucket.fetch_add(1);
        if (b >= Bp) break;
        in.clear();
        readAll(lvlPath(L, b), dc, in);
        myIn += in.size();
        for (const Rec& r : in){
          u128 c = rc(r);
          for (int val = 0; val < 2; ++val){
            for (int k = 0; k < W; ++k){ int rel = r.k[k]; tmp[k] = rel ? (Mate)(rel - 1 + v0L) : 0; }
            int nl = spec.getChild(tmp.data(), L, val);
            if (nl == -1){ myHits++; if (!addChecked(myAns, c)) { failed = true; die("answer overflow"); } }
            else if (nl > 0){
              if (nl != L - 1) die("spec skipped a level with lookahead off — invariant broken");
              Rec ch; memset(&ch, 0, sizeof ch);
              for (int k = 0; k < W; ++k){
                int mv = tmp[k];
                if (mv && (mv < v0n || mv >= v0n + W)) die("child mate out of window");
                ch.k[k] = mv ? (uint8_t)(mv - v0n + 1) : 0;
              }
              wc(ch, c);
              int cb = (int)(hashKey(ch.k) & (uint64_t)(Bc-1));
              buf[cb].push_back(ch);
              myKids++;
              if (buf[cb].size() >= bufrec) flush(cb);
            }
          }
        }
      }
      for (int b = 0; b < Bc; ++b) flush(b);
      statesIn += myIn; childrenRaw += myKids; hits += myHits;
      { std::lock_guard<std::mutex> lk(ansMtx); if (!addChecked(ansLevel, myAns)) die("answer overflow (reduce)"); }
      ZSTD_freeCCtx(cc); ZSTD_freeDCtx(dc);
    };
    { std::vector<std::thread> ts; for (int t = 0; t < expandThreads; ++t) ts.emplace_back(worker); for (auto& t : ts) t.join(); }
    if (failed) return 2;
    for (int b = 0; b < Bc; ++b) if (outs[b].f) fclose(outs[b].f);
    if (!addChecked(answer, ansLevel)) die("answer overflow (global)");

    // COMPACT level L-1: merge runs per bucket
    std::atomic<uint64_t> statesOut{0};
    if (L > 1){
      std::atomic<int> nb{0};
      auto compactor = [&](){
        ZSTD_CCtx* cc = ZSTD_createCCtx(); ZSTD_DCtx* dc = ZSTD_createDCtx();
        std::vector<uint8_t> scratch; std::vector<Rec> v;
        for(;;){
          int b = nb.fetch_add(1);
          if (b >= Bc) break;
          v.clear();
          if (!readAll(runPath(L-1, b), dc, v)) { remove(runPath(L-1, b).c_str()); continue; }
          sortDedupe(v);
          FILE* f = fopen(lvlPath(L-1, b).c_str(), "wb");
          if (!f) die("compact fopen");
          const size_t CHUNK = (64u<<20) / sizeof(Rec);           // 64 MB raw frames
          for (size_t i = 0; i < v.size(); i += CHUNK) appendFrame(f, cc, v.data()+i, std::min(CHUNK, v.size()-i), scratch);
          fclose(f);
          remove(runPath(L-1, b).c_str());
          statesOut += v.size();
        }
        ZSTD_freeCCtx(cc); ZSTD_freeDCtx(dc);
      };
      std::vector<std::thread> ts; for (int t = 0; t < compactThreads; ++t) ts.emplace_back(compactor); for (auto& t : ts) t.join();
    } else {
      for (int b = 0; b < BMAX; ++b) remove(runPath(0, b).c_str());  // no level-0 states can exist
    }

    // manifest (atomic + durable: fsync before and after the rename, and a
    // trailing sentinel so a truncated write can never parse as a valid,
    // shorter record), then drop the parent level's files
    {
      std::string tmpm = manifest + ".tmp";
      FILE* mf = fopen(tmpm.c_str(), "w");
      if (!mf) die("manifest fopen");
      fprintf(mf, "level %d answer %s buckets %d states %llu end\n", L-1, u128str(answer).c_str(),
              Bc, (unsigned long long)statesOut.load());
      if (fflush(mf) || fsync(fileno(mf))) die("manifest fsync");
      fclose(mf);
      if (rename(tmpm.c_str(), manifest.c_str())) die("manifest rename");
      int dfd = open(DIR.c_str(), O_RDONLY);
      if (dfd >= 0){ fsync(dfd); close(dfd); }
    }
    for (int b = 0; b < Bp; ++b) remove(lvlPath(L, b).c_str());
    Bprev = Bc; prevStates = statesOut.load();

    long secs = (long)(time(nullptr) - t0);
    fprintf(stderr, "level %3d: in=%" PRIu64 " kids=%" PRIu64 " out=%" PRIu64 " hits=%" PRIu64 " ans=%s  %lds rss=%ldMB free=%.1fGB B=%d buf=%zu\n",
            L, statesIn.load(), childrenRaw.load(), statesOut.load(), hits.load(), u128str(answer).c_str(), secs, rssMB(), freeGB(), Bc, bufrec);
    if (statsf){ fprintf(statsf, "%d,%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%ld,%ld,%.2f,%s,%d,%zu\n", L, statesIn.load(), childrenRaw.load(), statesOut.load(), hits.load(), secs, rssMB(), freeGB(), u128str(answer).c_str(), Bc, bufrec); fflush(statsf); }
    if (STOP_AT >= 0 && L - 1 == STOP_AT){ fprintf(stderr, "STOP_AT_LEVEL %d reached — exiting cleanly (resume from manifest)\n", STOP_AT); return 42; }
  }
  if (statsf) fclose(statsf);
  printf("UNDIRECTED Hamiltonian cycles = %s\n", u128str(answer).c_str());
  return 0;
}
