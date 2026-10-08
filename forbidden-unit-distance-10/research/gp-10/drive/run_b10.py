"""B10 entry point with predictions, bounded parallelism, and resume."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .driver import PYTHON_DEFAULT, run_pipeline, _parse_limits
    from .graph6 import load_graph6
    from .poset import build_poset
except ImportError:
    from driver import PYTHON_DEFAULT, _parse_limits, run_pipeline  # type: ignore
    from graph6 import load_graph6  # type: ignore
    from poset import build_poset  # type: ignore


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "B10.g6"


def _write_predictions(path: Path, input_count: int, poset_stats: dict[str, object], args: argparse.Namespace) -> None:
    predicted_embedded = args.predicted_embedded
    predicted_refuted = args.predicted_refuted
    predicted_unknown = args.predicted_unknown
    if predicted_embedded is None and predicted_refuted is None and predicted_unknown is None:
        predicted_embedded = input_count
        predicted_refuted = 0
        predicted_unknown = 0
        basis = "provisional optimistic baseline, supplied before producers run"
    else:
        predicted_embedded = 0 if predicted_embedded is None else predicted_embedded
        predicted_refuted = 0 if predicted_refuted is None else predicted_refuted
        predicted_unknown = 0 if predicted_unknown is None else predicted_unknown
        basis = "values supplied on the command line before producers run"
    path.write_text(
        "# GP-10 B10 predictions\n\n"
        "This file is written before the first producer process is launched.\n\n"
        f"- input graphs: {input_count}\n"
        f"- predicted embedded: {predicted_embedded}\n"
        f"- predicted refuted: {predicted_refuted}\n"
        f"- predicted unknown: {predicted_unknown}\n"
        f"- predicted maximal graphs: {poset_stats.get('maximal_count')}\n"
        f"- timing model: poset build is measured once, then each producer budget is a\n"
        f"  per-graph limit; wall time is approximately the sum of batch maxima divided\n"
        f"  by the requested process count, plus propagation and aggregation.\n"
        f"- basis: {basis}\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--embedder", default=str(ROOT / "embed" / "gp10embed.py"))
    parser.add_argument("--refuter", default=str(ROOT / "refute" / "gp10refute.py"))
    parser.add_argument("--forbidden", type=Path)
    parser.add_argument("--forbidden-g6", type=Path)
    parser.add_argument("--hosts", type=Path)
    parser.add_argument("--python", default=PYTHON_DEFAULT)
    parser.add_argument("--time-limits", type=_parse_limits, default=[1.0, 5.0, 30.0, 120.0])
    parser.add_argument("--processes", type=int, choices=(1, 2), default=1)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--predicted-embedded", type=int)
    parser.add_argument("--predicted-refuted", type=int)
    parser.add_argument("--predicted-unknown", type=int)
    parser.add_argument("--exhaustive-fallback", action="store_true")
    args = parser.parse_args()
    args.run_dir.mkdir(parents=True, exist_ok=True)
    input_g6 = load_graph6(args.input)
    poset_path = args.run_dir / "poset.json"
    if poset_path.exists():
        stats = json.loads(poset_path.read_text(encoding="utf-8")).get("stats", {})
    else:
        poset = build_poset(input_g6, progress_every=1000)
        poset.write(poset_path)
        stats = poset.stats
    predictions_path = args.run_dir / "PREDICTIONS.md"
    if not predictions_path.exists() or not args.resume:
        _write_predictions(predictions_path, len(input_g6), stats, args)
    summary = run_pipeline(
        args.input,
        args.run_dir,
        args.embedder,
        args.refuter,
        args.forbidden,
        args.time_limits,
        workers=args.processes,
        python=args.python,
        poset_path=poset_path,
        resume=args.resume,
        hosts_path=args.hosts,
        forbidden_g6_path=args.forbidden_g6,
        exhaustive_fallback=args.exhaustive_fallback,
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
