// Exact rational E[p_hat](n) for k=1 (streak-selection bias, fair coin),
// by brute enumeration with BigInt. E = (sum over defined seqs of h/o)/(2^n-2).
function gcd(a,b){a=a<0n?-a:a;b=b<0n?-b:b;while(b){[a,b]=[b,a%b];}return a;}
function lcm(a,b){return a/gcd(a,b)*b;}
function exactRational(n){
  // common denom L = lcm(1..n-1)
  let L=1n; for(let i=1n;i<=BigInt(n-1);i++) L=lcm(L,i);
  let sumNum=0n; // in units of 1/L
  let defined=0n;
  const total=1<<n;
  for(let mask=0; mask<total; mask++){
    let o=0,h=0;
    for(let t=1;t<n;t++){ if((mask>>(t-1))&1){ o++; if((mask>>t)&1) h++; } }
    if(o>0){ sumNum += BigInt(h)*(L/BigInt(o)); defined++; }
  }
  // E = sumNum/L / defined = sumNum / (L*defined)
  let num=sumNum, den=L*defined;
  const g=gcd(num,den); num/=g; den/=g;
  return {n, num, den, dec: Number(num)/Number(den)};
}
const nums=[], dens=[];
for(let n=2;n<=22;n++){
  const r=exactRational(n);
  nums.push(r.num.toString()); dens.push(r.den.toString());
  if(n<=8||n>=20) console.log(`n=${n}: ${r.num}/${r.den}  = ${r.dec.toFixed(6)}`);
}
console.log("NUMERATORS:", nums.join(','));
console.log("DENOMINATORS:", dens.join(','));
