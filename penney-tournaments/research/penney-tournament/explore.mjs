// Exploration: the Penney's-game dominance tournament at length k.
// Reuse Conway's leading-number formula (validated 3 ways in research/penneys-game).
const g = (a,b)=> (b? g(b,a%b) : a<0n?-a:a);
class Q{constructor(n,d=1n){if(d<0n){n=-n;d=-d;}const k=g(n<0n?-n:n,d)||1n;this.n=n/k;this.d=d/k;}
  cmp(o){return this.n*o.d - o.n*this.d;} // sign of (this - o), as BigInt
  eqv(o){return this.n===o.n&&this.d===o.d;} get s(){return `${this.n}/${this.d}`;}}
const corr=(X,Y)=>{const L=X.length;let t=0n;for(let k=1;k<=L;k++) if(X.slice(-k)===Y.slice(0,k)) t+=2n**BigInt(k-1);return t;};
// P(A appears before B): Conway. odds(A first):(B first) = (BB-BA):(AA-AB)
function pAfirst(A,B){const AA=corr(A,A),AB=corr(A,B),BA=corr(B,A),BB=corr(B,B);
  const a=BB-BA, b=AA-AB; return new Q(a, a+b);} // P(A first)
const HALF=new Q(1n,2n);
const seqsOf=(k)=>Array.from({length:1<<k},(_,i)=>i.toString(2).padStart(k,'0').replace(/0/g,'H').replace(/1/g,'T'));

function analyze(k){
  const S=seqsOf(k), n=S.length;
  // relation matrix: rel[i][j] = +1 if i beats j, -1 if loses, 0 tie
  const rel=Array.from({length:n},()=>new Array(n).fill(0));
  const probSet=new Set();
  let ties=0;
  for(let i=0;i<n;i++)for(let j=0;j<n;j++){ if(i===j)continue;
    const p=pAfirst(S[i],S[j]); probSet.add(p.s);
    const c=p.cmp(HALF); rel[i][j]= c>0n?1:(c<0n?-1:0);
    if(c===0n && i<j) ties++;
  }
  const out=rel.map(r=>r.filter(x=>x===1).length);
  const maxout=Math.max(...out);
  const nMax=out.filter(x=>x===maxout).length;
  const kings=out.filter((o,i)=>rel[i].every((x,j)=>i===j||x>=0)).length; // beats-or-ties everyone... in-degree among losses 0
  // 3-cycles: triples with all three edges decided forming a directed cycle
  let cyc3=0, transTri=0, decidedTri=0;
  for(let a=0;a<n;a++)for(let b=a+1;b<n;b++)for(let c=b+1;c<n;c++){
    const ab=rel[a][b],bc=rel[b][c],ac=rel[a][c];
    if(ab===0||bc===0||ac===0) continue; decidedTri++;
    // cyclic iff each node has out-degree 1 within the triple
    const od=[ (ab===1?1:0)+(ac===1?1:0), (ab===-1?1:0)+(bc===1?1:0), (ac===-1?1:0)+(bc===-1?1:0) ];
    if(od[0]===1&&od[1]===1&&od[2]===1) cyc3++; else transTri++;
  }
  return {k,n,ties,maxout,nMax,kings,cyc3,transTri,decidedTri,distinctP:probSet.size};
}

const rows=[];
for(let k=1;k<=9;k++) rows.push(analyze(k));
console.log('k\tn\tties\tmaxout\tnMax\tcyc3\ttransTri\tdistinctP');
for(const r of rows) console.log(`${r.k}\t${r.n}\t${r.ties}\t${r.maxout}\t${r.nMax}\t${r.cyc3}\t${r.transTri}\t${r.distinctP}`);
console.log('\nSequences (k=2..9):');
console.log('ties:     ', rows.slice(1).map(r=>r.ties).join(', '));
console.log('cyc3:     ', rows.slice(1).map(r=>r.cyc3).join(', '));
console.log('transTri: ', rows.slice(1).map(r=>r.transTri).join(', '));
console.log('maxout:   ', rows.slice(1).map(r=>r.maxout).join(', '));
console.log('nMax:     ', rows.slice(1).map(r=>r.nMax).join(', '));
console.log('distinctP:', rows.slice(1).map(r=>r.distinctP).join(', '));
