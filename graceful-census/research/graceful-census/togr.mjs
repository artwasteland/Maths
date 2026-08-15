import { FAMILIES } from './graceful.mjs';
const [,, fam, n] = process.argv;
const g = FAMILIES[fam](+n);
let out = g.v + ' ' + g.e.length + '\n' + g.e.map(([a,b])=>a+' '+b).join('\n') + '\n';
process.stdout.write(out);
