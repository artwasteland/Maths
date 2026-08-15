// Certification (1): the leaper attack model, fed the eight UNIT leapers, must
// reproduce the already-validated nonorientable-queens KING attack graph
// cell-for-cell on all four topologies (the one move where the universal-cover
// definition and the single-step ray-tracer must coincide).
import { attackGraph as leaperGraph } from './engine.mjs';
import { attackGraph as queensGraph } from '../nonorientable-queens/engine.mjs';
const KING = [[1,0],[-1,0],[0,1],[0,-1],[1,1],[1,-1],[-1,1],[-1,-1]];
let ok = true, checks = 0;
for (const topo of ['flat','torus','mobius','klein']) {
  for (let n = 1; n <= 8; n++) {
    const A = leaperGraph(topo, n, KING);
    const B = queensGraph(topo, n, 'king');
    for (let v = 0; v < n*n; v++) {
      checks++;
      if (A[v] !== B[v]) { ok = false; console.log(`MISMATCH ${topo} n=${n} cell ${v}`); }
    }
  }
}
console.log(ok ? `PASS — all king attack graphs identical (${checks} cells; flat/torus/mobius/klein, n=1..8)` : 'FAILED');
process.exit(ok ? 0 : 1);
