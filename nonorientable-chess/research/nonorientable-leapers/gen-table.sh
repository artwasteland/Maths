#!/bin/bash
cd "$(dirname "$0")"
out=terms-1-13.tsv
echo -e "topo\tleaper\tterms(n=1..13)" > $out
for topo in flat torus mobius klein; do
  for L in "1 2 knight" "1 3 camel" "2 3 zebra" "1 4 giraffe"; do
    set -- $L; a=$1; b=$2; name=$3; line=""
    for k in $(seq 1 13); do line="$line $(./leap $topo $a $b $k)"; done
    echo -e "$topo\t$name\t$(echo $line | sed 's/ /, /g')" >> $out
    echo "done: $topo $name" >&2
  done
done
echo "ALL DONE" >&2
