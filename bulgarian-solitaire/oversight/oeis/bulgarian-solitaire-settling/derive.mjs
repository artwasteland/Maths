// ⚠ THIS SCRIPT OVERWRITES THE b-FILES IN THIS DIRECTORY.
// It regenerates them from a range it chooses by default, which may be
// SHORTER than what is published here. Copy the directory before running
// it, or pass an explicit range. Reading the numbers back out is what the
// verifier in ../../../research/ is for; this is the generator, not the check.
// Standalone derivation of the Bulgarian-solitaire total settling time S(n).
// S(n) = sum over all partitions of n of the number of Bulgarian-solitaire moves
// that arrangement needs to FIRST become periodic (reach its eventual cycle).
// Reproducible from scratch; writes b-file.txt. Calibrated in research/.../verify.mjs.
import { writeFileSync } from 'fs';
function partitions(n){const r=[],c=[];(function go(rem,mx){if(rem===0){r.push(c.slice());return;}for(let k=Math.min(rem,mx);k>=1;k--){c.push(k);go(rem-k,k);c.pop();}})(n,n);return r;}
function move(p){const piles=p.length,np=[];for(const x of p)if(x-1>0)np.push(x-1);np.push(piles);np.sort((a,b)=>b-a);return np;}
function S(n){
  const parts=partitions(n),N=parts.length,idx=new Map();
  parts.forEach((p,i)=>idx.set(p.join(','),i));
  const next=parts.map(p=>idx.get(move(p).join(',')));
  const stt=new Uint8Array(N),cyc=new Uint8Array(N);
  for(let s=0;s<N;s++){if(stt[s])continue;const pa=[];let u=s;while(stt[u]===0){stt[u]=1;pa.push(u);u=next[u];}if(stt[u]===1){let v=u;do{cyc[v]=1;v=next[v];}while(v!==u);}for(const w of pa)stt[w]=2;}
  const rev=Array.from({length:N},()=>[]);next.forEach((j,i)=>rev[j].push(i));
  const d=new Int32Array(N).fill(-1),q=[];for(let i=0;i<N;i++)if(cyc[i]){d[i]=0;q.push(i);}
  for(let h=0;h<q.length;h++){const u=q[h];for(const w of rev[u])if(d[w]<0){d[w]=d[u]+1;q.push(w);}}
  let s=0;for(let i=0;i<N;i++)s+=d[i];return s;
}
const NMAX=+process.argv[2]||55;
const vals=[];for(let n=1;n<=NMAX;n++)vals.push(S(n));
writeFileSync(new URL('./b-file.txt',import.meta.url),vals.map((v,i)=>`${i+1} ${v}`).join('\n')+'\n');
console.log('S(n), n=1..'+NMAX+':');
console.log(vals.join(','));
