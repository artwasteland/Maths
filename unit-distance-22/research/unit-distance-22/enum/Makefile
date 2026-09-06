CC ?= cc
CFLAGS ?= -O3 -DNDEBUG
CFLAGS += -std=c17 -Wall -Wextra -Wpedantic -Wshadow -Wconversion \
	-Wno-old-style-declaration \
	-I/usr/include/x86_64-linux-gnu/nauty -I/usr/include/nauty
LDLIBS += -lnauty

.PHONY: all clean check

all: udenum

udenum: udenum.c
	$(CC) $(CFLAGS) $< -o $@ $(LDLIBS)

check: udenum
	./verify.py quick

clean:
	rm -f udenum
