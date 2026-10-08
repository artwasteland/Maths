CC ?= cc
CFLAGS ?= -std=c17 -O3 -Wall -Wextra -Wpedantic

# The two linear-rule provers are in "all" (2026-09-26, the u(23) supervisor): the cloud slice script's bare
# "make" builds them on every worker, whose pins and self-checks then include them.
all: libudfilter.a udfilter udrhombus udtriangle

libudfilter.a: udfilter.o
	ar rcs $@ $^

udfilter: libudfilter.a udfilter-cli.o
	$(CC) $(CFLAGS) -o $@ udfilter-cli.o libudfilter.a

udfilter.o: udfilter.c udfilter.h
	$(CC) $(CFLAGS) -c -o $@ udfilter.c

udfilter-cli.o: udfilter-cli.c udfilter.h
	$(CC) $(CFLAGS) -c -o $@ udfilter-cli.c

# The triangle-orientation case-tree prover (research/unit-distance-23/RHOMBUS-SPEC.md, Section 4); tests in
# ../enum/test-triangle (run.sh; the quick ones are "make check-triangle").  Standalone (no code shared with
# udfilter).
udtriangle: udtriangle.c
	$(CC) $(CFLAGS) -o $@ udtriangle.c

# The rhombus rule's prover (research/unit-distance-23/RHOMBUS-SPEC.md, Sections 1-3); tests in ../enum/test-rhombus
# (run-all.sh; the quick ones are "make check-rhombus").  Standalone.
udrhombus: udrhombus.c
	$(CC) $(CFLAGS) -o $@ udrhombus.c

clean:
	$(RM) udfilter libudfilter.a udfilter.o udfilter-cli.o udtriangle udrhombus

.PHONY: check-398
# Set 74 finds K4 and passes the first GP-10 graph; set 398 names it as member 74; set 398
# refuses the 74 file.  The full validation of set 398 is ../enum/test-398 (REPORT-398.md).
check-398: udfilter
	printf 'C~\n' | ./udfilter -f ../data/forbidden-74.json -t ../data/tu-gadgets.json | grep -q '"verdict":"forbidden"'
	! printf 'I??OzIJ}?\n' | ./udfilter -f ../data/forbidden-74.json -t ../data/tu-gadgets.json | grep -q '"verdict":"forbidden"'
	printf 'I??OzIJ}?\n' | ./udfilter -s 398 -f ../data/forbidden-398.json -t ../data/tu-gadgets.json | grep -q '"index":74,'
	! printf 'C~\n' | ./udfilter -s 398 -f ../data/forbidden-74.json -t ../data/tu-gadgets.json 2>/dev/null
	@echo "check-398: set 74 and set 398 behave as pinned; set 398 refuses the 74 file"

.PHONY: check-u23
# The host limit UDF_MAX_VERTICES = 24 (u(23) programme): 23- and 24-vertex hosts are read and
# filtered, a 25-vertex host is refused.  Hosts: K4 on vertices 19..22 of 23 (member 0 in both
# sets); TU gadget 0 with its pair non-adjacent on vertices 16..21 of 24; member 74 (the first of
# GP-10's 324) on vertices 13..22 of 23, which set 398 names and set 74 does not.
check-u23: udfilter
	printf 'V??????????????????????????????????@???W??B_\n' | ./udfilter -s 74 -f ../data/forbidden-74.json -t ../data/tu-gadgets.json | grep -q '"verdict":"forbidden","witness":{"index":0,'
	printf 'Wh????????????????????????G??G??S??H???g???????\n' | ./udfilter -s 398 -f ../data/forbidden-398.json -t ../data/tu-gadgets.json | grep -q '"verdict":"tu","witness":{"index":0,'
	printf 'V????????????????????????????O??[??q??PW?Bw?\n' | ./udfilter -s 398 -f ../data/forbidden-398.json -t ../data/tu-gadgets.json | grep -q '"verdict":"forbidden","witness":{"index":74,'
	! printf 'V????????????????????????????O??[??q??PW?Bw?\n' | ./udfilter -f ../data/forbidden-74.json -t ../data/tu-gadgets.json | grep -q '"verdict":"forbidden"'
	! printf 'X??????????????????????????????????????????????_???\n' | ./udfilter -s 398 -f ../data/forbidden-398.json -t ../data/tu-gadgets.json 2>/dev/null
	@echo "check-u23: 23- and 24-vertex hosts are filtered in both sets; a 25-vertex host is refused"

PYTHON ?= python3
.PHONY: check-rhombus
# The rhombus prover's unit tests (enum/test-rhombus/units.py, standard library only): K2,3 refuted;
# the six TU gadgets tu with their own pairs; Moser spindle, unit rhombus and W6 pass; AMP's 56
# known graphs pass; every certificate replayed, tampered certificates rejected, bad input refused.
# The B10, agreement, mutant and end-to-end tests are enum/test-rhombus/run-all.sh.
check-rhombus: udrhombus
	$(PYTHON) ../enum/test-rhombus/units.py --udrhombus ./udrhombus

.PHONY: check-triangle
# The triangle prover's unit graphs (enum/test-triangle/units.tsv: K4 and K1,1,3 refuted; Moser spindle, W6, two
# triangular-lattice patches and the rhombus with its short diagonal pass; the six TU gadgets tu) get exactly
# their expected verdicts, and the statistics line counts no verify_fail, lift_fail or internal pass.  The full
# suite, with the certificate checks, is ../enum/test-triangle/run.sh.
check-triangle: udtriangle
	@out=$$(mktemp) && err=$$(mktemp) && cut -f2 ../enum/test-triangle/units.tsv | ./udtriangle 2>$$err \
	  | sed -n 's/^{"verdict":"\([a-z]*\)".*/\1/p' > $$out && cut -f3 ../enum/test-triangle/units.tsv | diff - $$out \
	  && grep -q 'verify_fail=0 lift_fail=0 internal=0' $$err; status=$$?; rm -f $$out $$err; exit $$status
	@echo "check-triangle: the 13 unit graphs of enum/test-triangle/units.tsv get their expected verdicts"
