<div align="center">

# unstaple

**Split one fat scanned PDF of stapled-together documents into correctly-bounded, sensibly-named separate PDFs.**

[![CI](https://github.com/BenMalaga/unstaple/actions/workflows/test.yml/badge.svg)](https://github.com/BenMalaga/unstaple/actions/workflows/test.yml)
[![release](https://img.shields.io/github/v/release/BenMalaga/unstaple?color=blue&label=release)](https://github.com/BenMalaga/unstaple/releases)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)](https://pypi.org/project/unstaple/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

</div>

You fed a stack of mail into the sheet scanner. Out came `scan.pdf`: an invoice, a lab report, and a city notice, all stapled into one 6-page file. Your archive wants three files with real names. `unstaple` reads the text layer, finds where one document ends and the next begins, and writes each one out separately.

```console
$ unstaple scan.pdf
scan.pdf: 6 pages, 3 documents detected

proposed cuts:
  cut before page 3   confidence 0.95  [page numbering reset: "Page 1 of 3" after "Page 2 of 2"; header shift (similarity 0.00)]
  cut before page 6   confidence 0.96  [page numbering reset: "Page 1 of 1" after "Page 3 of 3"; header shift (similarity 0.00); date change (2026-04-17 -> 2026-05-02)]

documents:
  pages 1-2    -> 2026-03-03-acme-supply-co-invoice-4821.pdf
  pages 3-5    -> 2026-04-17-northwind-medical-group-lab-results-summary.pdf
  page 6       -> 2026-05-02-city-of-springfield.pdf

wrote unstapled/2026-03-03-acme-supply-co-invoice-4821.pdf
wrote unstapled/2026-04-17-northwind-medical-group-lab-results-summary.pdf
wrote unstapled/2026-05-02-city-of-springfield.pdf
```

That transcript is real: it is the output of `unstaple` on the synthetic fixture in `tests/fixtures/`, and the test suite asserts those exact boundaries and names.

## Install

```console
pip install unstaple
```

Or, for a clean isolated install of the CLI:

```console
pipx install unstaple
```

Requires Python 3.10 or newer. The only runtime dependency is [pypdf](https://pypi.org/project/pypdf/).

## Usage

```console
unstaple scan.pdf              # split into ./unstapled/
unstaple scan.pdf --dry-run    # show proposed cuts and names, write nothing
unstaple scan.pdf -o outbox    # choose the output directory
unstaple scan.pdf --threshold 0.7   # demand more confidence before cutting
```

Always start with `--dry-run`. It prints every proposed cut with a confidence score and the evidence behind it, so you can sanity-check the plan before any files are written. If a boundary is missed, lower `--threshold`; if it cuts too eagerly, raise it.

`unstaple` is lossless: every input page lands in exactly one output file, in order. Blank pages (separator sheets, blank duplex backs) stay attached to the document before them.

## How boundary scoring works

For every page, `unstaple` extracts deterministic signals from the text layer. No ML, no network, no cloud: the same input always produces the same cuts, and every cut comes with its reasons.

For each pair of adjacent pages it asks: does the second page start a new document?

**Evidence for a cut** (combined with a noisy-OR, so any strong signal can carry the decision):

| Signal | Weight | Example |
|---|---|---|
| Page numbering resets after completing | 0.90 | `Page 1 of 3` right after `Page 2 of 2` |
| Page numbering drops back to 1 | 0.85 | `Page 1 of 5` after `Page 4 of 9` |
| Bare numbering restarts | 0.70 | a lone `1` after a lone `6` |
| Blank page separator | 0.80 | a scanner divider sheet between documents |
| Numbering starts after unnumbered pages | 0.55 | `Page 1 of 2` after a letter with no page numbers |
| Header shift | 0.50 | first-lines token fingerprint goes from one letterhead to another |
| Previous page completed its numbering | 0.45 | `Page 2 of 2` followed by an unnumbered page |
| Date change | 0.30 | both pages dated, no date in common |

**Evidence against a cut** (multiplies the score down):

| Dampener | Factor | Example |
|---|---|---|
| Page numbering continues | 0.10 | `Page 1 of 3` then `Page 2 of 3` |
| Header continuity | 0.50 | the same letterhead tokens on both pages |
| Shared date | 0.70 | the same date printed on both pages |

A cut is proposed when the final score clears `--threshold` (default 0.5). One deliberate asymmetry: a hard numbering reset overrides header continuity and shared dates, because three invoices from the same vendor share a letterhead but are still three documents.

Names are inferred from the first page of each split: the first date found (ISO format) plus the first prominent line (usually the letterhead), plus a following all-caps title line if there is one. Collisions get `-2`, `-3` suffixes; if nothing usable is found, you get `document-01.pdf`.

## Honest scope

v0.1 is deliberately narrow. Know what you are getting:

- **Text-layer PDFs only.** If `pypdf` cannot extract text, `unstaple` refuses and tells you so. Image-only scans need OCR first (run them through [OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF)); native OCR support is on the roadmap.
- **Heuristics, not magic.** Documents with no page numbers, no dates, and an identical or absent header will not be separated. Two-page memos that look alike may be merged. `--dry-run` exists precisely so you can check before committing.
- **English-leaning patterns.** "Page X of Y" and English month names are recognized; other languages are roadmap material (and easy contributions, see below).
- **One PDF in, N PDFs out.** No watch folders, no GUI, no daemon. It is a small sharp tool meant to sit in a pipeline before your archive tool ingests the results.

## Why this exists

Every paperless workflow hits this problem: the scanner ADF happily eats a month of mail and hands you one giant PDF. The [paperless-ngx issue tracker has years of requests](https://github.com/paperless-ngx/paperless-ngx/discussions) for automatic document separation, and the usual answers are barcode separator sheets (which require planning ahead), cloud SaaS splitters (your mail, someone else's server), or GUI page-range pickers (you do the boundary detection yourself, with a mouse). `unstaple` is the missing fourth option: a local, deterministic, scriptable splitter that explains its decisions and never sends a byte anywhere.

## Development

```console
git clone https://github.com/BenMalaga/unstaple
cd unstaple
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

The test fixtures are synthetic stapled PDFs generated by `tests/fixtures/make_fixtures.py` (reportlab, dev dependency only). The end-to-end tests split them and assert exact boundaries and filenames.

## Roadmap

- OCR fallback for image-only scans (probably via optional OCRmyPDF integration)
- Non-English page-number and date patterns
- Font-size and layout signals from the PDF content stream (a big bold first line is a strong title hint)
- `--interactive` mode to accept, reject, or move proposed cuts

## Contributing

The single most valuable contribution is a real-world PDF that `unstaple` gets wrong, anonymized, with a note about where the cuts should have been. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE), Copyright (c) 2026 Ben Malaga.
