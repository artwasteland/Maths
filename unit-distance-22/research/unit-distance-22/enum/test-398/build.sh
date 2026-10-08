#!/bin/bash
# Build every binary the enum/test-398 scripts use, from sources in this directory:
#   old/enum/udenum, old/filter/udfilter   the UNMODIFIED sources (git HEAD 377aa704e); with the
#                                          system cc 13.3.0 and libnauty 2.8.8 they rebuild byte for
#                                          byte to the production binaries (udenum 94a85d33...,
#                                          udfilter d4ccae3f..., hashed in every u(22) shard manifest)
#   bin/matcher10                          GP-10's matcher.c, unmodified (10-vertex hosts)
#   bin/matcher32                          matcher32.c, the same with hosts widened to 31 vertices
# The NEW udenum and udfilter are built by the ordinary Makefiles in ../ and ../../filter/.
set -euo pipefail
cd "$(dirname "$0")"
nice -n 10 make -C old/enum udenum
nice -n 10 make -C old/filter
mkdir -p bin
nice -n 10 cc -O3 -std=c11 -Wall -Wextra -pedantic bin/matcher-gp10-original.c -lz -o bin/matcher10
nice -n 10 cc -O3 -std=c11 -Wall -Wextra -pedantic matcher32.c -lz -o bin/matcher32
nice -n 10 make -C .. udenum
nice -n 10 make -C ../../filter
sha256sum old/enum/udenum old/filter/udfilter bin/matcher-gp10-original.c bin/matcher10 bin/matcher32 \
    ../udenum ../../filter/udfilter
