# The CURRENT Mode 398 udenum (branch claude/answering-alexeev-u22 at 952ae252d, REPORT-398.md),
# kept unmodified as the reference of the Mode 398 speed work (SPEED-398): udenum.c here is
# byte-identical to enum/udenum.c at 952ae252d, and with cc 13.3.0 and libnauty 2.8.8 it rebuilds
# to a99b130a..., the binary REPORT-398 validated.  Same flags as enum/Makefile.
CC ?= cc
CFLAGS ?= -O3 -DNDEBUG
CFLAGS += -std=c17 -Wall -Wextra -Wpedantic -Wshadow -Wconversion \
	-Wno-old-style-declaration \
	-I/usr/include/x86_64-linux-gnu/nauty -I/usr/include/nauty
LDLIBS += -lnauty

.PHONY: all clean

all: udenum

udenum: udenum.c
	$(CC) $(CFLAGS) $< -o $@ $(LDLIBS)

clean:
	rm -f udenum
