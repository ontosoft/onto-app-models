"""CLI: generate an OntoUI model from a SHACL shapes file.

    python -m model_generator shapes.ttl                # Turtle to stdout
    python -m model_generator shapes.ttl -o model.ttl   # write to a file
"""

from __future__ import annotations

import argparse
import sys

from .builder import generate_appmodel_from_shacl
from .templates import DEFAULT_BASE


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="model_generator",
        description="Generate a complete OntoUI app model from SHACL shapes.",
    )
    parser.add_argument("shapes", help="Path to the input SHACL shapes Turtle file")
    parser.add_argument("-o", "--output", help="Write Turtle here (default: stdout)")
    parser.add_argument(
        "--base", default=DEFAULT_BASE, help="Base IRI for the generated individuals"
    )
    args = parser.parse_args(argv)

    with open(args.shapes, encoding="utf-8") as fh:
        shapes_ttl = fh.read()
    rdf = generate_appmodel_from_shacl(shapes_ttl, base=args.base).rdf

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(rdf)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(rdf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
