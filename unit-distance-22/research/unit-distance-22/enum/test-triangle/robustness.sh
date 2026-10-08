#!/usr/bin/env bash
# Input handling and budget edge cases.
set -uo pipefail
cd "$(dirname "$0")"
BIN=${UDTRIANGLE:-../../filter/udtriangle}
PY=${PY:-$HOME/tools/pyenv-gp10/bin/python}
status=0
expect_exit() {   # name, expected status, stdin bytes (printf format)
    local name=$1 want=$2 input=$3
    printf "$input" | "$BIN" > /dev/null 2>&1
    local got=$?
    if [ "$got" = "$want" ]; then echo "ok   $name (exit $got)"; else echo "FAIL $name (exit $got, want $want)"; status=1; fi
}
expect_exit "empty line is an error" 2 '\n'
expect_exit "a space inside graph6 is an error" 2 'C ~\n'
expect_exit "wrong length is an error" 2 'C~~\n'
expect_exit "25 vertices is an error (host limit 24)" 2 'X??????????????????????????????????????????????????\n'
expect_exit "a >>graph6<< header is an error" 2 '>>graph6<<C~\n'
expect_exit "nonzero padding bits are an error" 2 'Bx\n'
expect_exit "a byte above 126 is an error" 2 'C\x7f\n'
expect_exit "CRLF line ending is accepted" 0 'C~\r\n'
expect_exit "a last line without newline is accepted" 0 'C~'
expect_exit "order 0 and 1 are accepted" 0 '?\n@\n'
"$BIN" -b 0 < /dev/null > /dev/null 2>&1 && { echo "FAIL -b 0 accepted"; status=1; } || echo "ok   -b 0 refused"
"$BIN" -b 100001 < /dev/null > /dev/null 2>&1 && { echo "FAIL -b 100001 accepted"; status=1; } || echo "ok   -b 100001 refused"
out=$(printf '?\n@\nA_\nC~\n' | "$BIN" 2>/dev/null)
want=$'{"verdict":"pass"}\n{"verdict":"pass"}\n{"verdict":"pass"}'
if [ "$(echo "$out" | head -3)" = "$want" ] && echo "$out" | sed -n 4p | /usr/bin/grep -q '"verdict":"refuted"'; then
    echo "ok   orders 0, 1, 2 pass and K4 is refuted"
else echo "FAIL small orders: $out"; status=1; fi
# budgets: every budget from 1 to 12 on measure-17 gives valid output, flags only a subset of the full run's flags,
# and the counts are monotone in the budget
prev=-1
for b in 1 2 3 4 5 6 7 8 9 10 11 12 4096; do
    nice -n 10 "$BIN" -b "$b" < data/measure-17.g6 > out/budget-$b.out 2> out/budget-$b.err
    flagged=$(/usr/bin/grep -c -v '"verdict":"pass"' out/budget-$b.out)
    chk=$(nice -n 10 "$PY" devcheck_tri.py data/measure-17.g6 out/budget-$b.out)
    mx=$(echo "$chk" | sed -n 's/.* max_nodes=\([0-9]*\).*/\1/p')
    case "$chk" in ACCEPT*) ;; *) echo "FAIL budget $b: $chk"; status=1;; esac
    if [ "$mx" -gt "$b" ]; then echo "FAIL budget $b: a tree has $mx nodes"; status=1; fi
    if [ "$flagged" -lt "$prev" ]; then echo "FAIL budget $b: fewer flags than a smaller budget"; status=1; fi
    prev=$flagged
    echo "ok   budget $b: flagged $flagged of 1500, largest tree $mx nodes, dev checker ACCEPT"
done
# a budget only ever turns a verdict into pass: compare with the unbounded run line by line
bad=$(paste -d'\t' out/budget-5.out out/budget-4096.out | awk -F'\t' '$1 != "{\"verdict\":\"pass\"}" && $1 != $2' | wc -l)
if [ "$bad" = 0 ]; then echo "ok   budget 5: every certificate equals the unbounded run's"; else echo "FAIL budget 5 differs on $bad lines"; status=1; fi
# determinism: the same bytes twice
a=$(nice -n 10 "$BIN" < data/measure-16.g6 2>/dev/null | sha256sum); b=$(nice -n 10 "$BIN" < data/measure-16.g6 2>/dev/null | sha256sum)
[ "$a" = "$b" ] && echo "ok   deterministic (measure-16 twice: ${a:0:16})" || { echo "FAIL nondeterministic"; status=1; }
exit $status
