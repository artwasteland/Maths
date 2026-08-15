#!/usr/bin/env bash
cd "$(dirname "$0")"
for sd in 1001 2002 3003 4004 5005 6006 7007 8008; do
  ./sis 5 12000000 $sd | grep UNDIRECTED | sed "s/^/seed $sd  /"
done
echo DONE
