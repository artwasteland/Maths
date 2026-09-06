PYTHON := $(HOME)/tools/pyenv-maths/bin/python
DRAT_SOURCE := $(HOME)/tools/sat/cadical/test/cnf/drat-trim.c

.PHONY: check controls clean-artifacts

scratch/drat-trim: $(DRAT_SOURCE)
	mkdir -p scratch
	gcc -O2 -DNDEBUG -o $@ $<

check: scratch/drat-trim
	$(PYTHON) -m py_compile chirosat.py controls.py run_controls.py batch_bench.py run_batch_controls.py exist.py aggregate-depth2.py
	nice -n 10 $(PYTHON) exist.py 8 8 --backend cadical --artifacts scratch/exist-8-8 --corrupt-proof > /dev/null
	nice -n 10 $(PYTHON) exist.py 8 8 --backend pysat --drop-exact-b | grep -q '"verdict": "SAT"'
	! nice -n 10 $(PYTHON) exist.py 8 8 --list-cubes --backend pysat --mutate-drop-cube 2>/dev/null
	! nice -n 10 $(PYTHON) exist.py 8 8 --list-cubes --backend pysat --cube-depth 2 --cube-index 0 --mutate-drop-cube 2>/dev/null
	nice -n 10 $(PYTHON) run_controls.py --mutations fano pappus

controls: scratch/drat-trim
	nice -n 10 $(PYTHON) run_controls.py --mutations

clean-artifacts:
	@echo "Remove scratch artifacts manually after checking their paths."
