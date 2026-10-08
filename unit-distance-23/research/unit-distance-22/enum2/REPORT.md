# WHAT WORKS

`enum2.py` is an independent Python implementation using pynauty for canonical labelling and automorphism orbits. It has a local graph6 codec, the 635 rooted forbidden patterns from `data/forbidden-74.json`, minimal bad-neighborhood computation, the edge window, the minimum-degree parent guard, and an independent injective edge-preserving backtracker.

Compilation check:

    ~/tools/pyenv-maths/bin/python -m py_compile enum2.py

Output: no output, exit status 0.

Input loading check:

    ~/tools/pyenv-maths/bin/python - <<'PY'
    import enum2
    print(f'forbidden={len(enum2.LOAD_FORBIDDEN)} patterns={len(enum2.PATTERNS)}')
    PY

Output:

    forbidden=74 patterns=635

The real extension path mutation harness:

    nice -n 10 ~/tools/pyenv-maths/bin/python enum2.py mutations

Output:

    {"break_orbit_raw": 2, "break_orbit_unique": 1, "drop_pattern_k4": 1, "normal_k4": 0}

The normal path rejects the K4 child from a triangle parent. Removing the four K4 rooted patterns emits one K4 child. Disabling the orbit test produces two raw constructions of one canonical child. These are all extension-path checks, not direct calls to a filter.

The deliberate red mutation was made by changing line 472, `if normal_count != 0:`, to `if normal_count != 1:`. The command above then exited 1 with:

    AssertionError: K4 was accepted by the normal path

The line was restored and the passing output above was rerun.

Brute-force comparison command for every edge count at n=4 through n=8:

    for n in 4 5 6 7 8; do for m in $(seq 0 $((n*(n-1)/2))); do nice -n 10 ~/tools/pyenv-maths/bin/python enum2.py check --n "$n" --m "$m" || exit 1; done; done

Every line reported `equal=True`. The exact F-free count vectors, indexed by m from zero through the complete graph, were:

    n=4: 1,1,2,3,2,1,0
    n=5: 1,1,2,4,6,6,4,1,0,0,0
    n=6: 1,1,2,5,9,15,19,18,11,4,0,0,0,0,0,0
    n=7: 1,1,2,5,10,21,39,58,73,72,41,8,1,0,0,0,0,0,0,0,0,0
    n=8: 1,1,2,5,11,24,54,108,193,307,397,381,221,38,3,0,0,0,0,0,0,0,0,0,0,0,0,0,0

The same check was run for n=3 and m=0,1,2,3. The four outputs were respectively `ours=1 brute=1 equal=True`.

The n=9 checks completed for m=0 through m=15 before the aggregate sweep was stopped. Exact counts were:

    1,1,2,5,11,25,61,141,316,661,1249,2055,2759,2703,1550,243

For each of those 16 values, ours and brute force were equal. The exact command was:

    timeout 500 bash -c 'for m in $(seq 0 36); do ~/tools/pyenv-maths/bin/python -u enum2.py check --n 9 --m "$m" || exit 1; done' > /tmp/enum2-n9-all.out 2>&1

The foreground sweep was stopped with exit status 130 while m=16 and later values remained. No process was left running.

Canonical graph6 validation on all 56 supplied records:

    ~/tools/pyenv-maths/bin/python -u - <<'PY'
    from pathlib import Path
    import enum2
    known=[x for x in (enum2.ROOT.parent/'sources'/'amp'/'anc'/'graph6.txt').read_text().splitlines() if x]
    canonical=[enum2.canonical_g6(enum2.graph6_decode(x)) for x in known]
    print('known_records',len(known))
    print('canonical_stable',sum(a==b for a,b in zip(known,canonical)))
    print('unique',len(set(known)))
    PY
    /usr/bin/nauty-labelg -q ../sources/amp/anc/graph6.txt > /tmp/enum2-labelg.g6
    cmp ../sources/amp/anc/graph6.txt /tmp/enum2-labelg.g6 && echo 'labelg_byte_identical=True'

Output:

    known_records 56
    canonical_stable 56
    unique 56
    labelg_byte_identical=True

The real verification flag also ran on a K4 candidate:

    nice -n 10 ~/tools/pyenv-maths/bin/python enum2.py enumerate --parents /tmp/enum2-triangle.g6 --n 4 --m 6 --output /tmp/enum2-k4.g6 --verify
    wc -l /tmp/enum2-k4.g6

Output:

    children=0
    0 /tmp/enum2-k4.g6

Determinism check:

    nice -n 10 ~/tools/pyenv-maths/bin/python enum2.py determinism --n 8 --m 14

Output:

    n=8 m=14 records=3 byte_identical=True

# WHAT DOES NOT

The Table 1 dense recursive run did not complete. The command below produced no checkpoint count before the bounded attempt was stopped:

    nice -n 10 timeout 540 ~/tools/pyenv-maths/bin/python enum2.py table --limit 1

Therefore this module does not reproduce the required n=16 count 1 or n=17 count 15. It makes no claim about the larger Table 1 values, u-bar(22), or u-bar(23).

The n=9 sweep did not complete all edge counts. The full brute-force requirement for every m at n=10, n=11, and n=12 was not completed.

The 56 known graphs were checked for stable canonical graph6 representation, uniqueness, and labelg agreement. Their appearance in generated `(n,m)` output files was not completed because the dense recursive files were not generated.

# UNCERTAIN

- The n=10 through n=12 all-edge brute-force comparisons remain work items.
- The n=9 m=16 through m=36 brute-force comparisons remain work items.
- Dense recursive performance and counts at n=10 through n=22 remain unexercised.
- Shard manifests, frozen parent-file hashes, and the five megabyte file-size policy are not implemented in this module.
- TU filtering, embedding, certificate generation, and the independent checker are outside this module and were not exercised.
- Agreement against the first enumerator was not run, as the task forbids reading that module.
- The full known-extremal appearance check remains pending until the corresponding generated files exist.

# PROPOSED CONTRACT AMENDMENTS

None. The measured performance limitation is an implementation limitation, not evidence that the contract semantics are wrong.
