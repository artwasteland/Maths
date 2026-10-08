#!/usr/bin/env bash
# Desktop samples only. Supply a NEW_OUTDIR; never runs the full population.
# bash benchmark_samples.sh SAMPLES FORBIDDEN_JSON NEW_OUTDIR
set -euo pipefail
if (( $# != 3 )); then
    echo "usage: bash benchmark_samples.sh SAMPLES FORBIDDEN_JSON NEW_OUTDIR" >&2
    exit 2
fi
GP11_TOOLS=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
GP11_SAMPLES=$(realpath -- "$1")
GP11_F10=$(realpath -- "$2")
GP11_OUT=$3
GP11_PY=${GP11_PY:-<repo>/pyenv-gp10/bin/python}
if [[ -e "$GP11_OUT" ]]; then
    echo "Choose a new output directory: $GP11_OUT" >&2
    exit 2
fi
mkdir -p -- "$GP11_OUT"
GP11_OUT=$(realpath -- "$GP11_OUT")
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export TMPDIR="$GP11_OUT/scratch"
mkdir -p -- "$TMPDIR"
run() {
    local log=$1
    shift
    nice -n 15 timeout 1800 prlimit --as=4000000000 "$@" > "$GP11_OUT/$log" 2>&1
}
run selftest.log "$GP11_PY" -B "$GP11_TOOLS/selftest.py" "$GP11_SAMPLES" "$GP11_F10" "$GP11_OUT/selftest.json"
run audit-first2000.log "$GP11_PY" -B "$GP11_TOOLS/independent_audit.py" \
    "$GP11_SAMPLES/first2000-closed.g6" "$GP11_SAMPLES/first2000-closed.jsonl" \
    --sample --stages 13 --jobs 1 --outdir "$GP11_OUT/audit-first2000"
run audit-largest20.log "$GP11_PY" -B "$GP11_TOOLS/independent_audit.py" \
    "$GP11_SAMPLES/largest20-closed.g6" "$GP11_SAMPLES/largest20-closed.jsonl" \
    --sample --jobs 1 --forbidden-json "$GP11_F10" --outdir "$GP11_OUT/audit-largest20"
run redteam.log "$GP11_PY" -B "$GP11_TOOLS/independent_audit_redteam.py" \
    "$GP11_SAMPLES/largest20-closed.g6" "$GP11_SAMPLES/largest20-closed.jsonl" "$GP11_OUT/redteam"
run modp-by-type.log /usr/bin/python3 -S -B "$GP11_TOOLS/modp_identities.py" \
    "$GP11_SAMPLES/by-type.jsonl" "$GP11_OUT/modp-by-type.json" --jobs 1 --details "$GP11_OUT/modp-by-type.jsonl"
run modp-trees.log /usr/bin/python3 -S -B "$GP11_TOOLS/modp_identities.py" \
    "$GP11_SAMPLES/trees.jsonl" "$GP11_OUT/modp-trees.json" --jobs 1 --details "$GP11_OUT/modp-trees.jsonl"
run modp-largest20.log /usr/bin/python3 -S -B "$GP11_TOOLS/modp_identities.py" \
    "$GP11_SAMPLES/largest20.jsonl" "$GP11_OUT/modp-largest20.json" --jobs 1 --no-red-controls \
    --details "$GP11_OUT/modp-largest20.jsonl"
run embed-sample.log "$GP11_PY" -B "$GP11_TOOLS/embed_redteam.py" \
    "$GP11_OUT/audit-largest20/L11.g6" "$GP11_SAMPLES/largest20-closed.g6" \
    "$GP11_SAMPLES/largest20-closed.jsonl" "$GP11_OUT/embed-sample.json" \
    --jobs 1 --limit 2 --starts 512 --rounds 2 --details "$GP11_OUT/embed-sample.jsonl"
cat "$GP11_OUT/selftest.log"
