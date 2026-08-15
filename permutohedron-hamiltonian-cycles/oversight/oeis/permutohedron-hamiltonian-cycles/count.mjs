// Count UNDIRECTED Hamiltonian cycles in the n-permutohedron graph (Cayley
// graph of S_n, single adjacent transpositions). Correct pruning:
//  (1) every unvisited vertex must keep remaining-degree >= 2 in the subgraph
//      induced on (unvisited + head + start);
//  (2) (unvisited + head + start) must stay connected.
// Validated: n=3 -> 1, n=4 -> 44 (truncated octahedron, OEIS A343433).
function allPerms(n){const r=[];const a=[...Array(n).keys()];const rec=k=>{if(k===n){r.push(a.slice());return;}for(let i=k;i<n;i++){[a[k],a[i]]=[a[i],a[k]];rec(k+1);[a[k],a[i]]=[a[i],a[k]];}};rec(0);r.sort((x,y)=>x.join('')<y.join('')?-1:1);return r;}
function build(n){const ps=allPerms(n);const idx=new Map();ps.forEach((p,i)=>idx.set(p.join(','),i));const N=ps.length;const adj=Array.from({length:N},()=>[]);for(let i=0;i<N;i++){const p=ps[i];for(let s=0;s<n-1;s++){const q=p.slice();[q[s],q[s+1]]=[q[s+1],q[s]];const j=idx.get(q.join(','));if(j!==undefined&&j!==i)adj[i].push(j);}}for(let i=0;i<N;i++)adj[i]=[...new Set(adj[i])].sort((a,b)=>a-b);return {N,adj};}

function countHam(N, adj, report){
  const M=Array.from({length:N},()=>new Uint8Array(N));
  for(let i=0;i<N;i++)for(const j of adj[i])M[i][j]=1;
  const visited=new Uint8Array(N);
  const avail=new Int32Array(N); for(let i=0;i<N;i++)avail[i]=adj[i].length;
  const start=0; let count=0n;
  const stack=new Int32Array(N); const seen=new Uint8Array(N);
  function connectedAllReached(head){
    seen.fill(0); let sp=0; stack[sp++]=head; seen[head]=1;
    while(sp>0){const v=stack[--sp];for(const w of adj[v]){if((visited[w]===0||w===start)&&seen[w]===0){seen[w]=1;stack[sp++]=w;}}}
    for(let u=0;u<N;u++){ if((visited[u]===0||u===start)&&seen[u]===0) return false; }
    return true;
  }
  function mark(v){visited[v]=1;for(const w of adj[v])avail[w]--;}
  function unmark(v){visited[v]=0;for(const w of adj[v])avail[w]++;}
  function degOK(head){
    // every unvisited u: avail[u] + (u~head) + (u~start) >= 2
    for(let u=0;u<N;u++){ if(visited[u]) continue;
      let d=avail[u]+M[u][head]+(start!==head?M[u][start]:0);
      if(d<2) return false; }
    return true;
  }
  function dfs(head, depth){
    if(depth===N){ if(M[head][start]) count++; return; }
    for(const w of adj[head]){
      if(visited[w]) continue;
      mark(w);
      if(avail[start]>0 || depth+1===N){           // start still closable
        if(degOK(w) && connectedAllReached(w)) dfs(w, depth+1);
      }
      unmark(w);
    }
  }
  mark(start);
  const firsts=adj[start];
  for(let fi=0; fi<firsts.length; fi++){
    const w=firsts[fi]; mark(w); dfs(w,2); unmark(w);
    if(report) console.error(`  branch ${fi+1}/${firsts.length} done, cumulative directed=${count} (${count/2n} undirected so far)  t=${process.uptime().toFixed(0)}s`);
  }
  return count/2n;
}
const n=parseInt(process.argv[2]||"4"); const report=process.argv[3]==="1";
const t0=Date.now(); const {N,adj}=build(n);
console.log(`n=${n}: V=${N} degree=${adj[0].length}`);
const c=countHam(N,adj,report);
console.log(`n=${n}: UNDIRECTED Hamiltonian cycles = ${c}  (${((Date.now()-t0)/1000).toFixed(1)}s)`);
