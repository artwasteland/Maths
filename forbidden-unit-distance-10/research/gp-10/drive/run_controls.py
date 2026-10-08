"""Compatibility entry point for the registered GP-10 controls."""

try:
    from .controls import main
except ImportError:
    from controls import main  # type: ignore


if __name__ == "__main__":
    raise SystemExit(main())

