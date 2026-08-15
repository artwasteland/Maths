import { tournament, pAfirst_conway, pAfirst_markov } from './engine.mjs';

// girth of the strict dominance digraph: length of the shortest directed cycle.
// edge i->j iff pattern i strictly beats pattern j (rel = +1). Ties are non-edges.
// BFS from each source; first return to source is the shortest cycle through it.
export function girth(k, pfn = pAfirst_conway){
  const t = tournament(k, pfn);
  const { n, rel } = t;
  const adj = Array.from({length:n}, (_,i)=>{ const o=[]; for(let j=0;j<n;j++) if(rel[i][j]===1) o.push(j); return o; });
  let best = Infinity, witness=null;
  for(let s=0;s<n;s++){
    const dist=new Array(n).fill(-1), par=new Array(n).fill(-1);
    const q=[s]; dist[s]=0;
    for(let qi=0; qi<q.length; qi++){
      const u=q[qi];
      if(dist[u]+1>=best) continue;
      for(const v of adj[u]){
        if(v===s){ const len=dist[u]+1; if(len<best){ best=len; const path=[u]; let x=u; while(x!==s){x=par[x]; path.push(x);} witness=path.reverse().map(i=>t.S[i]); } }
        else if(dist[v]===-1){ dist[v]=dist[u]+1; par[v]=u; q.push(v); }
      }
    }
  }
  return {k, n, girth: best===Infinity?null:best, witness};
}

if(import.meta.url === `file://${process.argv[1]}`){
  for(let k=1;k<=9;k++){
    const r=girth(k);
    console.log(`k=${k}\tn=${r.n}\tgirth=${r.girth}\t${r.witness?('cycle: '+r.witness.join(' > ')+' > '+r.witness[0]):''}`);
  }
}
