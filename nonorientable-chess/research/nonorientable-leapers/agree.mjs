import { attackGraph, countPermutations, countPermutationsAlt, leaperVectors, LEAPERS } from './engine.mjs';
let ok=true;
for (const topo of ['flat','torus','mobius','klein'])
  for (const L of Object.keys(LEAPERS)) {
    const [a,b]=LEAPERS[L]; const V=leaperVectors(a,b);
    for (let n=1;n<=8;n++){
      const g=attackGraph(topo,n,V);
      const x=countPermutations(g,n), y=countPermutationsAlt(topo,n,V);
      if(x!==y){ok=false;console.log(`DISAGREE ${topo} ${L} n=${n}: ${x} vs ${y}`);}
    }
  }
console.log(ok?'PASS — two enumerators agree (flat/torus/mobius/klein × 4 leapers, n=1..8)':'FAILED');
