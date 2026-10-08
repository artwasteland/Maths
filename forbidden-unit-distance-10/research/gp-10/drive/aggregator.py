"""Compatibility entry point for the GP-10 aggregate writer."""

try:
    from .aggregate import *  # type: ignore
    from .aggregate import _cli
except ImportError:
    from aggregate import *  # type: ignore
    from aggregate import _cli  # type: ignore


if __name__ == "__main__":
    raise SystemExit(_cli())

