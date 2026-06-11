"""Command line interface for unstaple."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .naming import infer_stem, uniquify
from .scoring import DEFAULT_THRESHOLD, find_boundaries, segments
from .splitter import NoTextLayerError, load_features, write_segment


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="unstaple",
        description=(
            "Split one fat scanned PDF of stapled-together documents into "
            "correctly-bounded, sensibly-named separate PDFs."
        ),
    )
    parser.add_argument("pdf", type=Path, help="the stapled-together PDF to split")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print proposed cut points, confidence, and names; write nothing",
    )
    parser.add_argument(
        "-o",
        "--out-dir",
        type=Path,
        default=Path("unstapled"),
        help="output directory for split PDFs (default: ./unstapled)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        metavar="T",
        help=f"cut confidence threshold in [0,1] (default: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument("--version", action="version", version=f"unstaple {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.pdf.is_file():
        print(f"unstaple: error: {args.pdf}: no such file", file=sys.stderr)
        return 2

    try:
        reader, features = load_features(args.pdf)
    except NoTextLayerError as exc:
        print(f"unstaple: error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"unstaple: error: {args.pdf}: {exc}", file=sys.stderr)
        return 2

    num_pages = len(features)
    boundaries = find_boundaries(features, threshold=args.threshold)
    ranges = segments(num_pages, boundaries)
    n_docs = len(ranges)

    plural = "s" if num_pages != 1 else ""
    print(f"{args.pdf}: {num_pages} page{plural}, {n_docs} document{'s' if n_docs != 1 else ''} detected")

    if not boundaries:
        print("no document boundaries found; nothing to unstaple "
              "(try a lower --threshold, or this may be a single document)")
        return 0

    print()
    print("proposed cuts:")
    for b in boundaries:
        reasons = "; ".join(b.reasons)
        print(f"  cut before page {b.page_index + 1:<3} confidence {b.confidence:.2f}  [{reasons}]")

    feature_by_index = {f.index: f for f in features}
    stems = uniquify(
        [infer_stem(feature_by_index[start], i + 1) for i, (start, _) in enumerate(ranges)]
    )
    names = [f"{stem}.pdf" for stem in stems]

    print()
    print("documents:")
    for (start, end), name in zip(ranges, names):
        pages = f"pages {start + 1}-{end}" if end - start > 1 else f"page {start + 1}"
        print(f"  {pages:<12} -> {name}")

    if args.dry_run:
        print()
        print("dry run: nothing written")
        return 0

    print()
    for (start, end), name in zip(ranges, names):
        out_path = args.out_dir / name
        write_segment(reader, start, end, out_path)
        print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
