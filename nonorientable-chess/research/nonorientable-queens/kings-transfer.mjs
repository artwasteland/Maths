// research/nonorientable-queens/kings-transfer.mjs
//
// A SECOND, INDEPENDENT exact counter for non-attacking KINGS on the four board
// topologies — a transfer matrix over line-states, structurally unrelated to the
// ray-tracing DFS in engine.mjs. Two unrelated methods that agree on every
// overlapping term are the project's "never one path" trust rule.
//
// King independent sets = placements of any number of mutually non-attacking kings
// (kings attack the 8 Chebyshev-adjacent squares). We sweep one line (column, or row
// for klein) at a time. A "line state" is the occupied-cell subset of that line.
//
// Geometry per surface (matching engine.mjs's gluing):
//   flat   — no gluing. Sweep columns; rows LINEAR; ends OPEN.
//   torus  — both pairs glued straight. Sweep columns; rows CYCLIC; closure STRAIGHT.
//   mobius — left/right glued with a vertical(row) flip; top/bottom free.
//            Sweep columns; rows LINEAR (free); closure FLIPPED (reverse a line).
//   klein  — left/right glued straight; top/bottom glued with a horizontal(col) flip.
//            Sweep ROWS; cols CYCLIC (straight wrap); closure FLIPPED (reverse a line).
//
// Within a line: no two occupied cells adjacent (linear or cyclic per surface).
// Between adjacent lines: cells (p in line A) and (q in line B) attack iff their
// cross-line index differs by <=1 (linear or cyclic) — horizontal + both diagonals.
// The flip seam reverses one line's bitmask before applying the straight rule
// (derived from engine.mjs's step(): crossing a flip seam reflects the transverse
// coordinate p -> n-1-p, so a whole line's occupancy reverses).

function bits(mask, n) { const o=[]; for (let i=0;i<n;i++) if (mask&(1<<i)) o.push(i); return o; }
function reverseBits(mask, n){ let r=0; for(let i=0;i<n;i++) if(mask&(1<<i)) r|=1<<(n-1-i); return r; }

// valid single line: no two occupied adjacent (cyclic ? wrap : linear)
function lineValid(mask, n, cyclic) {
  if (mask & (mask >> 1)) return false;            // linear adjacency
  if (cyclic && n>1 && (mask & 1) && (mask & (1<<(n-1)))) return false; // wrap ends
  return true;
}
// two adjacent lines A,B compatible iff no p in A, q in B with |p-q|<=1 (cyclic|linear)
function compat(a, b, n, cyclic) {
  // B "shadow" = B | B<<1 | B>>1 ; if cyclic, wrap the shifted bits
  let shadow = b | (b<<1) | (b>>1);
  if (cyclic) {
    if (b & 1) shadow |= (1<<(n-1));
    if (b & (1<<(n-1))) shadow |= 1;
  }
  shadow &= (1<<n)-1;
  return (a & shadow) === 0;
}

// Build the list of valid line states and index them.
function states(n, cyclic) {
  const S=[]; for (let m=0;m<(1<<n);m++) if (lineValid(m,n,cyclic)) S.push(m);
  return S;
}

// Dense BigInt transfer matrix T[i][j] = compat(S[i],S[j]) (straight, non-seam).
function transfer(S, n, cyclic) {
  const V=S.length, T=[];
  for (let i=0;i<V;i++){ const row=new Array(V); for(let j=0;j<V;j++) row[j]=compat(S[i],S[j],n,cyclic)?1n:0n; T.push(row);} 
  return T;
}
// Flip-seam matrix: reverse A then straight-compat with B.
function transferFlip(S, n, cyclic) {
  const V=S.length, T=[];
  for (let i=0;i<V;i++){ const ai=reverseBits(S[i],n); const row=new Array(V);
    for(let j=0;j<V;j++) row[j]=compat(ai,S[j],n,cyclic)?1n:0n; T.push(row);} 
  return T;
}
function matmul(A,B){ const n=A.length,m=B[0].length,k=B.length,C=[];
  for(let i=0;i<n;i++){const row=new Array(m).fill(0n);
    for(let t=0;t<k;t++){const a=A[i][t]; if(a) for(let j=0;j<m;j++) row[j]+=a*B[t][j];}
    C.push(row);} return C; }
function matpow(A,p){ let R=null,B=A; while(p>0){ if(p&1) R=R?matmul(R,B):B; p>>=1; if(p>0) B=matmul(B,B);} return R; }
function trace(A){ let s=0n; for(let i=0;i<A.length;i++) s+=A[i][i]; return s; }
function sumAll(A){ let s=0n; for(const r of A) for(const x of r) s+=x; return s; }

// Total non-attacking king placements (all sizes, incl. empty) on n x n `topology`.
function kingTotal(topology, n) {
  if (n===0) return 1n;
  if (topology==='flat') {                 // rows linear, cols open
    const S=states(n,false), T=transfer(S,n,false);
    return sumAll(matpow(T, n-1));         // 1^T T^{n-1} 1, but T^{0}=? handle n=1
      // n=1: matpow(T,0) undefined -> handle below
  }
  if (topology==='torus') {                // rows cyclic, cols cyclic closure straight
    const S=states(n,true), T=transfer(S,n,true);
    return trace(matpow(T,n));
  }
  if (topology==='mobius') {               // rows linear, cols closure flipped
    const S=states(n,false), T=transfer(S,n,false), F=transferFlip(S,n,false);
    return trace(matmul(matpow(T,n-1), F));
  }
  if (topology==='klein') {                // sweep rows: cols cyclic, closure flipped
    const S=states(n,true), T=transfer(S,n,true), F=transferFlip(S,n,true);
    return trace(matmul(matpow(T,n-1), F));
  }
  throw new Error('unknown '+topology);
}
// n=1 fixups (matpow with p=0)
function kingTotalSafe(topology,n){
  if(n===1){ // 1x1 board: empty or one king = 2, on every surface
    return 2n;
  }
  return kingTotal(topology,n);
}

export { kingTotalSafe as kingTotal, states, transfer, transferFlip, compat, reverseBits };

if (import.meta.url === `file://${process.argv[1]}`) {
  const [, , topo='torus', nlo='1', nhi='8'] = process.argv;
  const out=[];
  for(let n=Number(nlo);n<=Number(nhi);n++) out.push(kingTotalSafe(topo,Number(n)).toString());
  console.log(topo, out.join(', '));
}
