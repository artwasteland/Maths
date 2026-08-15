import { FF, T } from './ff.mjs';
import { writeFileSync } from 'node:fs';
const rows={};
const rowspec={5:44,6:38,7:32,8:26,9:24,10:22,11:20,12:18};
for(const m in rowspec){ const N=rowspec[m]; rows[m]=[]; for(let n=1;n<=N;n++) rows[m].push(FF(+m,n).toString()); }
const AR=16; const array=[];
for(let m=1;m<=AR;m++){ const r=[]; for(let n=1;n<=AR;n++) r.push(FF(m,n).toString()); array.push(r); }
const anti=[]; for(let s=2;s<=2*AR;s++) for(let n=1;n<s;n++){ const m=s-n; if(m>=1&&m<=AR&&n<=AR) anti.push(FF(m,n).toString()); }
// A124997 diagonal: validated constants (each independently reproduced by this engine; see verify.mjs).
const diag={2:'0',4:'0',6:'0',8:'25506',10:'1759280998',12:'854818404562894',
  14:'3588226034666378581610',16:'138311081613064367684548901556',
  18:'50272239752141442901464758051467073726',
  20:'174927321882862834702052846250836696969014873138',
  22:'5889117928937174007411459040006660524033737246962655301188',
  24:'1934659183999048207708201264307215891852758175871534722685882120022644'};
const out={ generated:'2026-07-11', rows, rowspec, array, arraySize:AR, antidiagonals:anti, diagonal:diag };
writeFileSync('data.json', JSON.stringify(out,null,1));
console.log('5x(2n):',rows[5].filter(x=>x!=='0').slice(0,8).join(','));
console.log('6xn (n>=5):',rows[6].slice(4,15).join(','));
console.log('7x(2n):',rows[7].filter(x=>x!=='0').slice(0,7).join(','));
console.log('8xn (n>=5):',rows[8].slice(4,13).join(','));
console.log('done');
