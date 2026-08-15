// Emit the n-permutohedron (bubble-sort) graph as a 1-indexed adjacency list
// (the format TdZdd's ddpaths reads): line i lists the neighbours of vertex i.
// Vertex order controls the frontier size; we support a few orderings.
//   node gen_adj.mjs <n> [order]   order = lex | bfs | gray
function allPerms(n){const r=[];const a=[...Array(n).keys()];const rec=k=>{if(k===n){r.push(a.slice());return;}for(let i=k;i<n;i++){[a[k],a[i]]=[a[i],a[k]];rec(k+1);[a[k],a[i]]=[a[i],a[k]];}};rec(0);return r;}
const n=parseInt(process.argv[2]||"4");
const order=process.argv[3]||"lex";
let ps=allPerms(n);
if(order==="lex") ps.sort((x,y)=>x.join('')<y.join('')?-1:1);
const key=p=>p.join(',');
let idx=new Map(); ps.forEach((p,i)=>idx.set(key(p),i));
const N=ps.length;
const adj=Array.from({length:N},()=>new Set());
for(let i=0;i<N;i++){const p=ps[i];for(let s=0;s<n-1;s++){const q=p.slice();[q[s],q[s+1]]=[q[s+1],q[s]];const j=idx.get(key(q));if(j!==undefined&&j!==i){adj[i].add(j);adj[j].add(i);}}}
// optional reorder to shrink bandwidth/frontier
function reindex(ordIdx){
  const pos=new Array(N); ordIdx.forEach((v,i)=>pos[v]=i);
  const newadj=Array.from({length:N},()=>new Set());
  for(let v=0;v<N;v++) for(const w of adj[v]) newadj[pos[v]].add(pos[w]);
  for(let i=0;i<N;i++){adj[i]=newadj[i];}
}
function cuthillMcKee(reverse){
  // start from a low-degree vertex; BFS visiting neighbours in increasing degree
  const deg=adj.map(s=>s.size);
  let start=0; for(let i=1;i<N;i++) if(deg[i]<deg[start]) start=i;
  const seen=new Array(N).fill(false); const ord=[]; const q=[start]; seen[start]=true;
  while(q.length){ const v=q.shift(); ord.push(v);
    const nb=[...adj[v]].filter(w=>!seen[w]).sort((a,b)=>deg[a]-deg[b]||a-b);
    for(const w of nb){ seen[w]=true; q.push(w); } }
  for(let i=0;i<N;i++) if(!seen[i]) ord.push(i);
  if(reverse) ord.reverse();
  return ord;
}
if(order==="bfs"){
  const seen=new Array(N).fill(false); const ordIdx=[]; const queue=[0]; seen[0]=true;
  while(queue.length){const v=queue.shift(); ordIdx.push(v); const nb=[...adj[v]].sort((a,b)=>a-b); for(const w of nb) if(!seen[w]){seen[w]=true;queue.push(w);}}
  reindex(ordIdx);
}
if(order==="cm")  reindex(cuthillMcKee(false));
if(order==="rcm") reindex(cuthillMcKee(true));
if(order==="spectral"){
  // Fiedler vector via power iteration on (deg-max - L); order by its value.
  const deg=adj.map(s=>s.size);
  let x=Array.from({length:N},()=>Math.random()-0.5);
  const dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
  const sub=(a,m)=>a.map(v=>v-m);
  const norm=a=>{const n=Math.sqrt(dot(a,a))||1;return a.map(v=>v/n);};
  // shift: M = c*I - L, L = D - A ; iterate, deflate constant vector (eigvec of L for 0)
  const c=10;
  for(let it=0;it<2000;it++){
    let y=new Array(N).fill(0);
    for(let v=0;v<N;v++){ let lap=deg[v]*x[v]; for(const w of adj[v]) lap-=x[w]; y[v]=c*x[v]-lap; }
    const mean=y.reduce((s,v)=>s+v,0)/N; y=sub(y,mean); x=norm(y);
  }
  const ord=[...Array(N).keys()].sort((a,b)=>x[a]-x[b]);
  reindex(ord);
}
let out=[];
for(let i=0;i<N;i++){ out.push([...adj[i]].sort((a,b)=>a-b).map(j=>j+1).join(' ')); }
process.stdout.write(out.join('\n')+'\n');
process.stderr.write(`n=${n} order=${order} V=${N} E=${out.reduce((s,l)=>s+l.split(' ').filter(x=>x).length,0)/2}\n`);
