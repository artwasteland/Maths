
## 3. The run and the agreement table

`replay.py replay --plan-file plan-main.json --workers 4 --tag main` on liam-desktop, started 2026-09-05T13:24:19Z, finished 2026-09-05T14:14:29Z, wall 3010 s (50.2 min) with 4 worker processes under `nice -n 10`; enum2 CPU 12036 s summed over units.

Shards replayed: 92 of 92 (6 whole, 86 sub-ranges); identical: 92 of 92; all identical: **True**. Parent records replayed: 7503 (of 815,215 in the two transitions, 0.92%); of these 6177 pass the minimum-degree guard (of udenum's 636,488 processed parents, 0.97%). udenum children in the replayed ranges: 57355 (of 5,128,203 in the two transitions, 1.12%); enum2 distinct children: 57355; enum2 raw constructions exceeding distinct (Aut(H)-equivalent neighbourhoods, removed by the set): 4326.

Vacuous shards (0 children on both sides, counted as identical but proving only that both guards skip the same parents): 13: 11-18-0-10000 [9497,9537), 11-19-0-10000 [3736,3776), 12-20-0-10000 [3392,3432), 12-24-0-6127 [3116,3266), 12-20-10000-20000 [12080,12120), 12-20-50000-60000 [50636,50676), 12-21-50000-60000 [50641,50681), 12-20-60000-70000 [60096,60136), 12-20-80000-90000 [89674,89714), 12-21-80000-90000 [89047,89087), 12-21-170000-180000 [178540,178580), 12-21-180000-190000 [183355,183395), 12-21-190000-200000 [198614,198654).

Every shard output file's sha256 matched its manifest: True; every shard file's line count matched the manifest's `children_written`: True; duplicate lines inside udenum blocks: 0.

Guard consistency (independent of the replay): `processed.py` re-expresses the AMP minimum-degree guard on the parent records alone; on the six whole shards its counts (11-21: 242, 11-22: 40, 11-23: 9, 12-25: 149, 12-26: 18, 12-27: 2) equal udenum's `parents_processed` in the shard stats exactly. Per cell for the planned ranges:

```
11-17 replayed 400 pass_guard 400
11-18 replayed 360 pass_guard 321
11-19 replayed 80 pass_guard 70
11-20 replayed 40 pass_guard 35
11-21 replayed 247 pass_guard 242
11-22 replayed 247 pass_guard 40
11-23 replayed 20 pass_guard 9
12-20 replayed 3080 pass_guard 2749
12-21 replayed 2060 pass_guard 1782
12-22 replayed 360 pass_guard 320
12-23 replayed 40 pass_guard 40
12-24 replayed 150 pass_guard 0
12-25 replayed 390 pass_guard 149
12-26 replayed 27 pass_guard 18
12-27 replayed 2 pass_guard 2
total replayed 7503 pass_guard 6177
```

### 3.1 Per-cell agreement table (the certificate item)

| cell | shards replayed / in cell | parent records replayed / in cell | d | udenum children | enum2 children | only udenum | only enum2 | identical |
|---|---:|---:|---|---:|---:|---:|---:|---|
| 11-17 | 4 / 4 | 400 / 31131 | 2 | 2559 | 2559 | 0 | 0 | yes |
| 11-18 | 5 / 5 | 360 / 43603 | 1,2,3 | 4596 | 4596 | 0 | 0 | yes |
| 11-19 | 2 / 2 | 80 / 18668 | 3 | 29 | 29 | 0 | 0 | yes |
| 11-20 | 1 / 1 | 40 / 3333 | 3 | 18 | 18 | 0 | 0 | yes |
| 11-21 | 1 / 1 | 247 / 247 | 1,3 | 363 | 363 | 0 | 0 | yes |
| 11-22 | 1 / 1 | 247 / 247 | 2,4 | 25 | 25 | 0 | 0 | yes |
| 11-23 | 1 / 1 | 20 / 20 | 3,4 | 2 | 2 | 0 | 0 | yes |
| 12-20 | 37 / 37 | 3080 / 369247 | 2,3 | 30631 | 30631 | 0 | 0 | yes |
| 12-21 | 28 / 28 | 2060 / 270819 | 1,2,3 | 18084 | 18084 | 0 | 0 | yes |
| 12-22 | 7 / 7 | 360 / 65229 | 1,2,3 | 921 | 921 | 0 | 0 | yes |
| 12-23 | 1 / 1 | 40 / 6125 | 3 | 39 | 39 | 0 | 0 | yes |
| 12-24 | 1 / 1 | 150 / 6127 | 4 | 0 | 0 | 0 | 0 | yes |
| 12-25 | 1 / 1 | 390 / 390 | 2,4 | 81 | 81 | 0 | 0 | yes |
| 12-26 | 1 / 1 | 27 / 27 | 3,4 | 6 | 6 | 0 | 0 | yes |
| 12-27 | 1 / 1 | 2 / 2 | 4 | 1 | 1 | 0 | 0 | yes |
| **total** | **92 / 92** | **7503 / 815215** | | **57355** | **57355** | **0** | **0** | **yes** |

Per shard (range = parent-record indices replayed; whole = the entire shard; block = udenum output lines matched to those parents by parent recovery; rec = parents recovered to locate/verify the block):

| shard | range | whole | d | parents | udenum block | udenum children | enum2 raw | enum2 distinct | only udenum | only enum2 | rec | identical | enum2 cpu s |
|---|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|---:|
| 11-17-0-10000 | [9623,9663) | n | 2 | 40 | [6733,6790) of 7639 | 57 | 57 | 57 | 0 | 0 | 68 | yes | 6 |
| 11-17-10000-20000 | [14426,14546) | n | 2 | 120 | [12763,13209) of 44070 | 446 | 467 | 446 | 0 | 0 | 454 | yes | 20 |
| 11-17-20000-30000 | [21370,21490) | n | 2 | 120 | [6838,7268) of 91641 | 430 | 434 | 430 | 0 | 0 | 441 | yes | 18 |
| 11-17-30000-31131 | [30734,30854) | n | 2 | 120 | [14455,16081) of 19944 | 1626 | 1962 | 1626 | 0 | 0 | 1634 | yes | 21 |
| 11-18-0-10000 | [9497,9537) | n | 3 | 40 | [68,68) of 72 | 0 | 0 | 0 | 0 | 0 | 6 | yes | 19 |
| 11-18-10000-20000 | [18407,18447) | n | 3 | 40 | [639,653) of 819 | 14 | 14 | 14 | 0 | 0 | 23 | yes | 74 |
| 11-18-20000-30000 | [25154,25194) | n | 2,3 | 40 | [1451,1529) of 32249 | 78 | 124 | 78 | 0 | 0 | 88 | yes | 25 |
| 11-18-30000-40000 | [37798,37918) | n | 2 | 120 | [88861,91082) of 133823 | 2221 | 2595 | 2221 | 0 | 0 | 2235 | yes | 32 |
| 11-18-40000-43603 | [40431,40551) | n | 1,2 | 120 | [9034,11317) of 38990 | 2283 | 2831 | 2283 | 0 | 0 | 2294 | yes | 19 |
| 11-19-0-10000 | [3736,3776) | n | 3 | 40 | [116,116) of 1741 | 0 | 0 | 0 | 0 | 0 | 11 | yes | 107 |
| 11-19-10000-18668 | [10672,10712) | n | 3 | 40 | [330,359) of 57388 | 29 | 32 | 29 | 0 | 0 | 42 | yes | 140 |
| 11-20-0-3333 | [1221,1261) | n | 3 | 40 | [204,222) of 5737 | 18 | 21 | 18 | 0 | 0 | 28 | yes | 178 |
| 11-21-0-247 | [0,247) | y | 1,3 | 247 | [0,363) of 363 | 363 | 644 | 363 | 0 | 0 | 2 | yes | 1405 |
| 11-22-0-247 | [0,247) | y | 2,4 | 247 | [0,25) of 25 | 25 | 50 | 25 | 0 | 0 | 2 | yes | 415 |
| 11-23-0-20 | [0,20) | y | 3,4 | 20 | [0,2) of 2 | 2 | 3 | 2 | 0 | 0 | 2 | yes | 122 |
| 12-20-0-10000 | [3392,3432) | n | 3 | 40 | [1410,1410) of 1441 | 0 | 0 | 0 | 0 | 0 | 11 | yes | 0 |
| 12-20-10000-20000 | [12080,12120) | n | 3 | 40 | [9,9) of 286 | 0 | 0 | 0 | 0 | 0 | 9 | yes | 0 |
| 12-20-20000-30000 | [20933,20973) | n | 3 | 40 | [22,25) of 931 | 3 | 3 | 3 | 0 | 0 | 13 | yes | 28 |
| 12-20-30000-40000 | [39238,39278) | n | 3 | 40 | [1044,1046) of 1202 | 2 | 2 | 2 | 0 | 0 | 11 | yes | 38 |
| 12-20-40000-50000 | [43678,43718) | n | 3 | 40 | [1389,1408) of 2059 | 19 | 19 | 19 | 0 | 0 | 27 | yes | 121 |
| 12-20-50000-60000 | [50636,50676) | n | 3 | 40 | [5,5) of 341 | 0 | 0 | 0 | 0 | 0 | 8 | yes | 3 |
| 12-20-60000-70000 | [60096,60136) | n | 3 | 40 | [0,0) of 1694 | 0 | 0 | 0 | 0 | 0 | 11 | yes | 73 |
| 12-20-70000-80000 | [73572,73612) | n | 3 | 40 | [587,600) of 1637 | 13 | 17 | 13 | 0 | 0 | 22 | yes | 93 |
| 12-20-80000-90000 | [89674,89714) | n | 3 | 40 | [1297,1297) of 1303 | 0 | 0 | 0 | 0 | 0 | 10 | yes | 43 |
| 12-20-90000-100000 | [99528,99568) | n | 3 | 40 | [1702,1705) of 1843 | 3 | 3 | 3 | 0 | 0 | 13 | yes | 93 |
| 12-20-100000-110000 | [102698,102738) | n | 3 | 40 | [1151,1171) of 3471 | 20 | 20 | 20 | 0 | 0 | 29 | yes | 148 |
| 12-20-110000-120000 | [113468,113508) | n | 3 | 40 | [1082,1106) of 2270 | 24 | 28 | 24 | 0 | 0 | 34 | yes | 99 |
| 12-20-120000-130000 | [125427,125467) | n | 3 | 40 | [2147,2206) of 4167 | 59 | 59 | 59 | 0 | 0 | 70 | yes | 168 |
| 12-20-130000-140000 | [139480,139520) | n | 3 | 40 | [4191,4228) of 4481 | 37 | 42 | 37 | 0 | 0 | 47 | yes | 125 |
| 12-20-140000-150000 | [140699,140739) | n | 3 | 40 | [305,309) of 4628 | 4 | 4 | 4 | 0 | 0 | 14 | yes | 30 |
| 12-20-150000-160000 | [151595,151635) | n | 3 | 40 | [740,746) of 3901 | 6 | 6 | 6 | 0 | 0 | 16 | yes | 73 |
| 12-20-160000-170000 | [166485,166525) | n | 2 | 40 | [102016,102336) of 125192 | 320 | 369 | 320 | 0 | 0 | 333 | yes | 9 |
| 12-20-170000-180000 | [170796,170916) | n | 2 | 120 | [5388,6191) of 98129 | 803 | 820 | 803 | 0 | 0 | 813 | yes | 26 |
| 12-20-180000-190000 | [184784,184904) | n | 2 | 120 | [55601,56616) of 119768 | 1015 | 1034 | 1015 | 0 | 0 | 1027 | yes | 24 |
| 12-20-190000-200000 | [192023,192143) | n | 2 | 120 | [34166,35301) of 132942 | 1135 | 1159 | 1135 | 0 | 0 | 1148 | yes | 25 |
| 12-20-200000-210000 | [206916,207036) | n | 2 | 120 | [81014,82514) of 118877 | 1500 | 1525 | 1500 | 0 | 0 | 1512 | yes | 24 |
| 12-20-210000-220000 | [219636,219756) | n | 2 | 120 | [116388,117993) of 120644 | 1605 | 1819 | 1605 | 0 | 0 | 1619 | yes | 26 |
| 12-20-220000-230000 | [220505,220625) | n | 2 | 120 | [5616,6883) of 115666 | 1267 | 1355 | 1267 | 0 | 0 | 1279 | yes | 38 |
| 12-20-230000-240000 | [239266,239386) | n | 2 | 120 | [160441,162613) of 173156 | 2172 | 2317 | 2172 | 0 | 0 | 2183 | yes | 34 |
| 12-20-240000-250000 | [240617,240737) | n | 2 | 120 | [8141,9303) of 161102 | 1162 | 1168 | 1162 | 0 | 0 | 1176 | yes | 27 |
| 12-20-250000-260000 | [250788,250908) | n | 2 | 120 | [11727,13232) of 159429 | 1505 | 1577 | 1505 | 0 | 0 | 1518 | yes | 29 |
| 12-20-260000-270000 | [268680,268800) | n | 2 | 120 | [167099,169084) of 190071 | 1985 | 1991 | 1985 | 0 | 0 | 1997 | yes | 30 |
| 12-20-270000-280000 | [276372,276492) | n | 2 | 120 | [117764,119352) of 179911 | 1588 | 1699 | 1588 | 0 | 0 | 1599 | yes | 25 |
| 12-20-280000-290000 | [281715,281835) | n | 2 | 120 | [31071,33431) of 188873 | 2360 | 2383 | 2360 | 0 | 0 | 2370 | yes | 27 |
| 12-20-290000-300000 | [290875,290995) | n | 2 | 120 | [17192,19469) of 185005 | 2277 | 2306 | 2277 | 0 | 0 | 2290 | yes | 27 |
| 12-20-300000-310000 | [302975,303095) | n | 2 | 120 | [54620,56712) of 185803 | 2092 | 2109 | 2092 | 0 | 0 | 2102 | yes | 28 |
| 12-20-310000-320000 | [318401,318521) | n | 2 | 120 | [168669,171059) of 200231 | 2390 | 2396 | 2390 | 0 | 0 | 2402 | yes | 27 |
| 12-20-320000-330000 | [323309,323429) | n | 2 | 120 | [66073,68113) of 184921 | 2040 | 2049 | 2040 | 0 | 0 | 2055 | yes | 25 |
| 12-20-330000-340000 | [339670,339790) | n | 2 | 120 | [188631,190821) of 196038 | 2190 | 2304 | 2190 | 0 | 0 | 2201 | yes | 30 |
| 12-20-340000-350000 | [349098,349218) | n | 2 | 120 | [38381,38683) of 40451 | 302 | 307 | 302 | 0 | 0 | 313 | yes | 28 |
| 12-20-350000-360000 | [351532,351652) | n | 2 | 120 | [2749,3030) of 26130 | 281 | 281 | 281 | 0 | 0 | 293 | yes | 31 |
| 12-20-360000-369247 | [364433,364553) | n | 2 | 120 | [14959,15411) of 35020 | 452 | 477 | 452 | 0 | 0 | 462 | yes | 27 |
| 12-21-0-10000 | [6973,7013) | n | 3 | 40 | [29529,29530) of 29690 | 1 | 1 | 1 | 0 | 0 | 16 | yes | 81 |
| 12-21-10000-20000 | [19066,19106) | n | 3 | 40 | [782,788) of 892 | 6 | 6 | 6 | 0 | 0 | 13 | yes | 214 |
| 12-21-20000-30000 | [23335,23375) | n | 3 | 40 | [242,243) of 3473 | 1 | 1 | 1 | 0 | 0 | 13 | yes | 97 |
| 12-21-30000-40000 | [38414,38454) | n | 3 | 40 | [1818,1820) of 1976 | 2 | 2 | 2 | 0 | 0 | 12 | yes | 104 |
| 12-21-40000-50000 | [41077,41117) | n | 3 | 40 | [192,195) of 1028 | 3 | 3 | 3 | 0 | 0 | 12 | yes | 115 |
| 12-21-50000-60000 | [50641,50681) | n | 3 | 40 | [22,22) of 1221 | 0 | 0 | 0 | 0 | 0 | 10 | yes | 22 |
| 12-21-60000-70000 | [63764,63804) | n | 3 | 40 | [247,248) of 2995 | 1 | 1 | 1 | 0 | 0 | 12 | yes | 142 |
| 12-21-70000-80000 | [76651,76691) | n | 3 | 40 | [5069,5102) of 6127 | 33 | 36 | 33 | 0 | 0 | 43 | yes | 196 |
| 12-21-80000-90000 | [89047,89087) | n | 3 | 40 | [3549,3549) of 3747 | 0 | 0 | 0 | 0 | 0 | 12 | yes | 161 |
| 12-21-90000-100000 | [95180,95220) | n | 3 | 40 | [2657,2695) of 5692 | 38 | 38 | 38 | 0 | 0 | 48 | yes | 204 |
| 12-21-100000-110000 | [105282,105322) | n | 3 | 40 | [5935,5957) of 8277 | 22 | 24 | 22 | 0 | 0 | 31 | yes | 207 |
| 12-21-110000-120000 | [118386,118426) | n | 3 | 40 | [6682,6752) of 8299 | 70 | 71 | 70 | 0 | 0 | 78 | yes | 211 |
| 12-21-120000-130000 | [126504,126544) | n | 3 | 40 | [6289,6306) of 9094 | 17 | 17 | 17 | 0 | 0 | 30 | yes | 132 |
| 12-21-130000-140000 | [130596,130636) | n | 3 | 40 | [217,253) of 6201 | 36 | 36 | 36 | 0 | 0 | 47 | yes | 147 |
| 12-21-140000-150000 | [142855,142895) | n | 3 | 40 | [1179,1189) of 13113 | 10 | 10 | 10 | 0 | 0 | 21 | yes | 151 |
| 12-21-150000-160000 | [151551,151591) | n | 3 | 40 | [2143,2181) of 16150 | 38 | 38 | 38 | 0 | 0 | 50 | yes | 143 |
| 12-21-160000-170000 | [164255,164295) | n | 3 | 40 | [6640,6650) of 10876 | 10 | 12 | 10 | 0 | 0 | 20 | yes | 138 |
| 12-21-170000-180000 | [178540,178580) | n | 3 | 40 | [14823,14823) of 14823 | 0 | 0 | 0 | 0 | 0 | 13 | yes | 0 |
| 12-21-180000-190000 | [183355,183395) | n | 3 | 40 | [0,0) of 0 | 0 | 0 | 0 | 0 | 0 | 0 | yes | 0 |
| 12-21-190000-200000 | [198614,198654) | n | 3 | 40 | [0,0) of 0 | 0 | 0 | 0 | 0 | 0 | 0 | yes | 0 |
| 12-21-200000-210000 | [208221,208261) | n | 2 | 40 | [87003,88613) of 157843 | 1610 | 1718 | 1610 | 0 | 0 | 1622 | yes | 14 |
| 12-21-210000-220000 | [214593,214713) | n | 2 | 120 | [169229,170375) of 240619 | 1146 | 1351 | 1146 | 0 | 0 | 1157 | yes | 35 |
| 12-21-220000-230000 | [228133,228253) | n | 2 | 120 | [138058,139950) of 174987 | 1892 | 1904 | 1892 | 0 | 0 | 1905 | yes | 41 |
| 12-21-230000-240000 | [232633,232753) | n | 2 | 120 | [50121,52207) of 190455 | 2086 | 2170 | 2086 | 0 | 0 | 2100 | yes | 39 |
| 12-21-240000-250000 | [247850,247970) | n | 2 | 120 | [154227,157067) of 202118 | 2840 | 2893 | 2840 | 0 | 0 | 2852 | yes | 37 |
| 12-21-250000-260000 | [257170,257290) | n | 2 | 120 | [152277,154393) of 215667 | 2116 | 2533 | 2116 | 0 | 0 | 2126 | yes | 38 |
| 12-21-260000-270000 | [269775,269895) | n | 1 | 120 | [130233,131486) of 132502 | 1253 | 1320 | 1253 | 0 | 0 | 1266 | yes | 0 |
| 12-21-270000-270819 | [270249,270749) | n | 1 | 500 | [2454,7307) of 7708 | 4853 | 5345 | 4853 | 0 | 0 | 4860 | yes | 2 |
| 12-22-0-10000 | [6474,6514) | n | 3 | 40 | [34881,35038) of 40932 | 157 | 160 | 157 | 0 | 0 | 167 | yes | 258 |
| 12-22-10000-20000 | [16252,16292) | n | 3 | 40 | [1816,1835) of 3397 | 19 | 19 | 19 | 0 | 0 | 29 | yes | 261 |
| 12-22-20000-30000 | [20444,20484) | n | 3 | 40 | [261,276) of 7279 | 15 | 15 | 15 | 0 | 0 | 25 | yes | 265 |
| 12-22-30000-40000 | [31308,31348) | n | 3 | 40 | [864,884) of 8655 | 20 | 21 | 20 | 0 | 0 | 30 | yes | 283 |
| 12-22-40000-50000 | [40339,40379) | n | 3 | 40 | [787,874) of 17753 | 87 | 88 | 87 | 0 | 0 | 97 | yes | 246 |
| 12-22-50000-60000 | [59090,59130) | n | 2,3 | 40 | [14907,14945) of 44672 | 38 | 38 | 38 | 0 | 0 | 51 | yes | 1 |
| 12-22-60000-65229 | [64775,64895) | n | 1,2 | 120 | [111357,111942) of 115022 | 585 | 732 | 585 | 0 | 0 | 599 | yes | 57 |
| 12-23-0-6125 | [3144,3184) | n | 3 | 40 | [6257,6296) of 16281 | 39 | 39 | 39 | 0 | 0 | 52 | yes | 381 |
| 12-24-0-6127 | [3116,3266) | n | 4 | 150 | [6,6) of 1034 | 0 | 0 | 0 | 0 | 0 | 10 | yes | 0 |
| 12-25-0-390 | [0,390) | y | 2,4 | 390 | [0,81) of 81 | 81 | 147 | 81 | 0 | 0 | 2 | yes | 2826 |
| 12-26-0-27 | [0,27) | y | 3,4 | 27 | [0,6) of 6 | 6 | 9 | 6 | 0 | 0 | 2 | yes | 417 |
| 12-27-0-2 | [0,2) | y | 4 | 2 | [0,1) of 1 | 1 | 1 | 1 | 0 | 0 | 2 | yes | 67 |

No differences.


## 4. The two controls, both red

**(a) Mutated parent record.** `replay.py control-a --ranges 12-20-200000-210000:200000:200030 --record 200010 --edge 0,1 --workers 2 --tag control-a`. Record 200010 of `_parents/12-20.g6` (`J??KaOeK]y?`, 11 vertices, 18 edges) had edge {0,1} flipped (added; raw `J_?KaOeK]y?`), the result re-canonicalised (`J@?J?qEoZy?`, 19 edges, so d becomes 1 for that record) and substituted before replaying parents [200000,200030) with (12,20). udenum block: 292 children; enum2: 301; only udenum: 2; only enum2: 11; identical: False -> RED as required (the 2 children of the original record are missing, 11 children of the mutated record are extra).

  only udenum: `K???IOaEKi|s K?_?GpCGp`zs`

  only enum2 (first 20): `K??HCcWPb@fk K??H_IPQbAfk K??P_IHQbAfk K??P_YGOjAfk K?C?H_KOr@vs K?C?H_KWMEfs K?C?H`DWKSfp K?GO@aEOqPfw K@??OWQWUHfs K@?HCCWPaBfk K@?KB?W@qDnc`

**(b) Forbidden graph dropped from a copy of the list.** `replay.py control-b --drop-index 1 --ranges 12-20-200000-210000:200000:200030,11-17-20000-30000:25000:25030 --workers 2 --tag control-b`. The copy `crosscheck/forbidden-73-drop1.json` (sha256 38ab9bcc08af7f27cc75e7ed50628d9d9b41c108b501392bfd3deee4e8c9ee89) is `data/forbidden-74.json` without index 1, the (5,6) graph K_{2,3} (edges [[0,3],[0,4],[3,1],[3,2],[4,1],[4,2]]); enum2's `PATTERNS` were rebuilt from it (`make_patterns`, 630 patterns instead of 635) and the same ranges replayed:

  - 12-20-200000-210000 [200000,200030): udenum 292, enum2 414, only enum2 122, only udenum 0, identical False; first extras: `K???G_JMNGw{ K???GodSdPxq K???GogH]dXp K???HGQE]P\w K???HGYA]_{Z K???HHOA[s{] K???HOopGvWx K???HPCKspxs`
  - 11-17-20000-30000 [25000,25030): udenum 155, enum2 217, only enum2 62, only udenum 0, identical False; first extras: `J??G_^_KmW_ J??GbAMKuW_ J??H_cLwFw? J?C?^?EK]H_ J?C?xJ?H]o_ J?GGGNOCvo_ J?GOGNOAvo_ J?HOOCP_~J?`

  Total extra children 184, missing 0, on 60 parents: RED as required, and in the right direction (a strict superset: removing a forbidden graph can only admit more neighbourhoods).

## 5. Exact commands and hashes

All from `research/unit-distance-22/enum2/crosscheck/` with `PY=<repo>/pyenv-maths/bin/python`:

```
$PY replay.py bench --parent-file <_parents/N-M.g6> --start A --end B --n N --m M      # Section 2.1, eight slices
$PY replay.py plan --seed 20260905 --lengths 0=500,1=500,2=120,3=40,4=150 --whole-max 400 --tag main
nice -n 10 $PY replay.py control-a --ranges 12-20-200000-210000:200000:200030 --record 200010 --edge 0,1 --workers 2 --tag control-a
nice -n 10 $PY replay.py control-b --drop-index 1 --ranges 12-20-200000-210000:200000:200030,11-17-20000-30000:25000:25030 --workers 2 --tag control-b
nice -n 10 $PY replay.py replay --plan-file plan-main.json --workers 4 --tag main      # > main.log
$PY render.py results-main.json                                                     # the tables above
$PY processed.py plan-main.json                                                     # guard-passing counts
$PY finalize.py                                                                     # sections 3-5 of this file
```

Outputs: `plan-main.json` (the sample), `shards-main.jsonl` (one line per shard as it finished), `results-main.json` (everything, including the first 20 differences per side per shard, which are empty), `results-control-a.json`, `results-control-b.json`, `main.log`, `control-a.log`, `control-b.log`.

| file | sha256 | records |
|---|---|---:|
| enum2/enum2.py | 1baf3478776993b8d188a23e09ec158771fcb8c77add0de5b2c7d500a3b48151 | |
| enum2/crosscheck/replay.py | c1cada1dd9592c0dc9bb91e48102f504da751f2f822f617ebb8577271d4c8743 | |
| enum/udenum (as hashed in every shard manifest) | 94a85d333d753ec2f518e62ef6d2f855d56b22dc6f3b890f53aa9575680f57b4 | |
| data/forbidden-74.json | ff1badd63a155fe71e53e2fef54888425f47bcae1a9e7b1d43e0df04cfff3c1a | 74 |
| enum/out-22/dag-22-61-f12/reach.json | 7ef2d3a6bc0d80852633e8a55b55462793be90238f40d62061249d77e1826dbc | |
| _parents/11-17.g6 | 5ffc92363c779b8b6c8ba6975ec2ecfe19ec8db3512d4cdc68a0037287a8e0f6 | 31131 |
| _parents/11-18.g6 | 0528952dfb7f646d6e8d7bb84e26e7e4c5adbe583e480d57449ea736551d4e17 | 43603 |
| _parents/11-19.g6 | 066ed9da90b6e85fb6282f68b84e073e4eca8189a2d765ab08c789e2efdf9eb0 | 18668 |
| _parents/11-20.g6 | dbea8d2ab3e3f2216be74483f2fc1d261d768b514e033fa936682cb1476495cf | 3333 |
| _parents/11-21.g6 | 5a4515afe0f7223d15f98361e23c0f0b56c37a84d48192ed4fdd0b229c041406 | 247 |
| _parents/11-22.g6 | 5a4515afe0f7223d15f98361e23c0f0b56c37a84d48192ed4fdd0b229c041406 | 247 |
| _parents/11-23.g6 | a976eb2a69a0f0f71659b00df1ce5288e95b203a7eeb88982461821dd570cdbd | 20 |
| _parents/12-20.g6 | 3e8f3b8ad92519dce733e2f2744f38544bae34b856a979920e363c70923c9130 | 369247 |
| _parents/12-21.g6 | 59c5b6bc7b7d8895db4af52e8740ae2fd23fbaeb4f35f716b9d2efa4b7b66f47 | 270819 |
| _parents/12-22.g6 | 723ef965e6d18e1432c6cdd586dbea79db2efb1570a8bfb9a7a9ce388918abe6 | 65229 |
| _parents/12-23.g6 | fbc33c6d28179935c1d50f4a0287193db42e1ed6c50b39a3dd06f2dbc5400a4d | 6125 |
| _parents/12-24.g6 | e1f0bdac545ad56591663222550c293aa634a35ea33307c6e155f7170b91e5ec | 6127 |
| _parents/12-25.g6 | 239dbbd122bea94d35fe6c980129cf93a526dd05cb19a817b99e110645088463 | 390 |
| _parents/12-26.g6 | b465334c1c390e499474cc3e585e0af5d3035a71168d9a4b16bf08ec6d90789a | 27 |
| _parents/12-27.g6 | 9cc850a8c6b406c368809cb76c2cb9e51d257fc72cdb4a11fd165e63b5e0f2db | 2 |

Manifest cross-check by the driver (`verify_inputs`): parent-file, forbidden-list and udenum hashes equal the values in every replayed shard manifest: yes.

