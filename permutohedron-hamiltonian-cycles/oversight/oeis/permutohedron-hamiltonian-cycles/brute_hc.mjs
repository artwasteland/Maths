// brute-force count of undirected Hamiltonian cycles of a graph given as a .dat
// adjacency list (1-indexed). For small graphs only. Independent of TdZdd.
import fs from 'fs';
const lines=fs.readFileSync(process.argv[2],'utf8').trim().split('\n');
const N=lines.length;
const adj=lines.map(l=>l.trim()?l.trim().split(/\s+/).map(x=>+x-1):[]);
const A=adj.map(a=>{const s=new Set(a);return s;});
let count=0; const seen=new Uint8Array(N); seen[0]=1;
(function dfs(v,d){ if(d===N){ if(A[v].has(0)) count++; return; } for(const w of adj[v]) if(!seen[w]){ seen[w]=1; dfs(w,d+1); seen[w]=0; } })(0,1);
console.log(count/2);
