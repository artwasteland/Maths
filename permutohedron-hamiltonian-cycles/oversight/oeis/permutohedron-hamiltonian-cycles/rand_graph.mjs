// random connected graph on V vertices, ~E edges, emit 1-indexed adjacency list .dat
const V=+process.argv[2], E=+process.argv[3], seed=+(process.argv[4]||1);
let s=seed>>>0||1; const rnd=()=>{s^=s<<13;s^=s>>>17;s^=s<<5;return ((s>>>0)/4294967296);};
const adj=Array.from({length:V},()=>new Set());
const perm=[...Array(V).keys()]; for(let i=V-1;i>0;i--){const j=Math.floor(rnd()*(i+1));[perm[i],perm[j]]=[perm[j],perm[i]];}
for(let i=1;i<V;i++){const j=Math.floor(rnd()*i); const a=perm[i],b=perm[j]; adj[a].add(b);adj[b].add(a);} // spanning tree => connected
let ec=V-1; let guard=0;
while(ec<E && guard++<E*50){ const a=Math.floor(rnd()*V),b=Math.floor(rnd()*V); if(a!==b&&!adj[a].has(b)){adj[a].add(b);adj[b].add(a);ec++;} }
const out=[]; for(let i=0;i<V;i++) out.push([...adj[i]].sort((x,y)=>x-y).map(j=>j+1).join(' '));
process.stdout.write(out.join('\n')+'\n');
