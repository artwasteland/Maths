CC ?= cc
CFLAGS ?= -std=c17 -O3 -Wall -Wextra -Wpedantic

all: libudfilter.a udfilter

libudfilter.a: udfilter.o
	ar rcs $@ $^

udfilter: libudfilter.a udfilter-cli.o
	$(CC) $(CFLAGS) -o $@ udfilter-cli.o libudfilter.a

udfilter.o: udfilter.c udfilter.h
	$(CC) $(CFLAGS) -c -o $@ udfilter.c

udfilter-cli.o: udfilter-cli.c udfilter.h
	$(CC) $(CFLAGS) -c -o $@ udfilter-cli.c

clean:
	$(RM) udfilter libudfilter.a udfilter.o udfilter-cli.o
