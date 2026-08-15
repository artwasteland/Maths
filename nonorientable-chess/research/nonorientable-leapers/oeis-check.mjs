// OEIS absence check for the leaper sequences. For each, query a distinctive
// interior window (skip the trivial leading 1) and the tail; report any A-number.
// Claim made is only "not found in OEIS as of the run date".
import { execSync } from 'node:child_process';

const SEQ = {
  'mobius knight':  [1,2,0,0,6,22,200,1266,11048,93510,956498],
  'mobius camel':   [1,0,6,2,2,64,150,1454,9114,97966,848378],
  'mobius zebra':   [1,2,6,4,6,32,270,1226,12102,108926,1129588],
  'mobius giraffe': [1,2,0,24,6,24,184,1008,12072,113896,1145510],
  'klein knight':   [1,0,0,0,4,4,136,628,6740,53280,576360],
  'klein camel':    [1,0,4,0,2,64,54,612,4100,45992,403342],
  'klein zebra':    [1,0,2,0,0,8,28,248,3588,31508,409334],
  'klein giraffe':  [1,0,0,16,0,0,56,864,4348,34872,414950],
  // flat leaper permutation counts — bonus: may be catalogued (would be an extra anchor)
  'flat knight':    [1,2,2,8,20,94,438,2766,19480,163058,1546726],
  'flat camel':     [1,2,6,8,24,126,524,3072,22854,189646,1827114],
  'flat zebra':     [1,2,6,12,36,174,708,4334,31424,263732,2503296],
  'flat giraffe':   [1,2,6,24,48,182,868,5752,37156,296944,2738820],
};

function sleep(ms) { execSync(`sleep ${ms / 1000}`); }

// OEIS fmt=json returns `null` when nothing matches, or a bare JSON ARRAY of
// result objects when something does. Handle both.
function query(terms) {
  const q = terms.join(',');
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const out = execSync(`curl -sS --max-time 40 "https://oeis.org/search?q=${q}&fmt=json"`, { encoding: 'utf8' }).trim();
      if (out === 'null' || out === '') return { hits: 0, ids: [] };
      const j = JSON.parse(out);
      const arr = Array.isArray(j) ? j : (j.results || []);
      const ids = arr.map(r => 'A' + String(r.number).padStart(6, '0'));
      return { hits: arr.length, ids };
    } catch (e) { sleep(4000); if (attempt === 2) return { error: String(e).slice(0, 100) }; }
  }
}

// Positive control: this MUST be found, else the checker/egress is broken.
const ctrl = query([1, 2, 6, 24, 120, 720, 5040]);
console.log(`CONTROL factorials -> ${ctrl.hits ? 'FOUND ' + ctrl.ids[0] : 'NOT FOUND (checker broken!)'}`);
sleep(2500);

for (const [name, seq] of Object.entries(SEQ)) {
  const w1 = seq.slice(4, 11);   // distinctive interior window
  const w2 = seq.slice(-6);      // tail window
  const r1 = query(w1); sleep(2500);
  const r2 = query(w2); sleep(2500);
  const found = [...new Set([...(r1.ids || []), ...(r2.ids || [])])];
  const verdict = found.length ? `FOUND ${found.join(',')}` : 'absent';
  console.log(`${name.padEnd(16)} ${verdict}   [w1 ${JSON.stringify(w1)} -> ${r1.hits ?? r1.error}] [tail -> ${r2.hits ?? r2.error}]`);
}
