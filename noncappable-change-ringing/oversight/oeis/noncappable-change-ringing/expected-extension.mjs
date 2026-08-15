// Expected extension values copied 2026-07-23 from finished run outputs.
// n=5 L=19: runs/n5-L20.out line 20, runs/n5-L21.out line 20
// n=5 L=20: runs/n5-L20.out line 21, runs/n5-L21.out line 21
// n=5 L=21: runs/n5-L21.out line 22
// n=6 L=14: runs/n6-L14.out line 15, runs/n6-L15.out line 15
// n=6 L=15: runs/n6-L15.out line 16
// n=7 L=12: runs/n7-L12.out line 13, runs/n7-L13.out line 13
// n=7 L=13: runs/n7-L13.out line 14

const SOURCES = {
  5: [
    [19, '12093668306934', '12093668306934'],
    [20, '60475934478010', '60475934478010'],
    [21, '300947562874178'],
  ],
  6: [
    [14, '15312433033758', '15312433033758'],
    [15, '153367319202102'],
  ],
  7: [
    [12, '82259765534440', '82259765534440'],
    [13, '1488223219474714'],
  ],
};

function buildExpectedExtension() {
  const table = {};
  for (const [n, rows] of Object.entries(SOURCES)) {
    table[n] = new Map();
    for (const [L, first, ...duplicates] of rows) {
      for (const duplicate of duplicates) {
        if (duplicate !== first) {
          throw new Error(`Conflicting finished-run values for n=${n} L=${L}: ${first} != ${duplicate}`);
        }
      }
      table[n].set(L, BigInt(first));
    }
  }
  return table;
}

const EXPECTED_EXTENSION = buildExpectedExtension();

export { EXPECTED_EXTENSION };
