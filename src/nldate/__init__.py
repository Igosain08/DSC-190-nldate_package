"""nldate: parse natural-language dates."""

import sys

from nldate.parser import parse

__all__ = ["main", "parse"]


def main() -> None:
    """Command-line entry point: ``nldate <expression>``."""
    expr = " ".join(sys.argv[1:])
    try:
        print(parse(expr).isoformat())
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
