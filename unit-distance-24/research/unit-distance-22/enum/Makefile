CC ?= cc
CFLAGS ?= -O3 -DNDEBUG
CFLAGS += -std=c17 -Wall -Wextra -Wpedantic -Wshadow -Wconversion \
	-Wno-old-style-declaration \
	-I/usr/include/x86_64-linux-gnu/nauty -I/usr/include/nauty
LDLIBS += -lnauty

.PHONY: all clean check check-398

all: udenum

udenum: udenum.c
	$(CC) $(CFLAGS) $< -o $@ $(LDLIBS)

check: udenum
	./verify.py quick

# Both forbidden sets load with their pinned statistics, and each refuses the other's file.
# The full validation of set 398 is enum/test-398 (REPORT-398.md).
check-398: udenum
	./udenum --forbidden ../data/forbidden-74.json --pattern-stats | grep -qx '{"forbidden_graphs":74,"patterns":635,"size_distribution":{"2":61,"3":413,"4":130,"5":26,"6":4,"7":1}}'
	./udenum --forbidden ../data/forbidden-398.json --forbidden-set 398 --pattern-stats | grep -qx '{"forbidden_graphs":398,"patterns":3875,"size_distribution":{"2":251,"3":2474,"4":920,"5":192,"6":34,"7":4}}'
	! ./udenum --forbidden ../data/forbidden-74.json --forbidden-set 398 --pattern-stats 2>/dev/null
	! ./udenum --forbidden ../data/forbidden-398.json --pattern-stats 2>/dev/null
	@echo "check-398: set 74 and set 398 load with their pinned statistics; each refuses the other's file"

clean:
	rm -f udenum
