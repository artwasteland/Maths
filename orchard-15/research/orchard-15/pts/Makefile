CC ?= gcc
CFLAGS ?= -std=c17 -O3 -Wall -Wextra -Wpedantic
NAUTY_INC ?= /usr/include/x86_64-linux-gnu/nauty

ptsenum: ptsenum.c
	$(CC) $(CFLAGS) -I$(NAUTY_INC) ptsenum.c -lnauty -o ptsenum

clean:
	rm -f ptsenum
