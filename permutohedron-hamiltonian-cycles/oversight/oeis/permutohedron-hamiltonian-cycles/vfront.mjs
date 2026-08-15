import fs from 'fs';
const lines=fs.readFileSync(process.argv[2],'utf8').trim().split('\n');
const N=lines.length; const adj=lines.map(l=>l.trim()?l.trim().split(/\s+/).map(x=>+x-1):[]);
// cut after position p (vertices 0..p on left): count left vertices with a neighbor at pos> p
let mx=0;
for(let p=0;p<N-1;p++){
  let cnt=0;
  for(let v=0;v<=p;v++){ if(adj[v].some(u=>u>p)){cnt++;} }
  if(cnt>mx)mx=cnt;
}
console.log(`${process.argv[2]}: cut-frontier=${mx}  (N=${N})`);
